"""
Central configuration: which leagues we track, which data provider(s) to
try for each one, and environment-driven settings (API keys, cache TTL).

Why a provider *chain* per league instead of one fixed provider:
football-data.org's free plan only covers 5 of our 10 leagues. Rather than
hard-failing on the other 5, each league lists its providers in priority
order; dashboard_service.py walks the list and uses the first one that
responds successfully. See providers/ for each provider's implementation.
"""
import os

try:
    # Loads backend/.env for local development. A no-op in production
    # (Vercel) since there's no .env file there -- real values come from
    # the project's Environment Variables instead.
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Leagues
# ---------------------------------------------------------------------------
# Display name -> official football-data.org competition code.
# (Codes confirmed against https://docs.football-data.org/general/v4/lookup_tables.html)
LEAGUES = {
    "Premier League":   "PL",
    "EFL League One":   "EL1",
    "EFL League Two":   "EL2",
    "La Liga":          "PD",
    "Segunda División": "SD",
    "Bundesliga":       "BL1",
    "2. Bundesliga":    "BL2",
    "Serie A":          "SA",
    "Ligue 1":          "FL1",
    "Ligue 2":          "FL2",
}

CODE_TO_NAME = {code: name for name, code in LEAGUES.items()}

# Provider priority per league code. "football_data_org" only actually
# succeeds for PL / PD / BL1 / SA / FL1 unless you're on a paid plan there.
# "openfootball" is listed last everywhere as a no-key safety net, but it's
# meaningfully stale for the five second-tier leagues (see
# providers/openfootball.py) -- it's there so a league shows *something*
# rather than nothing if every keyed provider is down, not as a fix for
# missing/broken keys. Get those working first; check GET /api/diagnostics
# to see exactly which provider is failing for which league and why.
LEAGUE_PROVIDER_CHAIN = {
    "PL":  ["football_data_org", "openfootball"],
    "PD":  ["football_data_org", "openfootball"],
    "BL1": ["football_data_org", "openligadb", "openfootball"],
    "SA":  ["football_data_org", "openfootball"],
    "FL1": ["football_data_org", "openfootball"],
    "EL1": ["api_football", "football_data_org", "openfootball"],
    "EL2": ["api_football", "football_data_org", "openfootball"],
    "SD":  ["api_football", "football_data_org", "openfootball"],
    "BL2": ["openligadb", "football_data_org", "openfootball"],
    "FL2": ["api_football", "football_data_org", "openfootball"],
}

# ---------------------------------------------------------------------------
# Provider credentials / endpoints
# ---------------------------------------------------------------------------
FOOTBALL_DATA_ORG_BASE_URL = "https://api.football-data.org/v4"
FOOTBALL_DATA_ORG_API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "")

OPENLIGADB_BASE_URL = "https://api.openligadb.de"

API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")

# Same API-Football data, resold through the RapidAPI marketplace under a
# different gateway/auth scheme. Set this instead of API_FOOTBALL_KEY if
# that's where you signed up -- see providers/api_football.py for why the
# two aren't interchangeable.
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
# EL1, EL2, SD and FL2 all try api_football first (BL2 prefers the
# keyless openligadb instead), so each full scan can cost up to 4 calls to
# API-Football's free plan, which is capped at 100/day:
#
#   scans/day = 86400 / CACHE_TTL_SECONDS
#   api-football calls/day ~= scans/day * 4   <- must stay well under 100
#
# 900s (15 min) was the original default but that's 96 scans/day = ~384
# calls/day -- nearly 4x the free quota. 10800s (3 hours) keeps it at
# ~8 scans/day = ~32 calls/day, leaving headroom for manual `?refresh=true`
# calls and the one-time league-id lookups. Don't go below ~1800s (30 min)
# unless you've upgraded the API-Football plan.
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", str(3 * 60 * 60)))
HTTP_TIMEOUT_SECONDS = int(os.environ.get("HTTP_TIMEOUT_SECONDS", "10"))
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")

# A streak whose match_date is older than this gets is_stale=true in the
# API response, regardless of which provider supplied it -- relevant now
# that openfootball (which can lag by months for some leagues) is in every
# chain as a last-resort fallback.
STALE_AFTER_DAYS = int(os.environ.get("STALE_AFTER_DAYS", "21"))
