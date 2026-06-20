from providers.football_data_org import FootballDataOrgProvider
from providers.openligadb import OpenLigaDBProvider
from providers.api_football import ApiFootballProvider
from providers.openfootball import OpenFootballProvider

_PROVIDER_CLASSES = {
    "football_data_org": FootballDataOrgProvider,
    "openligadb": OpenLigaDBProvider,
    "api_football": ApiFootballProvider,
    "openfootball": OpenFootballProvider,
}

_instances: dict = {}


def get_provider(name: str):
    if name not in _instances:
        if name not in _PROVIDER_CLASSES:
            raise KeyError(f"Unknown provider '{name}'")
        _instances[name] = _PROVIDER_CLASSES[name]()
    return _instances[name]
