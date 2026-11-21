"""Chat sessions: the sidebar's session list, the session screen, and sending messages.

The request flow (see docs/api-contract.md):
    "New session"  → POST /chats                       → Chat (empty)
    Send           → POST /chats/{chat_id}/messages    → SSE stream of StreamEvent
    Open a session → GET  /chats/{chat_id}             → ChatDetail (chat + messages)

How to read a route (the other router files follow the same pattern):
    @router.get("/{chat_id}", responses=errors(401, 404))
        method + path (relative to the router's prefix, so GET /chats/{chat_id});
        `responses` documents the error codes on /docs and in the generated
        TypeScript types.
    def get_chat(chat_id: str, uid: CurrentUser)
        `chat_id` is filled from `{chat_id}` in the path; `CurrentUser` runs the
        auth dependency first. A Pydantic model parameter (like `body:
        SendMessageRequest` on send_message) is read from the JSON request body.
    -> ChatDetail
        the response model: FastAPI validates and serialises the return value
        with it, and it's what /docs shows as the response shape.
    Docstring: shown on /docs. It names the screen and button that calls it.
"""

from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.sse import EventSourceResponse

from app.auth import CurrentUser
from app.errors import NOT_IMPLEMENTED, errors, not_implemented
from app.models import Chat, ChatDetail, Page, SendMessageRequest, StreamEvent

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", responses=errors(401))
def create_chat(uid: CurrentUser) -> Chat:
    """Sidebar → "New session" (or the first Send on Home). Creates an empty chat; the first message sets its title."""
    raise HTTPException(501, NOT_IMPLEMENTED)


@router.get("", responses=errors(401))
def list_chats(uid: CurrentUser, cursor: str | None = None) -> Page[Chat]:
    """Sidebar → "Sessions" list, newest first. Pass `next_cursor` back as `?cursor=` to get more."""
    raise HTTPException(501, NOT_IMPLEMENTED)


@router.get("/{chat_id}", responses=errors(401, 404))
def get_chat(chat_id: str, uid: CurrentUser) -> ChatDetail:
    """Clicking a session in the sidebar: the chat header plus all its messages, oldest first."""
    raise HTTPException(501, NOT_IMPLEMENTED)


@router.post(
    "/{chat_id}/messages",
    response_class=EventSourceResponse,
    dependencies=[Depends(not_implemented)],  # stub: remove when implemented
    responses=errors(401, 404, 429),
)
async def send_message(
    chat_id: str, body: SendMessageRequest, uid: CurrentUser
) -> AsyncIterable[StreamEvent]:
    """Session → Send button, or a tweak chip. Streams Server-Sent Events: the saved user message, status stages, the assistant's message, then `done`."""
    # Once this generator starts, the 200 status line has already gone to the
    # client, so an HTTPException raised in here can't change it. Checks that must
    # return a real 404 or 429 (the chat exists and belongs to uid; the rate limit)
    # go in dependencies, which run before the stream opens, like `not_implemented`
    # above. Failures during generation (a Gemini error, or the allergen check
    # failing twice) are sent as an ErrorEvent.
    return
    yield  # never reached; its presence makes this a generator, which streaming needs


@router.post("/{chat_id}/clear", responses=errors(401, 404))
def clear_chat(chat_id: str, uid: CurrentUser) -> Chat:
    """Session → "Clear session" → confirm. Deletes messages and unsaved recipes; keeps the chat, saved recipes, events and profile."""
    raise HTTPException(501, NOT_IMPLEMENTED)
