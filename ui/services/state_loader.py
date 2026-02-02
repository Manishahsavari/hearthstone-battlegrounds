from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


class StateValidationError(ValueError):
    pass


def load_json_file(path: str | Path) -> Dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_payload(payload)
    return payload


def validate_payload(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise StateValidationError("Payload must be a JSON object.")
    if "type" not in payload:
        raise StateValidationError("Payload missing required field: type")
    if "payload" in payload and not isinstance(payload["payload"], dict):
        raise StateValidationError("Payload 'payload' must be a JSON object.")

    payload_type = payload.get("type")
    if payload_type == "state_delta":
        _validate_state_delta(payload)
    if payload_type == "combat_event":
        _validate_combat_event(payload)


def _validate_state_delta(payload: Dict[str, Any]) -> None:
    delta_payload = payload.get("payload", {})
    for list_key in ("board", "hand", "shop"):
        if list_key in delta_payload:
            _validate_cards(delta_payload[list_key], list_key)


def _validate_combat_event(payload: Dict[str, Any]) -> None:
    event_payload = payload.get("payload", {})
    if "kind" not in event_payload:
        raise StateValidationError("Combat event payload missing 'kind'.")
    if "source" in event_payload:
        _validate_card_ref(event_payload["source"], "source")


def _validate_cards(cards: Iterable[Dict[str, Any]], context: str) -> None:
    if not isinstance(cards, list):
        raise StateValidationError(f"{context} must be a list.")
    for card in cards:
        _validate_card_ref(card, context)


def _validate_card_ref(card: Dict[str, Any], context: str) -> None:
    if not isinstance(card, dict):
        raise StateValidationError(f"{context} entries must be objects.")
    missing_fields = [field for field in ("slot", "type") if field not in card]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise StateValidationError(f"{context} missing required field(s): {missing}")
