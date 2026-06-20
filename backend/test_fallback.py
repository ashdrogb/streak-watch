import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from unittest.mock import patch, MagicMock

from providers.base import FootballDataAPIError
from dashboard_service import fetch_league_matches


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.json.return_value = json_data
    resp.headers = {}
    return resp


# BL2's chain is ["openligadb", "football_data_org"]. Make openligadb fail
# (simulating e.g. a transient outage) and football_data_org succeed, and
# confirm fetch_league_matches falls through correctly.
fd_org_payload = {
    "matches": [
        {
            "utcDate": "2026-02-01T15:00:00Z",
            "homeTeam": {"id": 1, "name": "Holstein Kiel", "crest": ""},
            "awayTeam": {"id": 2, "name": "Hannover 96", "crest": ""},
            "score": {"fullTime": {"home": 1, "away": 0}},
        }
    ]
}

# NOTE: providers/openligadb.py and providers/football_data_org.py both do
# `import requests`, so they share the exact same module object -- patching
# "providers.openligadb.requests.get" and "providers.football_data_org.requests.get"
# as two separate patches targets the *same* underlying attribute, and the
# second one silently clobbers the first. One routing fake, keyed off the
# URL, avoids that collision (the same trick test_providers.py already uses
# for API-Football's two endpoints).
def route_openligadb_down_fd_org_up(url, headers=None, params=None, timeout=None):
    if "openligadb.de" in url:
        # requests wraps real socket/urllib3 failures in its own
        # ConnectionError (a RequestException subclass) before they ever
        # reach our code -- using the bare builtin one here would test a
        # case that can't actually happen against the real library.
        raise requests.exceptions.ConnectionError("boom")
    return _mock_response(fd_org_payload)

with patch("requests.get", side_effect=route_openligadb_down_fd_org_up):
    # Make sure football_data_org has a key configured for this test, since
    # the registry caches a singleton across test files run in-process.
    from providers.registry import get_provider
    get_provider("football_data_org").api_key = "dummy-key"

    matches, provider_name = fetch_league_matches("BL2")
    assert provider_name == "football_data_org"
    assert len(matches) == 1
    assert matches[0].home_team == "Holstein Kiel"
    print("Fallback chain OK: openligadb failed, football_data_org served BL2")

# All providers fail -> should raise, carrying the last error. BL2's chain
# is now 3 deep (openligadb, football_data_org, openfootball); route_both_down
# raises regardless of URL, so it covers all three without needing to know
# how many there are.
def route_both_down(url, headers=None, params=None, timeout=None):
    raise requests.exceptions.ConnectionError("boom too")

with patch("requests.get", side_effect=route_both_down):
    try:
        fetch_league_matches("BL2")
        raise AssertionError("expected FootballDataAPIError")
    except FootballDataAPIError as exc:
        print("Fallback chain OK: every provider failing raises ->", exc)

# Sanity check the alerts package imports and runs against an empty list.
from alerts.league_scanner import LeagueScanner
from alerts.global_scanner import GlobalScanner

assert LeagueScanner.find_loss_streaks([]) == []
print("alerts.league_scanner imports and handles an empty match list")
print("alerts.global_scanner imports OK:", GlobalScanner)

print("\nAll fallback/alerts tests passed.")
