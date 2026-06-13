import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings

log = logging.getLogger("ingest")


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=30))
def get_json(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        r = client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


def save_raw(source: str, name: str, payload: Any, dt: date | None = None) -> Path:
    d = dt or date.today()
    out_dir = settings.raw_dir / source / d.isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    fp = out_dir / f"{name}.json"
    fp.write_text(json.dumps(payload, default=str))
    return fp


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")
