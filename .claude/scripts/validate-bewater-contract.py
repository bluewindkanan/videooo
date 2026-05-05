#!/usr/bin/env python3
"""Validate BeWater runtime artifacts against local JSON schemas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate payload JSON with a BeWater schema.")
    parser.add_argument("--schema", required=True, help="Path to schema JSON")
    parser.add_argument("--payload", required=True, help="Path to payload JSON")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{path}: file not found")
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}")


def _matches_type(type_name: str, value: Any) -> bool:
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, float)
    if type_name == "null":
        return value is None
    return False


def _validate_type(schema: dict[str, Any], value: Any, path: str, errors: list[str]) -> bool:
    expected = schema.get("type")
    if expected is None:
        return True
    expected_types = expected if isinstance(expected, list) else [expected]
    if any(_matches_type(type_name, value) for type_name in expected_types):
        return True
    joined = " | ".join(str(item) for item in expected_types)
    errors.append(f"{path}: expected type {joined}")
    return False


def _resolve_ref(schema: dict[str, Any], base_schema_path: Path) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not isinstance(ref, str) or "://" in ref:
        return schema
    ref_path = (base_schema_path.parent / ref).resolve()
    loaded = load_json(ref_path)
    if not isinstance(loaded, dict):
        raise ValueError(f"{ref_path}: referenced schema must be an object")
    merged = dict(loaded)
    for k, v in schema.items():
        if k != "$ref":
            merged[k] = v
    return merged


def validate_payload(schema: Any, payload: Any, schema_path: Path, path: str = "$") -> list[str]:
    errors: list[str] = []

    if not isinstance(schema, dict):
        errors.append(f"{path}: schema must be an object")
        return errors

    try:
        schema = _resolve_ref(schema, schema_path)
    except ValueError as exc:
        errors.append(str(exc))
        return errors

    type_valid = _validate_type(schema, payload, path, errors)

    enum_values = schema.get("enum")
    if enum_values is not None and payload not in enum_values:
        errors.append(f"{path}: value {payload!r} is not in enum {enum_values}")

    if not type_valid:
        return errors

    if isinstance(payload, dict):
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in payload:
                errors.append(f"{path}.{field}: missing required field")

        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)

        for key, value in payload.items():
            key_path = f"{path}.{key}"
            if key in properties:
                errors.extend(validate_payload(properties[key], value, schema_path, key_path))
                continue
            if additional is False:
                errors.append(f"{key_path}: additional property is not allowed")
                continue
            if isinstance(additional, dict):
                errors.extend(validate_payload(additional, value, schema_path, key_path))

    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        for sub in all_of:
            if_clause = sub.get("if")
            then_clause = sub.get("then")
            if isinstance(if_clause, dict) and isinstance(then_clause, dict):
                if_errors = validate_payload(if_clause, payload, schema_path, path)
                if not if_errors:
                    errors.extend(validate_payload(then_clause, payload, schema_path, path))

    if isinstance(payload, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(payload) < min_items:
            errors.append(f"{path}: expected at least {min_items} items")

        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(payload):
                errors.extend(validate_payload(item_schema, item, schema_path, f"{path}[{index}]"))

    if isinstance(payload, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(payload) < min_length:
            errors.append(f"{path}: expected at least {min_length} characters")

    not_schema = schema.get("not")
    if isinstance(not_schema, dict):
        not_errors = validate_payload(not_schema, payload, schema_path, path)
        if not not_errors:
            errors.append(f"{path}: must not match 'not' schema")

    const_value = schema.get("const")
    if const_value is not None and payload != const_value:
        errors.append(f"{path}: expected const {const_value!r}")

    return errors


def main() -> int:
    try:
        args = parse_args()
        schema_file = Path(args.schema)
        schema = load_json(schema_file)
        payload = load_json(Path(args.payload))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    errors = validate_payload(schema, payload, schema_file)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
