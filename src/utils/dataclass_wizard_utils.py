import dataclass_wizard as dw
from typing import Any

import requests


def equal_if_truthy(a: Any, b: Any) -> bool:
    return not a or not b or a == b


def remap(*keys: str) -> dict[str, dw.models.JSON]:
    """returns remapping information for field metadata.
    `keys` are possible names you want mapped into the attribute.
    by default, camel cases are mapped into snake cases."""

    return {"__remapping__": dw.json_key(*keys, all=True)}


def get_data(session: requests.Session, url: str, timeout: int = 5) -> Any:
    """gets data from the chess.com public api using url"""

    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data
