"""Recipes.

Two layers:
- `Recipe` is what the writer agent produces (its ADK `output_schema`). It contains
  only things the LLM decides.
- `StoredRecipe` wraps it with things the *system* knows: IDs, the allergen-check
  result, generation metadata and the user's state (saved, cooked, rating).
  Stored at Firestore `users/{uid}/recipes/{recipeId}`.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.common import SourceLink
from app.vocab.ids import AllergenId, CuisineId, DietId, IngredientId, SpiceLevel


class Ingredient(BaseModel):
    name: str  # as displayed: "boneless chicken thighs"
    ingredient_id: IngredientId | None = None  # mapped to the vocabulary; used by the allergen checker
    quantity: float | None = None  # null for "to taste"
    unit: str | None = None  # "g", "tsp", "to taste"
    notes: str | None = None  # "1 grated, 2 sliced"


class Recipe(BaseModel):
    """The structured recipe the writer agent returns. The frontend renders it as a
    card; there's no free-form markdown anywhere."""

    schema_version: int = 1
    title: str
    summary: str
    cuisine_id: CuisineId
    servings: int = Field(ge=1)
    prep_minutes: int = Field(ge=0)
    cook_minutes: int = Field(ge=0)  # the card's "Total" = prep + cook, computed on the frontend
    difficulty: Literal["easy", "medium", "hard"]
    spice_level: SpiceLevel
    ingredients: list[Ingredient]
    main_ingredient_ids: list[IngredientId] = []  # snapshotted into events as features
    steps: list[str]
    equipment: list[str] = []
    dietary_tags: list[DietId] = []
    allergens_present: list[AllergenId] = []  # the model's declaration; double-checked by code. Drives "Contains: milk"
    substitutions: list[str] = []  # "Swap: chicken thighs for firm tofu..."
    sources: list[SourceLink] = []  # filled from grounding metadata, not by the LLM
    suggested_tweaks: list[str] = Field(
        default=[],
        max_length=4,
        description='Short follow-ups shown as chips under the card ("Make it vegetarian").',
    )


class AllergenCheck(BaseModel):
    """Result of the deterministic check in safety/allergens.py. A recipe that fails
    is never shown, so `passed` is always true on recipes the client sees; the field
    exists for stored debugging and eval data."""

    passed: bool
    checked_allergens: list[AllergenId]  # drives the "Checked: no peanuts" badge
    checked_other: list[str] = []  # free-text allergens that were string-matched
    attempts: int = 1  # 2 if the first generation failed and was regenerated


class GenerationMetadata(BaseModel):
    """How the recipe was produced: for debugging, evals, cost tracking and future
    training data. Mostly hidden from users; latency_ms drives the "14.2 s" label."""

    prompt: str
    model: str
    pipeline_version: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    research_notes: str | None = None
    search_queries: list[str] = []
    search_entry_point_html: str | None = Field(
        default=None,
        description="Google Search suggestions widget, if grounding display rules require showing it.",
    )


class RecipeUserState(BaseModel):
    """The current state of the buttons on a recipe card. The event log keeps the full
    history; this is just "what is true now", so the card renders correctly."""

    saved: bool = False
    saved_at: datetime | None = None
    cooked: bool = False
    rating: Literal["up", "down"] | None = None


class StoredRecipe(BaseModel):
    """GET /recipes/{id}, and the recipe inside a chat message."""

    id: str
    chat_id: str | None  # null if the chat was cleared but the recipe was saved
    recipe: Recipe
    allergen_check: AllergenCheck
    user_state: RecipeUserState = RecipeUserState()
    generation: GenerationMetadata | None = None  # omitted from list/chat responses to keep them small
    created_at: datetime


class RecipeSummary(BaseModel):
    """One card on the Saved page or in Home's "Recent recipes". Contains everything
    the client-side filters need (Cooked, Under 30 min, Vegetarian, Liked) and the
    search box (title + summary)."""

    id: str
    title: str
    summary: str
    cuisine_id: CuisineId
    total_minutes: int
    servings: int
    dietary_tags: list[DietId] = []
    saved: bool
    saved_at: datetime | None = None
    cooked: bool = False
    rating: Literal["up", "down"] | None = None
    created_at: datetime
