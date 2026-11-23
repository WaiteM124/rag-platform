from __future__ import annotations

import re

# PostgreSQL TEXT must not contain NUL; strip other C0 controls except tab and newline.
_INVALID_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalise_text(text: str) -> str:
    """Strip NUL and disallowed control characters; preserve \\n and \\t."""
    if not _INVALID_CTRL.search(text):
        return text
    return _INVALID_CTRL.sub("", text)
