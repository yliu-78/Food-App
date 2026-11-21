"""Chat sessions.

Firestore layout:
    users/{uid}/chats/{chatId}                 Chat
    users/{uid}/chats/{chatId}/messages/{id}   ChatMessage
    users/{uid}/recipes/{recipeId}             StoredRecipe (chat_id points back)

Messages live in a subcollection because a Firestore document is capped at 1 MiB.
Recipes live outside the chat so "Clear session" can wipe messages without losing
saved recipes.

A tweak ("make it vegetarian") is just the next user message. The backend sends the
last few messages from Firestore to the agent as context; ADK sessions are only kept
for the length of one request (HANDOFF §6).
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.models.recipe import StoredRecipe


class Chat(BaseModel):
    """One session in the sidebar. The title is generated from the first message."""

    id: str
    title: str
    created_at: datetime  # header: "Started today, 18:42"
    updated_at: datetime  # sidebar ordering + "Today" / "Yesterday" / "12 Nov"
    recipe_count: int = 0  # header: "1 recipe"


# --- Message content ---------------------------------------------------------
# A discriminated union: the `kind` field says which shape this is. Pydantic picks
# the right class when parsing, and the TypeScript type lets the frontend `switch`
# on `kind` to render a text bubble or a recipe card.
#
# To add restaurants later: define RestaurantListContent(kind="restaurants") and add
# it to the union. Nothing else changes.


class TextContent(BaseModel):
    kind: Literal["text"] = "text"
    text: str


class RecipeContent(BaseModel):
    kind: Literal["recipe"] = "recipe"
    recipe: StoredRecipe


MessageContent = Annotated[TextContent | RecipeContent, Field(discriminator="kind")]


class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: MessageContent
    created_at: datetime


class ChatDetail(BaseModel):
    """GET /chats/{id}: the chat plus its messages, oldest first."""

    chat: Chat
    messages: list[ChatMessage]


# --- Sending a message -------------------------------------------------------


class SendMessageRequest(BaseModel):
    """Body of POST /chats/{id}/messages. The profile is never sent by the client;
    the server loads it from Firestore."""

    text: str = Field(min_length=1, max_length=1000)
    mode: Literal["recipe"] = "recipe"  # the Recipe / Restaurants toggle; add "restaurants" later
    servings: int | None = Field(default=None, ge=1, le=20)  # "Serves 2" control
    max_minutes: int | None = Field(default=None, ge=5, le=240)  # "Max 30 min" control


# --- Streamed response (Server-Sent Events) ----------------------------------
# POST /chats/{id}/messages answers with a stream of these, one per SSE `data:` line:
#   status(researching) → status(writing) → status(checking_allergens)
#   → status(saving) → message → done
# The status events drive the progress chips ("✓ Researched ideas" ...).

Stage = Literal["researching", "writing", "checking_allergens", "saving"]


class StatusEvent(BaseModel):
    type: Literal["status"] = "status"
    stage: Stage


class MessageEvent(BaseModel):
    """Sent once per new message: first the saved user message, then the assistant's."""

    type: Literal["message"] = "message"
    message: ChatMessage


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    latency_ms: int
    usage_remaining: int  # updates "Recipes left today" without another request


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str  # "rate_limited", "allergen_check_failed", "generation_failed"
    message: str


StreamEvent = Annotated[
    StatusEvent | MessageEvent | DoneEvent | ErrorEvent, Field(discriminator="type")
]
