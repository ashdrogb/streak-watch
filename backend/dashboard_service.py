"""
The original upload had three near-identical "loop every league and scan
it" implementations (DashboardService, GlobalStreakScanner, and the
loss-streak-only GlobalScanner). This is the one canonical version they all
collapse into -- everything else either called this same logic or has been
moved to alerts/ since it serves a different purpose (threshold alerts, not
the dashboard).
"""
import concurrent.futures

from config import LEAGUES, LEAGUE_PROVIDER_CHAIN, CACHE_TTL_SECONDS
from cache import cache_get, cache_set
from providers.base import FootballDataAPIError
from providers.registry import get_provider
from streak_scanner import StreakScanner

_CACHE_KEY = "all_streaks"


def fetch_league_matches(league_code: str):
    """
    Try each provider configured for *league_code*, in order, returning
    the matches from the first one that succeeds (and which provider that
    was, for logging) or raising the last error if all of them fail.

    Public (not prefixed with _) because alerts/global_scanner.py reuses it
    too -- both want "give me this league's matches via whichever provider
    actually works", just feeding the result to different scanners.
    """
    chain = LEAGUE_PROVIDER_CHAIN.get(league_code, ["football_data_org"])
    last_error = None

    for provider_name in chain:
        provider = get_provider(provider_name)
        try:
            return provider.get_completed_matches(league_code), provider_name
        except FootballDataAPIError as exc:
            last_error = exc
            continue

    raise last_error or FootballDataAPIError(f"{league_code}: no provider configured")


class DashboardService:
    """
    Fetches completed matches for every configured league and turns them
    into the list of active streaks shown on the dashboard.

    Results are cached for CACHE_TTL_SECONDS so that repeated page loads
    (and the league/type filters, which are applied to the cached list)
    don't re-hit the provider APIs -- important given football-data.org's
    10 req/min free-tier limit and API-Football's 100 req/day limit.
    """

    @staticmethod
    def get_all_streaks(force_refresh: bool = False) -> list:
        if not force_refresh:
            cached = cache_get(_CACHE_KEY)
            if cached is not None:
                return cached

        all_streaks = []

        # One league is one (or two, on fallback) outbound HTTP calls;
        # running them concurrently keeps a 10-league scan well inside a
        # Vercel Function's timeout instead of paying for each call serially.
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            future_to_league = {
                pool.submit(fetch_league_matches, code): (name, code)
                for name, code in LEAGUES.items()
            }
            for future in concurrent.futures.as_completed(future_to_league):
                league_name, league_code = future_to_league[future]
                try:
                    matches, provider_name = future.result()
                    print(f"{league_name} ({league_code}): {len(matches)} matches via {provider_name}")
                    all_streaks.extend(StreakScanner.scan(matches))
                except FootballDataAPIError as exc:
                    print(f"Skipped {league_name} ({league_code}): {exc}")
                except Exception as exc:
                    print(f"Failed {league_name} ({league_code}): {exc}")

        all_streaks.sort(key=lambda s: s.streak_length, reverse=True)
        cache_set(_CACHE_KEY, all_streaks, CACHE_TTL_SECONDS)
        return all_streaks


def run_diagnostics() -> list:
    """
    For every league, tries EVERY provider in its chain (not just the
    first one that works) and reports each attempt's outcome. This is
    what GET /api/diagnostics exposes -- meant for you to read in a
    browser while debugging, not something the frontend calls. It costs a
    real API call per provider per league (up to 3x what a normal scan
    costs), so don't poll it or wire it into the dashboard's own requests.
    """
    report = []

    for name, code in LEAGUES.items():
        chain = LEAGUE_PROVIDER_CHAIN.get(code, ["football_data_org"])
        attempts = []

        for provider_name in chain:
            provider = get_provider(provider_name)
            try:
                matches = provider.get_completed_matches(code)
                attempts.append({
                    "provider": provider_name,
                    "ok": True,
                    "matches_found": len(matches),
                })
            except FootballDataAPIError as exc:
                attempts.append({"provider": provider_name, "ok": False, "error": str(exc)})
            except Exception as exc:
                attempts.append({"provider": provider_name, "ok": False, "error": f"unexpected: {exc}"})

        report.append({"league": name, "code": code, "attempts": attempts})

    return report
