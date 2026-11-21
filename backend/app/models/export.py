"""GET /profile/export: everything stored about the user, as one JSON download
(the GDPR right of access). This is the only place `Event` is sent over the API."""

from datetime import datetime

from pydantic import BaseModel

from app.models.chat import ChatDetail
from app.models.event import Event
from app.models.profile import UserProfile
from app.models.recipe import StoredRecipe


class DataExport(BaseModel):
    exported_at: datetime
    uid: str
    email: str | None
    profile: UserProfile | None
    chats: list[ChatDetail]  # each chat with its messages
    recipes: list[StoredRecipe]  # saved and unsaved, with generation metadata
    events: list[Event]
