"""Common National Material Code (PRD 9.8, FR-902, TRD TR-MOD-08).

`NMC-` + 10-digit sequence + 1 Luhn check digit; non-significant on purpose.
"""

import re

_CNMC = re.compile(r"NMC-([0-9]{10})([0-9])")
MAX_SEQ = 10**10 - 1


def luhn_digit(body: str) -> int:
    total = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch) * (2 if i % 2 == 0 else 1)
        total += d - 9 if d > 9 else d
    return (10 - total % 10) % 10


def new_cnmc(seq: int) -> str:
    if not 0 <= seq <= MAX_SEQ:
        raise ValueError(f"CNMC sequence out of range: {seq}")
    body = f"{seq:010d}"
    return f"NMC-{body}{luhn_digit(body)}"


def cnmc_valid(code: str) -> bool:
    m = _CNMC.fullmatch(code)
    if m is None:
        return False
    return luhn_digit(m.group(1)) == int(m.group(2))
