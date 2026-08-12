"""
src/utils/config.py
-------------------
Loads the YAML config and exposes it as a simple namespace.
"""

import yaml
from pathlib import Path
from types import SimpleNamespace


def load_config(path: str = "configs/config.yaml") -> SimpleNamespace:
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return _to_namespace(data)


def _to_namespace(d):
    if isinstance(d, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in d.items()})
    return d

