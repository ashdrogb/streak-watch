import requests

from config import API_FOOTBALL_BASE_URL, API_FOOTBALL_KEY, RAPIDAPI_KEY, HTTP_TIMEOUT_SECONDS
from models import Match
from providers.base import MatchDataProvider, FootballDataAPIError
from season_util import current_season_start_year

# Same underlying API-Football data, sold through two different gateways.
# A key issued by one will NOT authenticate against the other -- that
# mismatch is a common silent-failure trap, and exactly what was happening
# here: a RapidAPI-issued key was being sent as `x-apisports-key` to
# v3.football.api-sports.io, which doesn't recognize RapidAPI keys at all.
RAPIDAPI_BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"
RAPIDAPI_HOST = "api-football-v1.p.rapidapi.com"


class ApiFootballProvider(MatchDataProvider):
    """
    API-Football's free plan (100 req/day, every competition it lists)
    fills the gap for League One, League Two, Segunda División and Ligue 2.
    It's available two ways:

      - Direct, via api-sports.io / dashboard.api-football.com
        -> header `x-apisports-key`, base URL v3.football.api-sports.io
      - Resold through the RapidAPI marketplace
        -> headers `x-rapidapi-key` + `x-rapidapi-host`,
           base URL api-football-v1.p.rapidapi.com/v3

    This provider auto-detects which one you have: set RAPIDAPI_KEY to use
    the RapidAPI route, or API_FOOTBALL_KEY for the direct route. If both
    are set, RapidAPI takes priority.

    League ids are resolved by name+country via /leagues and cached on the
    instance, rather than hard-coded -- API-Football's numeric ids aren't
    published anywhere stable enough to bake in without risking a silent
    mismatch.
    """

    name = "api_football"

    # (name, country) exactly as API-Football's /leagues endpoint expects.
    LEAGUE_LOOKUP = {
        "PL":  ("Premier League", "England"),
        "EL1": ("League One", "England"),
        "EL2": ("League Two", "England"),
        "PD":  ("La Liga", "Spain"),
        "SD":  ("Segunda Division", "Spain"),
        "BL1": ("Bundesliga", "Germany"),
        "BL2": ("2. Bundesliga", "Germany"),
        "SA":  ("Serie A", "Italy"),
        "FL1": ("Ligue 1", "France"),
        "FL2": ("Ligue 2", "France"),
    }

    def __init__(self, api_key: str = None, rapidapi_key: str = None, timeout: int = None):
        self.rapidapi_key = rapidapi_key if rapidapi_key is not None else RAPIDAPI_KEY
        self.api_key = api_key if api_key is not None else API_FOOTBALL_KEY
        self.timeout = timeout or HTTP_TIMEOUT_SECONDS
        self._league_id_cache: dict = {}

    @property
    def _via_rapidapi(self) -> bool:
        return bool(self.rapidapi_key)

    def _base_url(self) -> str:
        return RAPIDAPI_BASE_URL if self._via_rapidapi else API_FOOTBALL_BASE_URL

    def _headers(self):
        if self._via_rapidapi:
            return {"x-rapidapi-key": self.rapidapi_key, "x-rapidapi-host": RAPIDAPI_HOST}
        return {"x-apisports-key": self.api_key}

    def _get(self, path: str, params: dict) -> dict:
        try:
            response = requests.get(
                f"{self._base_url()}{path}",
                headers=self._headers(),
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise FootballDataAPIError(f"api-football: network error ({exc})") from exc

        if response.status_code == 429:
            raise FootballDataAPIError("api-football: daily request quota reached")
        if response.status_code in (401, 403):
            gateway = "RapidAPI" if self._via_rapidapi else "api-sports.io"
            raise FootballDataAPIError(
                f"api-football: {response.status_code} from the {gateway} gateway "
                f"-- this key doesn't match that gateway"
            )
        if not response.ok:
            raise FootballDataAPIError(f"api-football: returned {response.status_code}")

        return response.json()

    def _resolve_league_id(self, league_code: str) -> int:
        if league_code in self._league_id_cache:
            return self._league_id_cache[league_code]

        lookup = self.LEAGUE_LOOKUP.get(league_code)
        if not lookup:
            raise FootballDataAPIError(f"{league_code}: not in ApiFootballProvider.LEAGUE_LOOKUP")
        name, country = lookup

        data = self._get("/leagues", {"name": name, "country": country})
        results = data.get("response", [])
        if not results:
            raise FootballDataAPIError(
                f"{league_code}: api-football has no league matching '{name}' ({country})"
            )

        league_id = results[0]["league"]["id"]
        self._league_id_cache[league_code] = league_id
        return league_id

    def get_completed_matches(self, league_code: str) -> list[Match]:
        if not self.rapidapi_key and not self.api_key:
            raise FootballDataAPIError("Neither RAPIDAPI_KEY nor API_FOOTBALL_KEY is set")

        league_id = self._resolve_league_id(league_code)
        season = current_season_start_year()

        data = self._get(
            "/fixtures",
            {"league": league_id, "season": season, "status": "FT"},
        )

        matches = []
        for raw in data.get("response", []):
            goals = raw.get("goals", {})
            home_goals, away_goals = goals.get("home"), goals.get("away")
            if home_goals is None or away_goals is None:
                continue

            home, away = raw["teams"]["home"], raw["teams"]["away"]
            fixture_date = raw.get("fixture", {}).get("date", "")

            matches.append(
                Match(
                    league=league_code,
                    date=fixture_date[:10],
                    home_team=home["name"],
                    home_team_id=home["id"],
                    home_crest=home.get("logo", ""),
                    home_score=home_goals,
                    away_team=away["name"],
                    away_team_id=away["id"],
                    away_crest=away.get("logo", ""),
                    away_score=away_goals,
                )
            )

        return matches

