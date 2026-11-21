"""GET /me: the app shell's one call on load (sidebar, greeting, onboarding redirect).

See chats.py for the annotated walkthrough of how a router file is put together.
"""

from fastapi import APIRouter, HTTPException

from app.auth import CurrentUser
from app.errors import NOT_IMPLEMENTED, errors
from app.models import MeResponse

# No prefix: the full path is written on the route. `tags` groups it on /docs.
router = APIRouter(tags=["me"])


@router.get("/me", responses=errors(401))
def get_me(uid: CurrentUser) -> MeResponse:
    """Every screen, on app load: fills the sidebar (name, saved count, recipes left today). `profile: null` sends a new user to onboarding."""
    raise HTTPException(501, NOT_IMPLEMENTED)
