import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from season_util import current_season_start_year, current_season_label, previous_season_label

# Mid-season (today is "inside" the 2026/27 season window)
mid_season = date(2027, 2, 14)
assert current_season_start_year(mid_season) == 2026
assert current_season_label(mid_season) == "2026-27"
assert previous_season_label(mid_season) == "2025-26"

# Just after a season would have started (July boundary)
just_started = date(2026, 7, 1)
assert current_season_start_year(just_started) == 2026

# Just before that boundary -- still last season
just_before = date(2026, 6, 30)
assert current_season_start_year(just_before) == 2025
assert current_season_label(just_before) == "2025-26"

print("season_util OK: start-year/label helpers correct across season boundaries")
