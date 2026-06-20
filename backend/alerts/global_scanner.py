"""
See league_scanner.py for context -- this is the "loop every league"
counterpart to LeagueScanner.find_loss_streaks, not currently wired into
any route.
"""
from config import LEAGUES
from providers.base import FootballDataAPIError
from dashboard_service import fetch_league_matches
from alerts.league_scanner import LeagueScanner


class GlobalScanner:

    @staticmethod
    def scan_all_leagues(threshold=5):

        alerts = []

        for league_name, league_code in LEAGUES.items():
            try:
                matches, provider_name = fetch_league_matches(league_code)
                alerts.extend(LeagueScanner.find_loss_streaks(matches, threshold))
            except FootballDataAPIError as e:
                print(f"Skipped {league_name}: {e}")
            except Exception as e:
                print(f"Failed to scan {league_name}: {e}")

        return alerts
