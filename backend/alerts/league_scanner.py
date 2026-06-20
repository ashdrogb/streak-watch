"""
Kept from the original upload for a future notifications feature (e.g. a
cron-triggered Telegram/email alert when a team's loss streak crosses a
threshold). Not currently called by server.py -- the dashboard itself now
covers loss/draw/points-lost filtering via DashboardService + StreakScanner.
Wire find_loss_streaks() into a route or a scheduled job if/when you want
push notifications on top of the dashboard.
"""
from models import LossStreakAlert
from team_results import TeamResultsBuilder
from streak_engine import StreakEngine


class LeagueScanner:

    @staticmethod
    def find_loss_streaks(matches, threshold=5):

        if not matches:
            return []

        teams = set()
        for match in matches:
            teams.add(match.home_team)
            teams.add(match.away_team)

        alerts = []
        league = matches[0].league

        for team in teams:

            latest_match = TeamResultsBuilder.latest_match(matches, team)

            if latest_match.home_team == team:
                opponent = latest_match.away_team
            else:
                opponent = latest_match.home_team

            results = TeamResultsBuilder.build_results(matches, team)

            loss_streak = StreakEngine.current_loss_streak(results)

            if loss_streak >= threshold:
                alerts.append(
                    LossStreakAlert(
                        league=league,
                        team=team,
                        loss_streak=loss_streak,
                        last_result=results[0],
                        last_opponent=opponent,
                        match_date=latest_match.date,
                        alert_triggered=True,
                    )
                )

        return alerts
