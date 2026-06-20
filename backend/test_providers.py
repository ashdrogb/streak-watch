import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import patch, MagicMock

from providers.football_data_org import FootballDataOrgProvider
from providers.openligadb import OpenLigaDBProvider
from providers.api_football import ApiFootballProvider
from providers.base import FootballDataAPIError


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.json.return_value = json_data
    resp.headers = {}
    return resp


# --- football-data.org -------------------------------------------------
FD_ORG_PAYLOAD = {
    "matches": [
        {
            "utcDate": "2026-05-10T15:00:00Z",
            "homeTeam": {"id": 1, "name": "Real Madrid", "crest": "rm.png"},
            "awayTeam": {"id": 2, "name": "Barcelona", "crest": "fcb.png"},
            "score": {"fullTime": {"home": 2, "away": 1}},
        },
        {
            # malformed / no final score yet -- should be skipped
            "utcDate": "2026-05-17T20:00:00Z",
            "homeTeam": {"id": 3, "name": "Sevilla", "crest": "sev.png"},
            "awayTeam": {"id": 4, "name": "Valencia", "crest": "val.png"},
            "score": {"fullTime": {"home": None, "away": None}},
        },
    ]
}

with patch("providers.football_data_org.requests.get", return_value=_mock_response(FD_ORG_PAYLOAD)):
    provider = FootballDataOrgProvider(api_key="dummy-key")
    matches = provider.get_completed_matches("PD")
    assert len(matches) == 1, matches
    assert matches[0].home_team == "Real Madrid"
    assert matches[0].away_score == 1
    assert matches[0].league == "PD"
    print("FootballDataOrgProvider OK:", matches[0])

# No key configured -> should raise immediately, no network call attempted.
no_key_provider = FootballDataOrgProvider(api_key="")
try:
    no_key_provider.get_completed_matches("PD")
    raise AssertionError("expected FootballDataAPIError")
except FootballDataAPIError:
    print("FootballDataOrgProvider correctly refuses to run without a key")


# --- OpenLigaDB ----------------------------------------------------------
OPENLIGADB_PAYLOAD = [
    {
        "matchIsFinished": True,
        "matchDateTimeUTC": "2026-04-12T13:30:00Z",
        "team1": {"teamId": 10, "teamName": "FC Koln", "teamIconUrl": "fck.svg"},
        "team2": {"teamId": 11, "teamName": "Schalke 04", "teamIconUrl": "s04.svg"},
        "matchResults": [
            {"resultTypeID": 1, "pointsTeam1": 1, "pointsTeam2": 0},  # half-time
            {"resultTypeID": 2, "pointsTeam1": 2, "pointsTeam2": 2},  # final
        ],
    },
    {
        "matchIsFinished": False,   # not played yet -- should be skipped
        "team1": {"teamId": 12, "teamName": "Hertha"},
        "team2": {"teamId": 13, "teamName": "HSV"},
        "matchResults": [],
    },
]

with patch("providers.openligadb.requests.get", return_value=_mock_response(OPENLIGADB_PAYLOAD)):
    provider = OpenLigaDBProvider()
    matches = provider.get_completed_matches("BL2")
    assert len(matches) == 1, matches
    assert matches[0].home_team == "FC Koln"
    assert matches[0].home_score == 2 and matches[0].away_score == 2
    print("OpenLigaDBProvider OK:", matches[0])

# Unsupported league -> immediate error, no network call.
try:
    provider.get_completed_matches("PL")
    raise AssertionError("expected FootballDataAPIError")
except FootballDataAPIError:
    print("OpenLigaDBProvider correctly rejects an unsupported league code")


# --- API-Football ----------------------------------------------------------
LEAGUES_PAYLOAD = {"response": [{"league": {"id": 999, "name": "League One"}}]}
FIXTURES_PAYLOAD = {
    "response": [
        {
            "fixture": {"date": "2026-03-01T15:00:00+00:00"},
            "teams": {
                "home": {"id": 20, "name": "Wigan", "logo": "wigan.png"},
                "away": {"id": 21, "name": "Bolton", "logo": "bolton.png"},
            },
            "goals": {"home": 1, "away": 1},
        }
    ]
}

def fake_get(url, headers=None, params=None, timeout=None):
    if url.endswith("/leagues"):
        return _mock_response(LEAGUES_PAYLOAD)
    return _mock_response(FIXTURES_PAYLOAD)

