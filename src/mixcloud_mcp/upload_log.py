"""In-memory upload log — capped deque, no persistence required."""
from collections import deque
from datetime import datetime, UTC

# Holds the 20 most recent upload attempts; oldest entry drops automatically when full.
# Python's deque(maxlen=N) is the idiomatic bounded queue — no manual trimming needed.
_log: deque[dict] = deque(maxlen=20)


def record(entry: dict) -> None:
    _log.appendleft({**entry, "uploaded_at": datetime.now(UTC).isoformat()})


def recent(n: int = 5) -> list[dict]:
    return list(_log)[:n]
