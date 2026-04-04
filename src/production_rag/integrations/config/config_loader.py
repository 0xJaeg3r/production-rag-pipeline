"""Load integrations config from config.yaml."""

from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def _load_yaml() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


_yaml = _load_yaml()

# Static settings from YAML
mlflow_experiment_name = _yaml["mlflow"]["experiment_name"]
gateway_endpoint = _yaml["mlflow"]["gateway_endpoint"]
