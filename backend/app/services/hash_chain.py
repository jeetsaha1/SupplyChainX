import hashlib
import json


def hash_event(event_payload: dict[str, object], previous_hash: str | None = None) -> str:
    """Hash a canonical event payload and optional previous hash with SHA-256."""
    canonical_payload = {
        "event": event_payload,
        "previous_hash": previous_hash,
    }
    serialized = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()