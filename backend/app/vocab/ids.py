"""ID types shared by every model.

Small, stable vocabularies are `Literal`s: Pydantic rejects unknown values, and the
generated TypeScript gets a union type (e.g. "celery" | "gluten" | ...), so typos fail
at compile time on the frontend too.

Large or growing vocabularies (cuisines, ~300 ingredients) are plain `str` aliases for
now. Step 1 adds the full lists + synonym maps in this package, and validation then
happens in code (unknown values map to "other" and get logged) rather than in the type.
"""

from typing import Literal

# The UK 14 major allergens (Food Information Regulations 2014).
AllergenId = Literal[
    "celery",
    "gluten",  # cereals containing gluten
    "crustaceans",
    "eggs",
    "fish",
    "lupin",
    "milk",
    "molluscs",
    "mustard",
    "tree_nuts",
    "peanuts",
    "sesame",
    "soya",
    "sulphites",
]

DietId = Literal[
    "vegetarian",
    "vegan",
    "pescatarian",
    "halal",
    "kosher",
    "gluten_free",
    "dairy_free",
]

EquipmentId = Literal[
    "oven",
    "grill",
    "hob",
    "microwave",
    "air_fryer",
    "slow_cooker",
    "blender",
    "food_processor",
]

SpiceLevel = Literal["none", "mild", "medium", "hot"]

# Open vocabularies: validated against app/vocab lists in code (Step 1), not in the type.
CuisineId = str
IngredientId = str
