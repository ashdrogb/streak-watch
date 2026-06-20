"""
Every data source (football-data.org, OpenLigaDB, API-Football, ...)
implements the same tiny interface so dashboard_service.py can try them
interchangeably without caring which one actually answered.
"""
from models import Match


class FootballDataAPIError(Exception):
    """Raised whenever a provider can't return matches for a league --
    wrong plan, no key configured, rate-limited, league not covered, etc.
    dashboard_service.py catches this to move on to the next provider in
    that league's chain."""


class MatchDataProvider:
    name = "base"

    def get_completed_matches(self, league_code: str) -> list[Match]:
        raise NotImplementedError
