# Streak Watch

A Flask + React dashboard that scans completed matches across Europe's top
ten divisions and surfaces every team currently on a win, draw, or loss
streak -- plus a "points lost" view for teams quietly bleeding points across
mixed losses and draws, with goals for/against/difference for each streak.

```
┌──────────────────────┐        ┌───────────────────────┐        ┌────────────────────────────┐
│  React (Vite)         │  CORS  │  Flask API              │       │  football-data.org           │
│  frontend/             │ ─────▶│  backend/                │ ─────▶│  API-Football                 │
│  Vercel project #1     │        │  Vercel project #2      │       │  OpenLigaDB                   │
└──────────────────────┘        └───────────────────────┘        │  openfootball (no key)        │
                                                                    └────────────────────────────┘
```

Two separate Vercel projects from one repo, talking over CORS -- not one
combined deployment. That's deliberate: `flask-cors` is only needed if the
frontend and backend genuinely live on different origins, and keeping them
as separate projects means each can be redeployed, scaled, or swapped
independently (e.g. moving the backend off Vercel later costs you one
environment variable change on the frontend, not a rewrite).

## Why four data providers

football-data.org's free plan is free forever but only covers 12
competitions, and five of your ten leagues aren't on that list (England's
League One/Two, Spain's Segunda División, Germany's 2. Bundesliga, France's
Ligue 2). Rather than make those five leagues fail outright, each league in
`backend/config.py` lists its data sources in priority order, and
`dashboard_service.py` walks the list until one responds:

| League | Code | Provider order | Why |
|---|---|---|---|
| Premier League | `PL` | football-data.org → openfootball | free tier covers it |
| La Liga | `PD` | football-data.org → openfootball | free tier covers it |
| Bundesliga | `BL1` | football-data.org → OpenLigaDB → openfootball | free tier covers it; OpenLigaDB as a no-key backup |
| Serie A | `SA` | football-data.org → openfootball | free tier covers it |
| Ligue 1 | `FL1` | football-data.org → openfootball | free tier covers it |
| EFL League One | `EL1` | API-Football → football-data.org → openfootball | not on football-data.org's free tier |
| EFL League Two | `EL2` | API-Football → football-data.org → openfootball | not on football-data.org's free tier |
| Segunda División | `SD` | API-Football → football-data.org → openfootball | not on football-data.org's free tier |
| 2. Bundesliga | `BL2` | OpenLigaDB → football-data.org → openfootball | OpenLigaDB covers German football for free, no key |
| Ligue 2 | `FL2` | API-Football → football-data.org → openfootball | not on football-data.org's free tier |

If a league's whole provider chain fails for a given scan (an outage, a
missing key, a quota hit), `dashboard_service.py` logs it and the other
leagues still load -- the dashboard never goes fully blank over one bad
league. football-data.org is listed as a fallback for the second-tier
leagues too, in case you ever upgrade that plan to cover everything.

**`openfootball` is a genuine no-key, no-signup safety net** (static JSON
from https://github.com/openfootball/football.json), listed last
everywhere -- it's there so a league shows *something* rather than nothing
when both keyed providers are down, not as a fix for missing/broken keys.
It's also not equally fresh for every league. I actually fetched all ten
files to check (`python resolve_openfootball_paths.py` reproduces this):

```
PL/PD/BL1/SA/FL1 (the five football-data.org leagues): current through
  mid-to-late May 2026 -- the season had just finished.
EL1/EL2 (League One/Two):        latest finished match  2025-12-29
SD/BL2/FL2 (Segunda, 2. BL, L2):  latest finished match  2025-11-02/03
```

So for the five second-tier leagues, this fallback can be five to seven
months behind. Every streak's `is_stale` field (true once its match is
more than `STALE_AFTER_DAYS`, default 21, old) exists specifically to
surface that rather than let an old streak masquerade as current -- the
frontend shows a "data may be outdated" badge on those cards. Treat
`openfootball` filling in for a league as a sign to go fix that league's
real key, not as the fix itself.

## Getting your free API keys

I can't generate working keys for you -- they're tied to an account on each
provider's side -- but all three below are free to sign up for in a couple
of minutes:

| Provider | Free tier | Sign up |
|---|---|---|
| **football-data.org** | Free forever, 10 requests/min, 12 competitions | https://www.football-data.org/client/register |
| **API-Football** (api-sports.io) | Free, 100 requests/day, *every* competition it lists | https://dashboard.api-football.com/register (or via RapidAPI: https://rapidapi.com/api-sports/api/api-football) |
| **OpenLigaDB** | Free, no signup, no key at all | nothing to do -- it's already wired up |
| **openfootball** | Free, no signup, no key at all | nothing to do -- it's already wired up (see the freshness caveat above) |

