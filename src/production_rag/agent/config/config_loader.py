"""Load agent config from config.yaml."""

from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def _load_yaml() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


_yaml = _load_yaml()

# Static settings from YAML
llm = _yaml["llm"]
embedder = _yaml["embedder"]
reranker = _yaml["reranker"]
