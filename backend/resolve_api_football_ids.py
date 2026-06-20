"""
ApiFootballProvider resolves league ids dynamically (by name + country, via
GET /leagues) rather than hard-coding them, since API-Football's numeric ids
aren't published anywhere stable enough to bake into source. This script is
just a manual sanity check you can run after getting your key, to see what
it actually resolves to and spot a mismatched league name early:

    cd backend
    python resolve_api_football_ids.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from providers.api_football import ApiFootballProvider
from providers.base import FootballDataAPIError

provider = ApiFootballProvider()

if not provider.api_key:
    raise SystemExit(
        "Set API_FOOTBALL_KEY first (in backend/.env, or export it directly)."
    )

print(f"{'Our code':<6} {'API-Football name':<22} {'Country':<10} -> league id")
print("-" * 60)

for code, (name, country) in ApiFootballProvider.LEAGUE_LOOKUP.items():
    try:
        league_id = provider._resolve_league_id(code)
        print(f"{code:<6} {name:<22} {country:<10} -> {league_id}")
    except FootballDataAPIError as exc:
        print(f"{code:<6} {name:<22} {country:<10} -> ERROR: {exc}")
