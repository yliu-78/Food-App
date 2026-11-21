"""Recipes the user has generated: the Saved page, Home's "Recent recipes", and
the Save / un-save button. Generation itself happens in chats.py (send_message).

See chats.py for the annotated walkthrough of how a router file is put together.
"""

from fastapi import APIRouter, HTTPException, Query

from app.auth import CurrentUser
from app.errors import NOT_IMPLEMENTED, errors
from app.models import Page, RecipeSummary, RecipeUserState, StoredRecipe

router = APIRouter(prefix="/recipes", tags=["recipes"])


# Parameters that aren't in the path and aren't a Pydantic model become query
# parameters: GET /recipes?saved=true&limit=3&cursor=... `Query(...)` adds
# validation; a value outside 1..100 gets an automatic 422.
@router.get("", responses=errors(401))
def list_recipes(
    uid: CurrentUser,
    saved: bool | None = None,  # None = all recipes, saved or not
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,  # `next_cursor` from the previous page
) -> Page[RecipeSummary]:
    """Saved page (`?saved=true`); Home → "Recent recipes" (`?limit=3`). Newest first; search and filters run in the browser."""
    raise HTTPException(501, NOT_IMPLEMENTED)


@router.get("/{recipe_id}", responses=errors(401, 404))
def get_recipe(recipe_id: str, uid: CurrentUser) -> StoredRecipe:
    """Saved page → clicking a recipe card. The full recipe, including `generation` metadata."""
    raise HTTPException(501, NOT_IMPLEMENTED)


# Save is modelled as a resource you PUT (create) or DELETE, rather than a toggle,
# so a retried request can't flip the state back.
@router.put("/{recipe_id}/save", responses=errors(401, 404))
def save_recipe(recipe_id: str, uid: CurrentUser) -> RecipeUserState:
    """Recipe card → "Save". Idempotent: saving twice has the same effect as saving once."""
    raise HTTPException(501, NOT_IMPLEMENTED)


@router.delete("/{recipe_id}/save", responses=errors(401, 404))
def unsave_recipe(recipe_id: str, uid: CurrentUser) -> RecipeUserState:
    """Recipe card → tapping "Saved" again to un-save."""
    raise HTTPException(501, NOT_IMPLEMENTED)
