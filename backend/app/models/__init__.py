"""Pydantic models: the single source of truth for every data shape.

FastAPI turns these into the OpenAPI schema, which generates the frontend's
TypeScript types. Change a shape here, never in the frontend.
"""

from app.models.chat import (
    Chat,
    ChatDetail,
    ChatMessage,
    DoneEvent,
    ErrorEvent,
    MessageContent,
    MessageEvent,
    RecipeContent,
    SendMessageRequest,
    StatusEvent,
    StreamEvent,
    TextContent,
)
from app.models.common import ErrorResponse, ItemType, Page, SourceLink
from app.models.event import Event, FeedbackRequest
from app.models.export import DataExport
from app.models.profile import (
    HardConstraints,
    MeResponse,
    Practical,
    ProfileUpdate,
    SoftPreferences,
    UsageInfo,
    UserProfile,
    Vocab,
    VocabEntry,
)
from app.models.recipe import (
    AllergenCheck,
    GenerationMetadata,
    Ingredient,
    Recipe,
    RecipeSummary,
    RecipeUserState,
    StoredRecipe,
)

__all__ = [
    "AllergenCheck",
    "Chat",
    "ChatDetail",
    "ChatMessage",
    "DataExport",
    "DoneEvent",
    "ErrorEvent",
    "ErrorResponse",
    "Event",
    "FeedbackRequest",
    "GenerationMetadata",
    "HardConstraints",
    "Ingredient",
    "ItemType",
    "MeResponse",
    "MessageContent",
    "MessageEvent",
    "Page",
    "Practical",
    "ProfileUpdate",
    "Recipe",
    "RecipeContent",
    "RecipeSummary",
    "RecipeUserState",
    "SendMessageRequest",
    "SoftPreferences",
    "SourceLink",
    "StatusEvent",
    "StoredRecipe",
    "StreamEvent",
    "TextContent",
    "UsageInfo",
    "UserProfile",
    "Vocab",
    "VocabEntry",
]
