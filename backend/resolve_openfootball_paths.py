"""
OpenFootballProvider pulls from https://github.com/openfootball/football.json
(mirrored as static JSON, no key needed). This script fetches each
configured league's file directly and prints how many matches it has and
the date of the most recent finished one, so you can see at a glance which
leagues this fallback is actually current for right now versus genuinely
stale -- the gap can be months for some of the second-tier leagues (see the
docstring in providers/openfootball.py).

Run: python resolve_openfootball_paths.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

from providers.openfootball import RAW_BASE_URL, OpenFootballProvider
from season_util import current_season_label, previous_season_label

print(f"{'code':<5}{'file':<13}{'season':<9}{'matches':<9}{'latest finished'}")
print("-" * 60)

for code, filename in OpenFootballProvider.FILE_BY_CODE.items():
    found = None
    for label in (current_season_label(), previous_season_label()):
        url = f"{RAW_BASE_URL}/{label}/{filename}"
        try:
            resp = requests.get(url, timeout=10)
        except requests.RequestException as exc:
            print(f"{code:<5}{filename:<13} network error on {label}: {exc}")
            continue
        if resp.status_code == 200:
            found = (label, resp.json())
            break

    if not found:
        print(f"{code:<5}{filename:<13} -> no file found for current or previous season")
        continue

    label, payload = found
    matches = payload.get("matches", [])
    played_dates = sorted(m["date"] for m in matches if m.get("score") is not None)
    latest = played_dates[-1] if played_dates else "no finished matches yet"
    print(f"{code:<5}{filename:<13}{label:<9}{len(matches):<9}{latest}")
