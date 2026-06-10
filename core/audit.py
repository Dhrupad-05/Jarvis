from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger

audit_log = get_logger("assistant.audit")


def log_action(action: str, outcome: str, **fields: Any) -> None:
    """Write compact structured action logs."""

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "outcome": outcome,
        **fields,
    }
    audit_log.info(json.dumps(payload, ensure_ascii=True, default=str))
