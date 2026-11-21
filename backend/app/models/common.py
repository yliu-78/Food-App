"""Small shapes reused across the API."""

from typing import Literal

from pydantic import BaseModel, Field

# Which kind of thing an event or saved item refers to. Only "recipe" in the MVP;
# add "restaurant" here when §7 is picked up, and events/feedback work unchanged.
ItemType = Literal["recipe"]


class SourceLink(BaseModel):
    """A web page that inspired a recipe, taken from Gemini's grounding metadata.
    Shown under "Inspired by" on the recipe card."""

    title: str
    url: str
    domain: str | None = None  # "example.com", shown next to the title


class Page[T](BaseModel):
    """A page of results from a list endpoint.

    Firestore paginates with cursors (start after this document), not page numbers,
    so the client passes `next_cursor` back as `?cursor=` to get the next page."""

    items: list[T]
    next_cursor: str | None = None
    total: int | None = None  # only filled where it's cheap to count


class ErrorResponse(BaseModel):
    """Body of every non-2xx response, so the frontend handles errors one way.

    `code` is stable and machine-readable ("rate_limited", "allergen_check_failed",
    "not_found"); `message` is human-readable and may change."""

    code: str
    message: str
    retry_after_seconds: int | None = Field(
        default=None, description="Set on 429 rate-limit responses."
    )
