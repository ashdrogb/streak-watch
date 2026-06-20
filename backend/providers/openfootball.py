import zlib

import requests

from config import HTTP_TIMEOUT_SECONDS
from models import Match
from providers.base import MatchDataProvider, FootballDataAPIError
from season_util import current_season_label, previous_season_label

RAW_BASE_URL = "https://raw.githubusercontent.com/openfootball/football.json/master"


class OpenFootballProvider(MatchDataProvider):
    """
    https://github.com/openfootball/football.json -- free, no key, no
    signup: static JSON files maintained by volunteers, one per
    league/season. Listed LAST in every provider chain, for two reasons
    confirmed by actually pulling the live files rather than assuming:

    1. There are no team ids or crests in this dataset at all -- team_id
       below is a stable hash of the team name (not Python's built-in
       hash(), which is randomised per-process), and crest_url is always
       "" (the frontend already renders a placeholder for that).

    2. Freshness varies a lot by league. The five flagship leagues (PL,
       La Liga, Bundesliga, Serie A, Ligue 1) are kept fully current
       through the end of the season. The five second-tier leagues this
       project actually needs a backup for are not: as of building this,
       Segunda División and 2. Bundesliga hadn't been updated since
       roughly November, and League Two since roughly December -- months
       stale. That makes this a "better than a blank league" fallback,
       not a reliable live source, which is also why server.py flags any
       streak whose match_date is more than STALE_AFTER_DAYS old.
    """

    name = "openfootball"

    FILE_BY_CODE = {
        "PL":  "en.1.json",
        "EL1": "en.3.json",
        "EL2": "en.4.json",
        "PD":  "es.1.json",
        "SD":  "es.2.json",
        "BL1": "de.1.json",
        "BL2": "de.2.json",
        "SA":  "it.1.json",
        "FL1": "fr.1.json",
        "FL2": "fr.2.json",
    }

    def __init__(self, timeout: int = None):
        self.timeout = timeout or HTTP_TIMEOUT_SECONDS

    @staticmethod
    def _team_id(name: str) -> int:
        return zlib.crc32(name.encode("utf-8"))

    @staticmethod
    def _final_score(raw_score):
        """Handles all three shapes seen in the live data: a {"ft": [h,a],
        "ht": [h,a]} dict, a flat [h, a] list (matches with no recorded
        half-time score), or no "score" key at all (not played yet)."""
        if raw_score is None:
            return None, None
        if isinstance(raw_score, dict):
            raw_score = raw_score.get("ft")
        if not isinstance(raw_score, list) or len(raw_score) != 2:
            return None, None
        return raw_score[0], raw_score[1]

    def _fetch_season_file(self, season_label: str, filename: str):
        url = f"{RAW_BASE_URL}/{season_label}/{filename}"
        try:
            response = requests.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise FootballDataAPIError(f"openfootball: network error ({exc})") from exc

        if response.status_code == 404:
            return None
        if not response.ok:
            raise FootballDataAPIError(f"openfootball: returned {response.status_code}")
        return response.json()

    def get_completed_matches(self, league_code: str) -> list[Match]:
        filename = self.FILE_BY_CODE.get(league_code)
        if not filename:
            raise FootballDataAPIError(f"{league_code}: not in OpenFootballProvider.FILE_BY_CODE")

        # Try the current season's file first, then last season's, in case
        # the new season's file hasn't been created yet (e.g. mid-summer).
        payload = self._fetch_season_file(current_season_label(), filename)
        if payload is None:
            payload = self._fetch_season_file(previous_season_label(), filename)
        if payload is None:
            raise FootballDataAPIError(f"{league_code}: no openfootball season file found")

        matches = []
        for raw in payload.get("matches", []):
            home_goals, away_goals = self._final_score(raw.get("score"))
            if home_goals is None:
                continue

            team1, team2 = raw.get("team1", ""), raw.get("team2", "")
            matches.append(
                Match(
                    league=league_code,
                    date=raw.get("date", ""),
                    home_team=team1,
                    home_team_id=self._team_id(team1),
                    home_crest="",
                    home_score=home_goals,
                    away_team=team2,
                    away_team_id=self._team_id(team2),
                    away_crest="",
                    away_score=away_goals,
                )
            )

        return matches
