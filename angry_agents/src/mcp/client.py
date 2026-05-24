from __future__ import annotations

import os
from typing import Any

import httpx

BASE_URL = os.environ.get("ANGRY_API_BASE_URL", "http://localhost:8000")
TIMEOUT = 30.0


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as c:
        r = await c.get(path, params={k: v for k, v in (params or {}).items() if v is not None})
        r.raise_for_status()
        return r.json()


async def _post(path: str, json: dict[str, Any]) -> Any:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as c:
        r = await c.post(path, json=json)
        r.raise_for_status()
        return r.json()
