from models import Match


class TeamResultsBuilder:
    """
    Derives a team's match log, result sequence, and latest match from
    a flat list of Match objects covering an entire league.
    """

    @staticmethod
    def _team_matches_sorted(matches: list[Match], team: str) -> list[Match]:
        """All of *team*'s matches, newest first."""
        team_matches = [
            m for m in matches
            if m.home_team == team or m.away_team == team
        ]
        # Sort descending by date string (ISO-8601 sorts lexicographically)
        team_matches.sort(key=lambda m: m.date, reverse=True)
        return team_matches

    @staticmethod
    def build_match_log(matches: list[Match], team: str) -> list[tuple[str, int, int]]:
        """
        Return (result, goals_for, goals_against) for *team*, newest-first.
        result is "W" / "D" / "L". This is the single source of truth that
        build_results() below derives from, so goals and results can never
        drift out of sync with each other.
        """
        log = []
        for match in TeamResultsBuilder._team_matches_sorted(matches, team):
            if match.home_team == team:
                goals_for, goals_against = match.home_score, match.away_score
            else:
                goals_for, goals_against = match.away_score, match.home_score

            if goals_for > goals_against:
                result = "W"
            elif goals_for < goals_against:
                result = "L"
            else:
                result = "D"

            log.append((result, goals_for, goals_against))
        return log

    @staticmethod
    def build_results(matches: list[Match], team: str) -> list[str]:
        """
        Return a list of "W" / "D" / "L" strings for *team*,
        sorted newest-first (index 0 = most recent match).
        """
        return [result for result, _, _ in TeamResultsBuilder.build_match_log(matches, team)]

    @staticmethod
    def latest_match(matches: list[Match], team: str) -> Match:
        """
        Return the single most-recent Match involving *team*.
        Raises ValueError when the team has no matches.
        """
        team_matches = TeamResultsBuilder._team_matches_sorted(matches, team)

        if not team_matches:
            raise ValueError(f"No matches found for team: {team}")

        return team_matches[0]
