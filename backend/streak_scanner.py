from models import Match, TeamStreak
from team_results import TeamResultsBuilder
from streak_engine import StreakEngine


class StreakScanner:
    """
    Scans a list of matches from one league and returns a
    TeamStreak for every team that has an active streak of
    any type (win / draw / loss), enriched with the goals scored/conceded
    during that streak and an independent points-lost reading.
    """

    @staticmethod
    def scan(matches: list[Match]) -> list[TeamStreak]:

        if not matches:
            return []

        teams = {m.home_team for m in matches} | {m.away_team for m in matches}

        streaks = []

        for team in teams:

            match_log = TeamResultsBuilder.build_match_log(matches, team)

            if not match_log:
                continue

            results = [result for result, _, _ in match_log]

            streak_type, streak_length = StreakEngine.current_streak_type(results)

            points_lost_streak = StreakEngine.points_lost_streak_length(results)
            points_dropped = StreakEngine.points_dropped_in_streak(results)

            if streak_length == 0 and points_lost_streak == 0:
                continue

            # Goals scored/conceded across the streak_length matches that
            # make up the active streak (0 of them if streak_length is 0,
            # which can happen for a team with no current single-type
            # streak that still has a non-zero points-lost run -- e.g. "DL").
            window = match_log[:streak_length] if streak_length else []
            goals_for = sum(gf for _, gf, _ in window)
            goals_against = sum(ga for _, _, ga in window)

            latest = TeamResultsBuilder.latest_match(matches, team)

            if latest.home_team == team:
                team_id        = latest.home_team_id
                crest_url      = latest.home_crest
                last_opponent  = latest.away_team
                opponent_crest = latest.away_crest
            else:
                team_id        = latest.away_team_id
                crest_url      = latest.away_crest
                last_opponent  = latest.home_team
                opponent_crest = latest.home_crest

            streaks.append(
                TeamStreak(
                    league=latest.league,
                    team=team,
                    team_id=team_id,
                    crest_url=crest_url,
                    streak_type=streak_type,
                    streak_length=streak_length,
                    goals_for=goals_for,
                    goals_against=goals_against,
                    goal_difference=goals_for - goals_against,
                    points_lost_streak=points_lost_streak,
                    points_dropped=points_dropped,
                    last_opponent=last_opponent,
                    last_opponent_crest=opponent_crest,
                    match_date=latest.date,
                )
            )

        # Longest streaks first
        streaks.sort(key=lambda s: s.streak_length, reverse=True)

        return streaks
