"""Knowledge base: Block catalog (GEI-100682 library) from output/progress.json.

Pin tracing is handled by dynamodb_kb.py via DynamoDB GSI3 queries.
"""
from __future__ import annotations

import json
import os

KB_PATH = os.path.join(os.path.dirname(__file__), "../../../output/progress.json")

_EXCLUDE = {
    "null", "N/A", "IN", "GEI-100682",
    "_COMMENT_BF", "COMMENT", "COMMENT_BF", "COMMENT_NB",
}


def _load_block_catalog() -> tuple[dict, dict]:
    if not os.path.exists(KB_PATH):
        return {}, {}
    with open(KB_PATH) as f:
        raw: dict = json.load(f)["blocks"]
    verified = {
        k: {
            "category": v.get("category", ""),
            "description": v.get("description", "")[:120],
            "inputs": [
                {"name": p["name"], "type": p.get("data_type", "")}
                for p in v.get("inputs", [])
            ],
            "outputs": [
                {"name": p["name"], "type": p.get("data_type", "")}
                for p in v.get("outputs", [])
            ],
        }
        for k, v in raw.items()
        if v.get("inputs") and v.get("outputs") and k not in _EXCLUDE
    }
    return verified, raw


VERIFIED_KB, RAW_KB = _load_block_catalog()
