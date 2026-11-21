"""GET /vocab: the ID → label lists behind every chip on the onboarding and
profile screens, served from app/vocab so the frontend never keeps its own copy.

See chats.py for the annotated walkthrough of how a router file is put together.
"""

from fastapi import APIRouter, HTTPException

from app.auth import CurrentUser
from app.errors import NOT_IMPLEMENTED, errors
from app.models import Vocab

router = APIRouter(tags=["vocab"])


@router.get("/vocab", responses=errors(401))
def get_vocab(uid: CurrentUser) -> Vocab:
    """Onboarding and Profile: the labels for every chip (allergens, diets, cuisines, kit, ingredients)."""
    raise HTTPException(501, NOT_IMPLEMENTED)
