"""The user's stated profile (onboarding, Profile page) and the data-and-privacy
actions: export, clear activity history, delete everything.

See chats.py for the annotated walkthrough of how a router file is put together.
"""

from fastapi import APIRouter, HTTPException

from app.auth import CurrentUser
from app.errors import NOT_IMPLEMENTED, errors
from app.models import DataExport, ProfileUpdate, UserProfile

# Every route's path is relative to the prefix, so "" is /profile itself.
router = APIRouter(prefix="/profile", tags=["profile"])


@router.put("", responses=errors(401))
def put_profile(body: ProfileUpdate, uid: CurrentUser) -> UserProfile:
    """Onboarding → "Finish" (with `complete_onboarding: true`); Profile → "Save changes". Replaces the whole editable profile."""
    raise HTTPException(501, NOT_IMPLEMENTED)


@router.get("/export", responses=errors(401))
def export_profile(uid: CurrentUser) -> DataExport:
    """Profile → Data and privacy → "Request download". Everything stored about the user, as a JSON file."""
    # TODO: set `Content-Disposition: attachment; filename=food-app-export.json` so the browser downloads it.
    raise HTTPException(501, NOT_IMPLEMENTED)


# 204 No Content: success with an empty body, hence the `-> None` return type.
@router.delete("/activity", status_code=204, responses=errors(401))
def clear_activity(uid: CurrentUser) -> None:
    """Profile → Data and privacy → "Clear history". Deletes events and derived features; keeps saved recipes and the profile."""
    raise HTTPException(501, NOT_IMPLEMENTED)


@router.delete("", status_code=204, responses=errors(401))
def delete_profile(uid: CurrentUser) -> None:
    """Profile → Data and privacy → "Delete profile". Deletes everything for this user, including the Firebase Auth account."""
    raise HTTPException(501, NOT_IMPLEMENTED)