Put the first two into `backend/.env` (copy `backend/.env.example`):

```
FOOTBALL_DATA_API_KEY=your-football-data-org-key
API_FOOTBALL_KEY=your-api-football-key
```

**If you got your API-Football key through RapidAPI's marketplace listing**
rather than signing up directly at api-football.com, put it in
`RAPIDAPI_KEY` instead of `API_FOOTBALL_KEY` -- the two are different
gateways with different auth (`x-rapidapi-key` + a `api-football-v1.p.rapidapi.com`
host, vs `x-apisports-key` + `v3.football.api-sports.io`), and a key from
one will silently fail (401/403) against the other. `providers/api_football.py`
auto-detects which one you've set; if both are present, `RAPIDAPI_KEY` wins.

The app runs without either API-Football key -- you'll just lose League One,
League Two, Segunda División and Ligue 2 (2. Bundesliga still works via
OpenLigaDB) until you add one.

### Mind API-Football's 100/day cap

Four leagues (`EL1`, `EL2`, `SD`, `FL2`) try API-Football first. Each full
scan costs up to 4 calls there, and results are cached for
`CACHE_TTL_SECONDS` (3 hours by default) before the next scan re-hits any
provider:

```
scans/day = 86400 / CACHE_TTL_SECONDS
API-Football calls/day ≈ scans/day × 4   (must stay under 100)
```

3 hours → ~8 scans/day → ~32 calls/day, comfortable headroom. Don't drop
`CACHE_TTL_SECONDS` below ~1800 (30 min) unless you've upgraded that plan,
or you'll burn the quota before the day's half over and those four leagues
will silently fall back to football-data.org (which, on the free plan,
doesn't cover them either, so they'll just disappear from the dashboard
until the quota resets at 00:00 UTC).

### A league isn't loading -- check `/api/diagnostics` first

Once it's deployed (or running locally), open
`<your-backend-url>/api/diagnostics` directly in a browser. It tries
*every* provider in a league's chain (not just the first one) and reports
each attempt's real outcome -- "FOOTBALL_DATA_API_KEY is not set", "403
from the RapidAPI gateway", "openfootball returned 404", etc. -- rather
than you having to dig through deployment logs or guess. It's not cached
and the frontend never calls it, so it's safe to refresh as often as
you're debugging, just don't poll it automatically (each call is a real
request to every provider for every league).

## Local development

**Backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
python server.py        # http://localhost:5000
```

Run the test suite (no API keys or network needed -- everything's mocked):

```bash
python test_season_util.py    # season-label/start-year math across boundaries
python test_streak_logic.py   # streak/points-lost/GF-GA-GD math, no HTTP at all
python test_providers.py      # each provider's JSON parsing
python test_fallback.py       # provider chain fallback + alerts/ package
python test_routes.py         # Flask routes end-to-end against fake data, incl. CSV export
```

**Frontend** (separate terminal):

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api/* to :5000
```

## Deploying to Vercel

Two projects from the same GitHub repo:

**1. Backend** -- New Project → import the repo → set **Root Directory** to
`backend`. Vercel auto-detects Flask from `requirements.txt` and deploys
`server.py` zero-config. Add environment variables: `FOOTBALL_DATA_API_KEY`,
`API_FOOTBALL_KEY`, and once you know the frontend's URL, `FRONTEND_ORIGIN`
(e.g. `https://streak-watch.vercel.app`) to lock CORS down from the `*`
default.

**2. Frontend** -- New Project → import the same repo again → set **Root
Directory** to `frontend`. Vercel auto-detects Vite. Add one environment
variable: `VITE_API_URL` set to the backend project's URL plus `/api`
(e.g. `https://streak-watch-api.vercel.app/api`).

Redeploy the frontend after setting `VITE_API_URL` (Vite bakes env vars in
at build time, so it won't pick up a var added after the fact without a
new build).

## API reference

| Endpoint | Notes |
|---|---|
| `GET /api/health` | `{"status": "ok"}` |
| `GET /api/leagues` | `[{"name": "Premier League", "code": "PL"}, ...]` |
| `GET /api/streaks` | All teams' current streaks |
| `GET /api/streaks?league=PL` | One league (also accepts `PL,PD,SA`) |
| `GET /api/streaks?type=win\|draw\|loss` | Filter by the dominant streak type |
| `GET /api/streaks?type=points_lost` | Teams currently dropping points (draws+losses mixed in any order), sorted by points actually dropped |
| `GET /api/streaks?min_length=3` | Only streaks of at least N games |
| `GET /api/streaks?refresh=true` | Bypass the cache for this one request |
| `GET /api/streaks?format=csv` | Same filters, returned as a downloadable CSV instead of JSON |
| `GET /api/diagnostics` | Every provider's real outcome for every league -- not cached, see above |

