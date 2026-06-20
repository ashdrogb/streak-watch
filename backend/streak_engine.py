class StreakEngine:
    """
    Computes streak statistics from a chronologically-ordered
    list of result strings (e.g. ["L", "L", "W", "D"]).

    Convention: index 0 is the most recent match.
    """

    @staticmethod
    def current_loss_streak(results: list[str]) -> int:
        """Count consecutive losses from the most recent match."""
        streak = 0
        for result in results:
            if result == "L":
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def current_win_streak(results: list[str]) -> int:
        """Count consecutive wins from the most recent match."""
        streak = 0
        for result in results:
            if result == "W":
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def current_draw_streak(results: list[str]) -> int:
        """Count consecutive draws from the most recent match."""
        streak = 0
        for result in results:
            if result == "D":
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def current_unbeaten_streak(results: list[str]) -> int:
        """Count consecutive non-loss matches (W or D)."""
        streak = 0
        for result in results:
            if result in ("W", "D"):
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def current_winless_streak(results: list[str]) -> int:
        """Count consecutive non-win matches (L or D)."""
        streak = 0
        for result in results:
            if result in ("L", "D"):
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def current_streak_type(results: list[str]) -> tuple[str, int]:
        """
        Returns the active streak type and its length.
        Returns ("none", 0) when the results list is empty.
        """
        if not results:
            return ("none", 0)

        latest = results[0]

        if latest == "W":
            return ("win", StreakEngine.current_win_streak(results))
        elif latest == "L":
            return ("loss", StreakEngine.current_loss_streak(results))
        else:
            return ("draw", StreakEngine.current_draw_streak(results))

    # -- Points-lost streak -------------------------------------------------
    # A separate lens from current_streak_type above: it doesn't require the
    # run to be a single result type. "WLDL" has no clean 1-game loss streak
    # by current_streak_type, but it IS a 3-match run of dropped points --
    # exactly the kind of bad patch current_streak_type alone would miss.

    POINTS_DROPPED_FOR_RESULT = {"W": 0, "D": 2, "L": 3}  # vs. 3 for a win

    @staticmethod
    def points_dropped_in_streak(results: list[str]) -> int:
        """
        Total points dropped (relative to winning every game) over the
        current winless run. Stops counting at the first win, mirroring
        current_winless_streak -- so points_lost_streak_length() and this
        always describe the same window of matches.
        """
        dropped = 0
        for result in results:
            if result == "W":
                break
            dropped += StreakEngine.POINTS_DROPPED_FOR_RESULT[result]
        return dropped

    @staticmethod
    def points_lost_streak_length(results: list[str]) -> int:
        """Alias of current_winless_streak, kept under this name so callers
        reading for the points-lost feature don't have to know the two are
        the same calculation."""
        return StreakEngine.current_winless_streak(results)
