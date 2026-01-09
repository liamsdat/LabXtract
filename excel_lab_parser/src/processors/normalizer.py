import re 
from typing import Optional


_NUMERIC_RE = re.compile(
    r"""
    (?P<number>
        \d+(?:[.,]\d+)?
    )
    """,
    re.VERBOSE,
)

_NON_NUMERIC_MARKERS = (
    "не обнаруж",
    "отриц",
    "единич",
    "+",
    "следы",
    "отсутств",

)

def normalize_value(raw_value: str) -> Optional[float]:
    if not raw_value:
        return None
    
    text = raw_value.strip().lower()

    if any(marker in text for marker in _NON_NUMERIC_MARKERS):
        return None
    
    match = _NUMERIC_RE.search(text)
    if not match:
        return None
    
    number = match.group("number").replace(",",".")

    try:
        return float(number)
    except ValueError:
        return None