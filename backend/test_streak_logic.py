"""
Pure-logic test: builds synthetic Match objects directly (no HTTP) and
checks StreakScanner output, including the new GF/GA/GD and points-lost
fields. Run with: python test_streak_logic.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Match
from streak_scanner import StreakScanner

matches = [
    # Wolves: L, L, L (most recent last in this list, but date governs order)
    Match("PL", "2026-01-01", "Wolves", 1, "", 0, "Arsenal", 2, "", 2),   # L 0-2
    Match("PL", "2026-01-08", "Spurs", 3, "", 3, "Wolves", 1, "", 1),     # L 1-3
    Match("PL", "2026-01-15", "Wolves", 1, "", 0, "Chelsea", 4, "", 1),   # L 0-1

    # City: D, L (mixed bad run -> points-lost streak of 2, no single-type streak >=2)
    Match("PL", "2026-01-01", "City", 5, "", 1, "Everton", 6, "", 1),     # D 1-1
    Match("PL", "2026-01-08", "Burnley", 7, "", 2, "City", 5, "", 0),     # L 0-2 for City

    # Arsenal: W, W (win streak with goals)
    Match("PL", "2026-01-08", "Arsenal", 2, "", 3, "Fulham", 8, "", 0),   # W 3-0
]

streaks = StreakScanner.scan(matches)
by_team = {s.team: s for s in streaks}

wolves = by_team["Wolves"]
assert wolves.streak_type == "loss"
assert wolves.streak_length == 3
assert wolves.goals_for == 0 + 1 + 0       # 1 (newest-first order: 01-15, 01-08, 01-01)
assert wolves.goals_against == 1 + 3 + 2
assert wolves.points_lost_streak == 3
assert wolves.points_dropped == 9
print("Wolves OK:", wolves)

city = by_team["City"]
assert city.points_lost_streak == 2          # D then L, in some date order
assert city.points_dropped == 2 + 3          # one draw (2) + one loss (3) = 5
print("City OK:", city)

arsenal = by_team["Arsenal"]
assert arsenal.streak_type == "win"
assert arsenal.streak_length == 2
assert arsenal.points_lost_streak == 0
assert arsenal.points_dropped == 0
print("Arsenal OK:", arsenal)

print("\nAll assertions passed.")