with patch("providers.api_football.requests.get", side_effect=fake_get):
    provider = ApiFootballProvider(api_key="dummy-key")
    matches = provider.get_completed_matches("EL1")
    assert len(matches) == 1, matches
    assert matches[0].home_team == "Wigan"
    assert provider._league_id_cache["EL1"] == 999
    print("ApiFootballProvider OK (direct api-sports.io gateway):", matches[0])

# --- API-Football via RapidAPI ---------------------------------------------
# A RapidAPI-issued key must hit the RapidAPI host with x-rapidapi-key /
# x-rapidapi-host, NOT the direct gateway with x-apisports-key -- that
# mismatch (RapidAPI key sent as x-apisports-key to v3.football.api-sports.io)
# is exactly the silent-failure bug this test guards against.
calls = []

def recording_get(url, headers=None, params=None, timeout=None):
    calls.append({"url": url, "headers": headers})
    if url.endswith("/leagues"):
        return _mock_response(LEAGUES_PAYLOAD)
    return _mock_response(FIXTURES_PAYLOAD)

with patch("providers.api_football.requests.get", side_effect=recording_get):
    provider = ApiFootballProvider(rapidapi_key="dummy-rapidapi-key")
    matches = provider.get_completed_matches("EL1")
    assert len(matches) == 1, matches

    for call in calls:
        assert call["url"].startswith("https://api-football-v1.p.rapidapi.com/v3"), call
        assert call["headers"]["x-rapidapi-key"] == "dummy-rapidapi-key", call
        assert call["headers"]["x-rapidapi-host"] == "api-football-v1.p.rapidapi.com", call
        assert "x-apisports-key" not in call["headers"], call
    print("ApiFootballProvider OK (RapidAPI gateway, correct host + headers)")

# If both are configured, RapidAPI wins.
calls.clear()
with patch("providers.api_football.requests.get", side_effect=recording_get):
    provider = ApiFootballProvider(api_key="dummy-direct-key", rapidapi_key="dummy-rapidapi-key")
    provider.get_completed_matches("EL1")
    assert all("rapidapi" in c["url"] for c in calls)
    print("ApiFootballProvider OK: RapidAPI key takes priority when both are set")

# A key sent to the wrong gateway should surface a clear, specific error
# rather than a generic HTTP failure.
with patch("providers.api_football.requests.get", return_value=_mock_response({}, status_code=403)):
    provider = ApiFootballProvider(rapidapi_key="wrong-gateway-key")
    try:
        provider.get_completed_matches("EL1")
        raise AssertionError("expected FootballDataAPIError")
    except FootballDataAPIError as exc:
        assert "RapidAPI" in str(exc), exc
        print("ApiFootballProvider OK: 403 reports which gateway the key didn't match ->", exc)

# --- openfootball ------------------------------------------------------
from providers.openfootball import OpenFootballProvider
from season_util import current_season_label

OPENFOOTBALL_PAYLOAD = {
    "name": "Test League 2025/26",
    "matches": [
        {"date": "2025-08-09", "team1": "Rodez AF", "team2": "AS Nancy", "score": [0, 0]},
        {"date": "2025-08-16", "team1": "Rodez AF", "team2": "Le Havre",
         "score": {"ft": [2, 1], "ht": [1, 0]}},
        {"date": "2026-03-01", "team1": "Rodez AF", "team2": "Troyes"},  # not played yet
    ],
}

with patch("providers.openfootball.requests.get", return_value=_mock_response(OPENFOOTBALL_PAYLOAD)):
    provider = OpenFootballProvider()
    matches = provider.get_completed_matches("FL2")
    assert len(matches) == 2, matches  # the unplayed fixture is skipped
    assert matches[0].away_score == 0 and matches[1].away_score == 1
    assert matches[0].home_team_id == matches[1].home_team_id  # same team -> same synthetic id
    assert matches[0].home_crest == "" and matches[0].away_crest == ""
    print("OpenFootballProvider OK: parses flat-list and ft/ht score shapes, skips unplayed fixtures")

# Current season's file 404s -> falls back to last season's file.
def season_fallback_get(url, timeout=None):
    if current_season_label() in url:
        return _mock_response({}, status_code=404)
    return _mock_response(OPENFOOTBALL_PAYLOAD)

with patch("providers.openfootball.requests.get", side_effect=season_fallback_get):
    provider = OpenFootballProvider()
    matches = provider.get_completed_matches("FL2")
    assert len(matches) == 2, matches
    print("OpenFootballProvider OK: falls back to the previous season's file on a 404")

print("\nAll provider tests passed.")
