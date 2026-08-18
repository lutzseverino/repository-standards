"""Small Draft 2020-12 subset used to test the dependency-free manifest schema."""

from __future__ import annotations

import json
import re
from typing import Any


def validation_errors(instance: Any, schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _validate(instance, schema, "$", errors)
    return errors


def _matches_type(instance: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    raise AssertionError(f"unsupported schema type: {expected}")


def _validate(
    instance: Any, schema: dict[str, Any], path: str, errors: list[str]
) -> None:
    expected_types = schema.get("type")
    if expected_types is not None:
        if isinstance(expected_types, str):
            expected_types = [expected_types]
        if not any(_matches_type(instance, expected) for expected in expected_types):
            errors.append(f"{path}: expected {' or '.join(expected_types)}")
            return

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value is not in the declared enum")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path}: string is too short")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: string does not match {schema['pattern']}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: value is below the minimum")

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: array has too few items")
        if schema.get("uniqueItems"):
            keys = [json.dumps(item, sort_keys=True) for item in instance]
            if len(keys) != len(set(keys)):
                errors.append(f"{path}: array items are not unique")
        if "items" in schema:
            for index, item in enumerate(instance):
                _validate(item, schema["items"], f"{path}[{index}]", errors)

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for name in required:
            if name not in instance:
                errors.append(f"{path}: missing required field {name}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for name in instance:
                if name not in properties:
                    errors.append(f"{path}: unknown field {name}")
        additional = schema.get("additionalProperties")
        for name, value in instance.items():
            if name in properties:
                _validate(value, properties[name], f"{path}.{name}", errors)
            elif isinstance(additional, dict):
                _validate(value, additional, f"{path}.{name}", errors)
        if "propertyNames" in schema:
            for name in instance:
                _validate(name, schema["propertyNames"], f"{path}.{name}", errors)

    for child in schema.get("allOf", []):
        _validate(instance, child, path, errors)

    if "contains" in schema and isinstance(instance, list):
        matching = sum(
            not validation_errors(item, schema["contains"]) for item in instance
        )
        if matching < schema.get("minContains", 1):
            errors.append(f"{path}: array does not contain enough required items")
        if "maxContains" in schema and matching > schema["maxContains"]:
            errors.append(f"{path}: array contains too many matching items")

    if "oneOf" in schema:
        matching = sum(
            not validation_errors(instance, alternative)
            for alternative in schema["oneOf"]
        )
        if matching != 1:
            errors.append(f"{path}: expected exactly one matching alternative")
