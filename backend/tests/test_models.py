"""Step 0 checks: the models are internally consistent and round-trip through JSON."""

from datetime import UTC, datetime

import pytest
from pydantic import TypeAdapter, ValidationError

from app.models import (
    AllergenCheck,
    ChatMessage,
    HardConstraints,
    Ingredient,
    Recipe,
    RecipeContent,
    StoredRecipe,
    StreamEvent,
    TextContent,
    UserProfile,
)

NOW = datetime(2026, 11, 21, 18, 42, tzinfo=UTC)


def make_recipe() -> Recipe:
    return Recipe(
        title="Yoghurt-marinated chicken thighs with garlicky spinach",
        summary="A short yoghurt and lemon marinade keeps the thighs juicy.",
        cuisine_id="turkish",
        servings=2,
        prep_minutes=10,
        cook_minutes=18,
        difficulty="easy",
        spice_level="mild",
        ingredients=[
            Ingredient(name="boneless chicken thighs", ingredient_id="chicken_thigh", quantity=500, unit="g"),
            Ingredient(name="Greek yoghurt", ingredient_id="greek_yoghurt", quantity=150, unit="g"),
            Ingredient(name="salt and black pepper", unit="to taste"),
        ],
        main_ingredient_ids=["chicken_thigh", "spinach"],
        steps=["Mix the marinade.", "Grill the chicken.", "Wilt the spinach."],
        allergens_present=["milk"],
        suggested_tweaks=["Make it vegetarian", "Less garlic"],
    )


def make_stored() -> StoredRecipe:
    return StoredRecipe(
        id="r1",
        chat_id="c1",
        recipe=make_recipe(),
        allergen_check=AllergenCheck(passed=True, checked_allergens=["peanuts"]),
        created_at=NOW,
    )


def test_profile_round_trip():
    p = UserProfile(
        display_name="Sam",
        hard=HardConstraints(allergens=["peanuts"], other_allergens=["kiwi"]),
        created_at=NOW,
        updated_at=NOW,
    )
    assert UserProfile.model_validate_json(p.model_dump_json()) == p


def test_old_profile_document_still_loads():
    """A minimal doc as written by an older version: every newer field missing."""
    old = {"hard": {"allergens": ["milk"]}, "created_at": NOW.isoformat(), "updated_at": NOW.isoformat()}
    p = UserProfile.model_validate(old)
    assert p.schema_version == 1
    assert p.display_name is None
    assert p.hard.other_allergens == []


def test_unknown_allergen_rejected():
    with pytest.raises(ValidationError):
        HardConstraints(allergens=["peanut"])  # typo: the vocabulary ID is "peanuts"


def test_stored_recipe_round_trip():
    s = make_stored()
    assert StoredRecipe.model_validate_json(s.model_dump_json()) == s


def test_message_content_discriminator():
    raw_recipe = {
        "id": "m2",
        "role": "assistant",
        "created_at": NOW.isoformat(),
        "content": {"kind": "recipe", "recipe": make_stored().model_dump(mode="json")},
    }
    raw_text = {"id": "m1", "role": "user", "created_at": NOW.isoformat(), "content": {"kind": "text", "text": "hi"}}
    assert isinstance(ChatMessage.model_validate(raw_recipe).content, RecipeContent)
    assert isinstance(ChatMessage.model_validate(raw_text).content, TextContent)


def test_stream_event_discriminator():
    adapter = TypeAdapter(StreamEvent)
    assert adapter.validate_python({"type": "status", "stage": "writing"}).stage == "writing"
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "status", "stage": "thinking"})


def test_recipe_json_schema_generates():
    """The writer agent will use Recipe as its ADK output_schema."""
    schema = Recipe.model_json_schema()
    assert "ingredients" in schema["properties"]
