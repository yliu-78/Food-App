"""Event log (layer 2 in HANDOFF §5): everything the user did.

Stored in the top-level `events` collection, append-only. The one exception is the
user's own data-and-privacy actions ("Clear activity history", "Delete profile"),
which delete that user's events.

user_features/{uid} (layer 3) is always rebuildable from these events.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.models.common import ItemType

EventType = Literal[
    "impression",  # shown to the user: without these, "didn't like it" looks the same as "never saw it"
    "view",
    "save",
    "unsave",
    "cooked",
    "thumbs_up",
    "thumbs_down",
    "swap",
    "regenerate",  # a tweak message sent in reply to a recipe
    "dismiss",
]


class Event(BaseModel):
    event_id: str
    uid: str
    ts: datetime
    type: EventType
    item_type: ItemType
    item_id: str
    item_features: dict[str, Any]  # snapshot: cuisine_id, ingredient_ids, minutes, spice, difficulty
    context: dict[str, Any] = {}  # request text, time of day, (later) location bucket
    request_id: str | None = None
    source: str  # which system produced the item: "llm_v1", "heuristic_v1", ...
    position: int | None = None  # rank in the list shown, for position-bias correction later


class FeedbackRequest(BaseModel):
    """Body of POST /feedback: the "I cooked it" and thumbs buttons.

    Sending the same rating again clears it (a toggle). The server writes an event
    and returns the updated RecipeUserState."""

    item_type: ItemType = "recipe"
    item_id: str
    type: Literal["thumbs_up", "thumbs_down", "cooked", "swap"]
    detail: str | None = None  # e.g. the swap the user made
