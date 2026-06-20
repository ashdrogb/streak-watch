"""
Flask API consumed by the React dashboard.

Endpoints
---------
GET /                                  -> service info
GET /api/health                        -> health-check
GET /api/leagues                       -> configured leagues + codes
GET /api/streaks                       -> all active streaks
GET /api/streaks?league=PL             -> one league
GET /api/streaks?league=PL,PD,SA       -> several leagues
GET /api/streaks?type=win|draw|loss    -> filter by the dominant streak type
GET /api/streaks?type=points_lost      -> teams currently dropping points
                                           (draws+losses mixed in any order),
                                           sorted by points dropped
GET /api/streaks?min_length=3          -> only streaks of at least N games
GET /api/streaks?refresh=true          -> bypass the cache for this request
GET /api/streaks?format=csv            -> download the (filtered) rows as a CSV file
GET /api/diagnostics                   -> debug view: every provider's
                                           outcome for every league. Not
                                           cached, not called by the
                                           frontend -- open it in a browser
                                           tab when a league's data looks
                                           wrong, don't poll it.

Run locally:
    pip install -r requirements.txt
    python server.py
"""
import csv
import io
import os
import sys
from datetime import date, datetime

# Make sibling imports (config, models, providers.*, ...) resolve
# regardless of the working directory the entrypoint is launched from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, Response
from flask_cors import CORS

from config import LEAGUES, FRONTEND_ORIGIN, STALE_AFTER_DAYS
from dashboard_service import DashboardService, run_diagnostics

app = Flask(__name__)

# The frontend is a separate Vercel deployment (different origin), so CORS
# is required, not optional. Set FRONTEND_ORIGIN once you know your
# production frontend URL; defaults to "*" for local dev.
CORS(app, origins=FRONTEND_ORIGIN)


@app.route("/")
def home():
    return {
        "service": "Football Streaks API",
        "status": "running",
        "endpoints": ["/api/health", "/api/leagues", "/api/streaks", "/api/diagnostics"],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_stale(match_date_str: str) -> bool:
    """True once a streak's most recent match is more than
    STALE_AFTER_DAYS old -- a real possibility now that openfootball (which
    can lag by months for some leagues) sits at the end of every provider
    chain as a last-resort fallback."""
    try:
        match_date = datetime.strptime(match_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False
    return (date.today() - match_date).days > STALE_AFTER_DAYS


def _streak_to_dict(s) -> dict:
    return {
        "league": s.league,
        "league_name": LEAGUES_CODE_TO_NAME.get(s.league, s.league),
        "team": s.team,
        "team_id": s.team_id,
        "crest_url": s.crest_url,
        "streak_type": s.streak_type,
        "streak_length": s.streak_length,
        "goals_for": s.goals_for,
        "goals_against": s.goals_against,
        "goal_difference": s.goal_difference,
        "points_lost_streak": s.points_lost_streak,
        "points_dropped": s.points_dropped,
        "last_opponent": s.last_opponent,
        "last_opponent_crest": s.last_opponent_crest,
        "match_date": s.match_date,
        "is_stale": _is_stale(s.match_date),
    }


LEAGUES_CODE_TO_NAME = {code: name for name, code in LEAGUES.items()}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/leagues")
def leagues():
    return jsonify([{"name": name, "code": code} for name, code in LEAGUES.items()])


@app.route("/api/diagnostics")
def diagnostics():
    return jsonify(run_diagnostics())


@app.route("/api/streaks")
def streaks():
    league_filter = request.args.get("league")              # "PL" or "PL,PD,SA"
    type_filter = request.args.get("type")                   # win | draw | loss | points_lost
    min_length = request.args.get("min_length", type=int)
    force_refresh = request.args.get("refresh") == "true"
    fmt = request.args.get("format")                          # "csv" to download instead of JSON

    try:
        all_streaks = DashboardService.get_all_streaks(force_refresh=force_refresh)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    if league_filter:
        wanted_codes = {code.strip() for code in league_filter.split(",")}
        all_streaks = [s for s in all_streaks if s.league in wanted_codes]

    if type_filter == "points_lost":
        all_streaks = [s for s in all_streaks if s.points_lost_streak > 0]
        if min_length:
            all_streaks = [s for s in all_streaks if s.points_lost_streak >= min_length]
        all_streaks = sorted(all_streaks, key=lambda s: s.points_dropped, reverse=True)
    elif type_filter:
        all_streaks = [s for s in all_streaks if s.streak_type == type_filter]
        if min_length:
            all_streaks = [s for s in all_streaks if s.streak_length >= min_length]
    elif min_length:
        all_streaks = [s for s in all_streaks if s.streak_length >= min_length]

    rows = [_streak_to_dict(s) for s in all_streaks]

    if fmt == "csv":
        return _streaks_csv_response(rows)

    return jsonify(rows)


# ---------------------------------------------------------------------------
# CSV export -- same filtered rows /api/streaks would return, written out as
# a downloadable file instead of JSON. The frontend's "Download CSV" button
# just links straight to /api/streaks?...&format=csv with whatever filters
# are currently active, so this always matches what's on screen.
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "league", "league_name", "team",
    "streak_type", "streak_length",
    "goals_for", "goals_against", "goal_difference",
    "points_lost_streak", "points_dropped",
    "last_opponent", "match_date", "is_stale",
]


def _streaks_csv_response(rows: list[dict]) -> Response:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=streaks.csv"},
    )


# ---------------------------------------------------------------------------
# Dev entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
