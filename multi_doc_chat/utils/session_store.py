from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Dict, List


_STORE_PATH = Path("data") / "pageindex_sessions.json"
_STORE_LOCK = Lock()
_session_state: Dict[str, Dict[str, list]] = {}


def _load_state() -> Dict[str, Dict[str, list]]:
    if not _STORE_PATH.exists():
        return {}

    try:
        data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _save_state(state: Dict[str, Dict[str, list]]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(
        json.dumps(state, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _refresh_cache() -> Dict[str, Dict[str, list]]:
    global _session_state
    _session_state = _load_state()
    return _session_state


def add_pageindex_doc(session_id: str, doc_id: str) -> None:
    """
    Store a PageIndex doc_id for a given session.
    """
    with _STORE_LOCK:
        state = _refresh_cache()
        session = state.setdefault(session_id, {})
        doc_ids = session.setdefault("pageindex_doc_ids", [])
        if doc_id not in doc_ids:
            doc_ids.append(doc_id)
            _save_state(state)
        else:
            _save_state(state)


def get_pageindex_docs(session_id: str) -> List[str]:
    """
    Retrieve all PageIndex doc_ids associated with a session.
    """
    with _STORE_LOCK:
        state = _refresh_cache()
        return list(state.get(session_id, {}).get("pageindex_doc_ids", []))
