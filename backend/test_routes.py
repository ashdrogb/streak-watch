import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from models import TeamStreak

OLD_DATE = "2026-05-10"                                     # > 21 days before "today" in this sandbox
FRESH_DATE = date.today().strftime("%Y-%m-%d")               # today -- never stale

fake_streaks = [
    TeamStreak("PD", "Real Madrid", 1, "", "win", 4, 9, 2, 7, 0, 0, "Sevilla", "", OLD_DATE),
    TeamStreak("PL", "Wolves", 2, "", "loss", 3, 1, 6, -5, 3, 9, "Chelsea", "", "2026-05-09"),
    TeamStreak("PL", "City", 3, "", "loss", 1, 0, 2, -2, 2, 5, "Burnley", "", "2026-05-08"),
    TeamStreak("FL2", "Troyes", 4, "", "draw", 2, 2, 2, 0, 2, 4, "Laval", "", "2026-05-07"),
    TeamStreak("SA", "Inter", 5, "", "win", 2, 4, 0, 4, 0, 0, "Roma", "", FRESH_DATE),
]

with patch("dashboard_service.DashboardService.get_all_streaks", return_value=fake_streaks):
    import server
    client = server.app.test_client()

    r = client.get("/api/health")
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}
    print("GET /api/health OK")

    r = client.get("/api/leagues")
    leagues = r.get_json()
    assert {"name": "Ligue 2", "code": "FL2"} in leagues
    assert len(leagues) == 10
    print("GET /api/leagues OK (", len(leagues), "leagues )")

    r = client.get("/api/streaks")
    data = r.get_json()
    assert len(data) == 5
    assert data[0]["league_name"] == "La Liga"
    print("GET /api/streaks (no filter) OK")

    by_team = {d["team"]: d for d in data}
    assert by_team["Real Madrid"]["is_stale"] is True
    assert by_team["Inter"]["is_stale"] is False
    print("GET /api/streaks: is_stale correctly flags an old match_date and not today's")

    r = client.get("/api/streaks?league=PL")
    data = r.get_json()
    assert {d["team"] for d in data} == {"Wolves", "City"}
    print("GET /api/streaks?league=PL OK")

    r = client.get("/api/streaks?league=PL,FL2")
    data = r.get_json()
    assert {d["team"] for d in data} == {"Wolves", "City", "Troyes"}
    print("GET /api/streaks?league=PL,FL2 OK")

    r = client.get("/api/streaks?type=loss")
    data = r.get_json()
    assert {d["team"] for d in data} == {"Wolves", "City"}
    print("GET /api/streaks?type=loss OK")

    r = client.get("/api/streaks?type=loss&min_length=2")
    data = r.get_json()
    assert {d["team"] for d in data} == {"Wolves"}
    print("GET /api/streaks?type=loss&min_length=2 OK")

    r = client.get("/api/streaks?type=points_lost")
    data = r.get_json()
    # sorted by points_dropped desc: Wolves(9) > City(5) > Troyes(4)
    assert [d["team"] for d in data] == ["Wolves", "City", "Troyes"]
    print("GET /api/streaks?type=points_lost OK (sorted by points_dropped)")

    r = client.get("/api/streaks?format=csv")
    assert r.status_code == 200
    assert r.mimetype == "text/csv"
    assert r.headers["Content-Disposition"] == "attachment; filename=streaks.csv"
    lines = r.get_data(as_text=True).strip().splitlines()
    assert lines[0].split(",")[:3] == ["league", "league_name", "team"]
    assert len(lines) == 1 + len(fake_streaks)   # header + one row per streak
    print("GET /api/streaks?format=csv OK (", len(lines) - 1, "rows )")

    r = client.get("/api/streaks?league=PL&format=csv")
    lines = r.get_data(as_text=True).strip().splitlines()
    assert len(lines) == 1 + 2   # header + Wolves + City, same filter as JSON
    print("GET /api/streaks?league=PL&format=csv OK (filters apply to CSV too)")

# --- /api/diagnostics --------------------------------------------------
# Mocked at the provider level (not HTTP) so this test doesn't depend on
# dashboard_service's internal provider-resolution wiring, just on
# run_diagnostics() correctly reporting each attempt's outcome.
def fake_get_provider(name):
    provider = MagicMock()
    if name == "football_data_org":
        provider.get_completed_matches.side_effect = Exception("FOOTBALL_DATA_API_KEY is not set")
    elif name == "openligadb":
        provider.get_completed_matches.return_value = [MagicMock()] * 9
    else:
        provider.get_completed_matches.return_value = [MagicMock()] * 5
    return provider

with patch("dashboard_service.get_provider", side_effect=fake_get_provider):
    import server
    client = server.app.test_client()
    r = client.get("/api/diagnostics")
    report = r.get_json()

    assert len(report) == 10
    bl1 = next(entry for entry in report if entry["code"] == "BL1")
    providers_tried = [a["provider"] for a in bl1["attempts"]]
    assert providers_tried == ["football_data_org", "openligadb", "openfootball"]
    assert bl1["attempts"][0]["ok"] is False
    assert "not set" in bl1["attempts"][0]["error"]
    assert bl1["attempts"][1]["ok"] is True and bl1["attempts"][1]["matches_found"] == 9
    print("GET /api/diagnostics OK: reports every provider in the chain, not just the first")

print("\nAll route tests passed.")
