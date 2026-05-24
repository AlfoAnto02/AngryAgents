from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

STRICT = os.getenv("STRICT_MODE", "0") == "1"


class UnexpectedDeviation(RuntimeError):
    pass


def deviation(msg: str, **kwargs) -> None:
    if STRICT:
        raise UnexpectedDeviation(f"{msg} | {kwargs}")
    log.warning(msg, extra=kwargs)
