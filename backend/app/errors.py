"""Error responses for the OpenAPI docs (see "Errors" in docs/api-contract.md).

`errors(401, 404)` builds a route's `responses=` dict, so /docs and the generated
TypeScript types know those status codes return an ErrorResponse body.

TODO Step 2: by default FastAPI's HTTPException returns `{"detail": ...}`, not
ErrorResponse. Add exception handlers in main.py so real errors match this shape.
"""

from typing import Any

from fastapi import HTTPException

from app.models import ErrorResponse

_DESCRIPTIONS = {
    401: "`unauthenticated`: missing or invalid Firebase ID token",
    404: "`not_found`: unknown id, or an id belonging to another user",
    429: "`rate_limited`: daily generation limit reached; `retry_after_seconds` is set",
    502: "`generation_failed`: Gemini error or timeout",
}


def errors(*codes: int) -> dict[int | str, dict[str, Any]]:
    return {code: {"model": ErrorResponse, "description": _DESCRIPTIONS[code]} for code in codes}


NOT_IMPLEMENTED = "Not implemented"


def not_implemented() -> None:
    """Stub dependency for streaming routes. A dependency runs before the stream
    opens, so this still returns a real 501. Raising inside the generator would be
    too late, because the 200 status line has already been sent by then."""
    raise HTTPException(501, NOT_IMPLEMENTED)
