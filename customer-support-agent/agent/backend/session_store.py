"""Session-scoped memory for IO reports and Pins KB rows."""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

_lock = threading.Lock()
_sessions: Dict[str, Dict[str, Any]] = {}
_current_session_id: Optional[str] = None


def set_current_session_id(sid: str) -> None:
    global _current_session_id
    _current_session_id = sid


def get_current_session_id() -> Optional[str]:
    return _current_session_id


def save_session(
    session_id: str,
    enhancement_option: str,
    mappings: List[Dict[str, Any]],
    unwritten_variables: List[Dict[str, Any]] | None = None,
) -> None:
    with _lock:
        _sessions[session_id] = {
            "enhancement_option": enhancement_option,
            "mappings": mappings,
            "unwritten_variables": unwritten_variables or [],
        }


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    return _sessions.get(session_id)


def get_mappings() -> List[Dict[str, Any]]:
    sid = _current_session_id
    if not sid or sid not in _sessions:
        return []
    return _sessions[sid].get("mappings", [])


def get_enhancement_option() -> str:
    sid = _current_session_id
    if not sid or sid not in _sessions:
        return ""
    return _sessions[sid].get("enhancement_option", "")


def get_unwritten_variables() -> List[Dict[str, Any]]:
    sid = _current_session_id
    if not sid or sid not in _sessions:
        return []
    return _sessions[sid].get("unwritten_variables", [])


# ---- Last FBD context (for follow-up questions) ----
_last_fbd: Dict[str, Dict[str, Any]] = {}


def store_last_fbd(session_id: str, fbd: Dict[str, Any]) -> None:
    with _lock:
        _last_fbd[session_id] = fbd


def get_last_fbd(session_id: str) -> Optional[Dict[str, Any]]:
    return _last_fbd.get(session_id)

