from datetime import date


def current_season_start_year(today: date = None) -> int:
    """
    European league seasons run roughly August -> May. Given today's date,
    return the year the *current* season started -- e.g. on any day
    between 2026-07-01 and 2027-06-30 this returns 2026.
    """
    today = today or date.today()
    return today.year if today.month >= 7 else today.year - 1


def season_label(start_year: int) -> str:
    """e.g. 2025 -> '2025-26'."""
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def current_season_label(today: date = None) -> str:
    return season_label(current_season_start_year(today))


def previous_season_label(today: date = None) -> str:
    return season_label(current_season_start_year(today) - 1)
