"""Load ingestion pipeline config from config.yaml."""

from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def _load_yaml() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


_yaml = _load_yaml()

# Static settings from YAML
embedder = _yaml["embedder"]
vision_model = _yaml["vision"]["model"]
max_workers = _yaml["pipeline"]["max_workers"]
