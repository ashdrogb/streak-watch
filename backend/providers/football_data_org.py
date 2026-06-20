import requests

from config import FOOTBALL_DATA_ORG_BASE_URL, FOOTBALL_DATA_ORG_API_KEY, HTTP_TIMEOUT_SECONDS
from models import Match
from providers.base import MatchDataProvider, FootballDataAPIError


class FootballDataOrgProvider(MatchDataProvider):
    """
    https://www.football-data.org -- the free plan covers 12 competitions
    (PL, PD, BL1, SA, FL1, DED, PPL, ELC, CL, EC, WC, BSA). League One,
    League Two, Segunda División, 2. Bundesliga and Ligue 2 need a paid
    plan there, which is why those five list a different provider first
    in config.LEAGUE_PROVIDER_CHAIN.
    """

    name = "football_data_org"

    def __init__(self, api_key: str = None, timeout: int = None):
        self.api_key = api_key if api_key is not None else FOOTBALL_DATA_ORG_API_KEY
        self.timeout = timeout or HTTP_TIMEOUT_SECONDS

    def _headers(self):
        return {"X-Auth-Token": self.api_key} if self.api_key else {}

    def get_completed_matches(self, league_code: str) -> list[Match]:
        if not self.api_key:
            raise FootballDataAPIError(
                f"{league_code}: FOOTBALL_DATA_API_KEY is not set"
            )

        url = f"{FOOTBALL_DATA_ORG_BASE_URL}/competitions/{league_code}/matches"

        try:
            response = requests.get(
                url,
                headers=self._headers(),
                params={"status": "FINISHED"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise FootballDataAPIError(f"{league_code}: network error ({exc})") from exc

        if response.status_code == 429:
            reset = response.headers.get("X-RequestCounter-Reset", "?")
            raise FootballDataAPIError(
                f"{league_code}: rate-limited by football-data.org (resets in {reset}s)"
            )
        if response.status_code == 403:
            raise FootballDataAPIError(
                f"{league_code}: not included in this football-data.org plan"
            )
        if not response.ok:
            raise FootballDataAPIError(
                f"{league_code}: football-data.org returned {response.status_code}"
            )

        payload = response.json()
        matches = []

        for raw in payload.get("matches", []):
            score = raw.get("score", {}).get("fullTime", {})
            home_goals, away_goals = score.get("home"), score.get("away")

            # Defends against malformed/incomplete records; shouldn't
            # normally trigger for status=FINISHED.
            if home_goals is None or away_goals is None:
                continue

            matches.append(
                Match(
                    league=league_code,
                    date=raw["utcDate"][:10],
                    home_team=raw["homeTeam"]["name"],
                    home_team_id=raw["homeTeam"]["id"],
                    home_crest=raw["homeTeam"].get("crest", ""),
                    home_score=home_goals,
                    away_team=raw["awayTeam"]["name"],
                    away_team_id=raw["awayTeam"]["id"],
                    away_crest=raw["awayTeam"].get("crest", ""),
                    away_score=away_goals,
                )
            )

        return matches
