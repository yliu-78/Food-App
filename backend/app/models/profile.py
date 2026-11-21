"""User profile (layer 1 in HANDOFF §5): what the user told us.

Versioning rule: new fields are ALWAYS optional with a default. Firestore documents
written by older code then still load, and an older frontend still works against a
newer backend.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.vocab.ids import AllergenId, CuisineId, DietId, EquipmentId, IngredientId, SpiceLevel


class HardConstraints(BaseModel):
    """Rules a recipe must never break. Enforced in code (safety/allergens.py) after
    generation, never only in the prompt.

    An empty list means the user explicitly chose "None" / "No rules"; onboarding
    makes this step required, so empty never means "didn't answer"."""

    allergens: list[AllergenId] = []
    dietary_rules: list[DietId] = []
    other_allergens: list[str] = Field(
        default=[],
        description=(
            'Free text from the "Something else?" link. Not in the vocabulary, so '
            "the checker can only string-match these: best effort, not guaranteed."
        ),
    )


class SoftPreferences(BaseModel):
    """Nudges, not rules. Weights in [-1, 1].

    These act as cold-start priors: a future recommender blends them with what it
    learns from events. Onboarding/profile chips set: liked cuisine +0.5,
    avoided ingredient -1.0."""

    cuisines: dict[CuisineId, float] = {}
    ingredients: dict[IngredientId, float] = {}
    spice_tolerance: SpiceLevel | None = None


class Practical(BaseModel):
    """Practical limits on what the user can cook."""

    cooking_skill: Literal["beginner", "intermediate", "advanced"] | None = None
    equipment: list[EquipmentId] = []
    typical_time_minutes: Literal[15, 30, 45, 60] | None = None  # 60 means "60+"
    household_size: int | None = Field(default=None, ge=1, le=20)
    budget_level: Literal["low", "medium", "high"] | None = None


class UserProfile(BaseModel):
    """Stored at Firestore `users/{uid}`. Agents never read this directly: they
    only see the output of build_profile_context(uid)."""

    schema_version: int = 1
    display_name: str | None = None  # editable "Name"; drives the greeting and avatar initials
    hard: HardConstraints
    soft: SoftPreferences = SoftPreferences()
    practical: Practical = Practical()
    onboarding_completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    """Body of PUT /profile: the whole editable profile, sent by onboarding (once, at
    the end) and by the profile page's "Save changes".

    Timestamps and schema_version are absent because the server sets them; the
    client is never trusted with them."""

    display_name: str | None = Field(default=None, max_length=80)
    hard: HardConstraints
    soft: SoftPreferences = SoftPreferences()
    practical: Practical = Practical()
    complete_onboarding: bool = False  # true on the last onboarding step


class UsageInfo(BaseModel):
    """Drives the sidebar's "Recipes left today 27 / 30"."""

    used: int
    limit: int
    resets_at: datetime


class MeResponse(BaseModel):
    """GET /me: everything the app shell needs on load, in one call.

    `profile` is null for a brand-new user, so the frontend routes them to onboarding.
    `email` and `auth_provider` come from the Firebase token (read-only on the
    profile page), so they're not stored in UserProfile."""

    uid: str
    email: str | None
    auth_provider: Literal["google"]
    profile: UserProfile | None
    usage: UsageInfo
    saved_count: int


class VocabEntry(BaseModel):
    id: str
    label: str


class Vocab(BaseModel):
    """GET /vocab: ID → display label lists for every chip on the onboarding and
    profile screens, so the frontend doesn't keep its own copy that can drift."""

    allergens: list[VocabEntry]
    diets: list[VocabEntry]
    cuisines: list[VocabEntry]
    equipment: list[VocabEntry]
    ingredients: list[VocabEntry]
