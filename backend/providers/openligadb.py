import requests

from config import OPENLIGADB_BASE_URL, HTTP_TIMEOUT_SECONDS
from models import Match
from providers.base import MatchDataProvider, FootballDataAPIError
from season_util import current_season_start_year


class OpenLigaDBProvider(MatchDataProvider):
    """
    https://api.openligadb.de -- free, no API key, no signup. German
    football only, but that's exactly the gap football-data.org's free
    plan leaves for 2. Bundesliga (and it's a perfectly good alternative
    for Bundesliga itself too).

    Docs: https://github.com/OpenLigaDB/OpenLigaDB-Samples
    """

    name = "openligadb"

    SHORTCUTS = {
        "BL1": "bl1",
        "BL2": "bl2",
    }

    def __init__(self, timeout: int = None):
        self.timeout = timeout or HTTP_TIMEOUT_SECONDS

    @staticmethod
    def _final_score(raw: dict) -> tuple:
        results = raw.get("matchResults") or []
        if not results:
            return None, None
        # resultTypeID 2 is the official "Endergebnis" (final result); fall
        # back to the last entry if that type isn't present for some reason.
        final = next((r for r in results if r.get("resultTypeID") == 2), results[-1])
        return final.get("pointsTeam1"), final.get("pointsTeam2")

    def get_completed_matches(self, league_code: str) -> list[Match]:
        shortcut = self.SHORTCUTS.get(league_code)
        if not shortcut:
            raise FootballDataAPIError(
                f"{league_code}: OpenLigaDB only covers {list(self.SHORTCUTS)}"
            )

        season = current_season_start_year()
        url = f"{OPENLIGADB_BASE_URL}/getmatchdata/{shortcut}/{season}"

        try:
            response = requests.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise FootballDataAPIError(f"{league_code}: network error ({exc})") from exc

        if not response.ok:
            raise FootballDataAPIError(
                f"{league_code}: OpenLigaDB returned {response.status_code}"
            )

        matches = []
        for raw in response.json():
            if not raw.get("matchIsFinished"):
                continue

            home_goals, away_goals = self._final_score(raw)
            if home_goals is None or away_goals is None:
                continue

            team1, team2 = raw.get("team1", {}), raw.get("team2", {})
            raw_date = raw.get("matchDateTimeUTC") or raw.get("matchDateTime", "")

            matches.append(
                Match(
                    league=league_code,
                    date=raw_date[:10],
                    home_team=team1.get("teamName", "Unknown"),
                    home_team_id=team1.get("teamId", 0),
                    home_crest=team1.get("teamIconUrl", ""),
                    home_score=home_goals,
                    away_team=team2.get("teamName", "Unknown"),
                    away_team_id=team2.get("teamId", 0),
                    away_crest=team2.get("teamIconUrl", ""),
                    away_score=away_goals,
                )
            )

        return matches
