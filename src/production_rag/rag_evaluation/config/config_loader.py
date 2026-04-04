"""Load rag_evaluation config from config.yaml + env vars."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def _load_yaml() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


_yaml = _load_yaml()

# Static settings from YAML
judge_model = _yaml["judge_model"]
mlflow_experiment_name = _yaml["mlflow"]["experiment_name"]

# Secrets / env-specific from .env
mlflow_tracking_uri = os.environ["MLFLOW_TRACKING_URI"]
