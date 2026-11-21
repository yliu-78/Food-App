"""POST /feedback: the "I cooked it" and thumbs buttons. Each call appends an event
(the recommender's training data) and updates the recipe's RecipeUserState.

See chats.py for the annotated walkthrough of how a router file is put together.
"""

from fastapi import APIRouter, HTTPException

from app.auth import CurrentUser
from app.errors import NOT_IMPLEMENTED, errors
from app.models import FeedbackRequest, RecipeUserState

router = APIRouter(tags=["feedback"])


@router.post("/feedback", responses=errors(401, 404))
def post_feedback(body: FeedbackRequest, uid: CurrentUser) -> RecipeUserState:
    """Recipe card → "I cooked it", 👍 or 👎. A toggle: sending the current rating again clears it. Always appends an event."""
    raise HTTPException(501, NOT_IMPLEMENTED)
