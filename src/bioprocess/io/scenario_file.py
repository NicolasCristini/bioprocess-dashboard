"""Scenario <-> YAML/JSON text (schema-versioned)."""
from __future__ import annotations

import json

import yaml

from ..models import SCHEMA_VERSION, Scenario


def to_dict(sc: Scenario) -> dict:
    return sc.model_dump(mode="json")


def to_yaml(sc: Scenario) -> str:
    header = f"# Bioprocess Phase Planner scenario (schema {SCHEMA_VERSION})\n"
    return header + yaml.safe_dump(to_dict(sc), sort_keys=False, allow_unicode=True)


def to_json(sc: Scenario) -> str:
    return json.dumps(to_dict(sc), indent=2, ensure_ascii=False)


def from_text(text: str) -> Scenario:
    """Parse YAML or JSON (JSON is valid YAML). Raises ValueError with a readable message."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValueError(f"Not a valid YAML/JSON file: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("The file does not contain a scenario.")
    version = data.get("schema_version", SCHEMA_VERSION)
    if version > SCHEMA_VERSION:
        raise ValueError(f"Scenario schema {version} is newer than this app ({SCHEMA_VERSION}).")
    # pydantic: regime day keys come back as str from JSON; Scenario coerces them to int
    try:
        return Scenario.model_validate(data)
    except Exception as e:  # pydantic.ValidationError -> readable
        raise ValueError(f"The scenario has invalid values:\n{e}") from e