Each streak object:

```json
{
  "league": "PD", "league_name": "La Liga",
  "team": "Real Madrid", "team_id": 86, "crest_url": "...",
  "streak_type": "win", "streak_length": 4,
  "goals_for": 9, "goals_against": 2, "goal_difference": 7,
  "points_lost_streak": 0, "points_dropped": 0,
  "last_opponent": "Sevilla", "last_opponent_crest": "...",
  "match_date": "2026-05-10", "is_stale": false
}
```

`goals_for/against/difference` cover the `streak_length` matches that make
up the active streak. `points_lost_streak` is a separate lens: it counts
consecutive *non-win* matches regardless of whether they're all losses, all
draws, or a mix (e.g. `L, D, L` is a 3-match, 8-point-dropped run that
`streak_type`/`streak_length` alone would never surface, since that field
only tracks single-result runs). `points_dropped` is points lost relative to
winning every one of those games (loss = -3, draw = -2). `is_stale` is true
once `match_date` is more than `STALE_AFTER_DAYS` (default 21) old --
relevant now that `openfootball` can sit behind a multi-month-stale league.

## Downloading a CSV

The "Download CSV" button (next to the min-streak stepper) exports exactly
what's currently on screen -- whatever league/type/min-length filters are
active -- with a filename like
`streak-watch_PL-PD_loss_min3_2026-06-18.csv`. It's generated client-side
from the data already loaded (`frontend/src/csv.js`), so it's instant and
costs no extra request. If you want a filtered CSV without opening the UI
at all -- for a script, or a saved bookmark -- hit the backend directly,
e.g. `GET /api/streaks?type=loss&min_length=3&format=csv`; it applies the
exact same filters as the JSON endpoint.

## What changed from the original files

The upload had three near-duplicate "loop every league and scan it"
functions (`DashboardService.get_all_streaks`, `GlobalStreakScanner.scan`,
and the loss-only `GlobalScanner.scan_all_leagues`) plus a few missing
pieces (`Match` and `LossStreakAlert` weren't defined anywhere, `models.py`
was missing its `dataclass` import, and `server.py`/`dashboard_service.py`
referenced `FootballDataCollector`/`LEAGUES`/Flask imports that didn't
exist in the upload). This version:

- Collapses the three duplicates into one `DashboardService`, with the
  loss-streak-alert half moved to `alerts/` (kept for a possible future
  notifications feature, not currently called by any route).
- Adds the missing `Match`/`LossStreakAlert` dataclasses and fixes every
  import.
- Replaces the single `FootballDataCollector` with three real provider
  implementations behind a common interface, plus the per-league fallback
  chain above.
- Extends `TeamStreak` with `goals_for/against/difference` and
  `points_lost_streak`/`points_dropped`, computed in `streak_scanner.py`
  from a single sorted match log per team (`team_results.py`) so the
  results and the goals can never drift out of sync with each other.
- Adds a TTL cache (`cache.py`) so a page load -- or the league/type
  filters, which are applied to the cached list -- doesn't re-hit either
  provider API on every request.

`streak_engine.py` (win/draw/loss/unbeaten/winless streak counting) is
untouched from the original upload; `points_lost_streak_length()` is
literally an alias for the `current_winless_streak()` that was already
there.

**Added after the initial build**, in response to League One/Two/Segunda/
2.Bundesliga/Ligue 2 not loading even with both keyed providers configured:
a fourth provider (`providers/openfootball.py`, no key/signup) at the end
of every chain as a last resort; `GET /api/diagnostics`, which actually
calls every provider in a league's chain and reports each one's real
outcome instead of you guessing from logs; an `is_stale` flag on every
streak so a stale fallback can't masquerade as live data; and the CSV
export (button in the UI, `?format=csv` on the backend).

## Possible next step

`alerts/global_scanner.py` and `alerts/league_scanner.py` are fully working
but not wired into any route -- they're the basis for a "notify me when a
team's loss streak crosses N" feature (Telegram, email, whatever), e.g. as a
Vercel Cron job that calls `GlobalScanner.scan_all_leagues()` once a day and
diffs against `SentAlert` records to avoid re-notifying on the same streak.
