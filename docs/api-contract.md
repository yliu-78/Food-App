# API contract

The agreement between the frontend (Next.js) and the backend (FastAPI on Cloud Run). **The Pydantic models in [`backend/app/models/`](../backend/app/models/) are the source of truth.** This document is the readable index: which endpoint each screen calls and which model field each piece of the UI shows. If the two disagree, the models win and this file should be fixed.

Screens referenced below are in [`frontend-design/Food App Mockups-png/`](../frontend-design/Food%20App%20Mockups-png/).

## Conventions

- **Auth.** Every endpoint except `GET /healthz` needs `Authorization: Bearer <Firebase ID token>`. The backend verifies the token and takes `uid` from it. The client never sends a uid, and never sends the profile with a request.
- **JSON.** Field names are `snake_case`, the same as in Python. Timestamps are ISO 8601 in UTC, and the frontend formats them for display ("Today", "12 Nov").
- **Errors.** Every non-2xx response has an `ErrorResponse { code, message, retry_after_seconds? }` body. Codes:

  | HTTP | `code` | When |
  |---|---|---|
  | 401 | `unauthenticated` | missing or invalid token |
  | 404 | `not_found` | unknown id, or an id belonging to another user |
  | 422 | `validation_error` | the body doesn't match the model (FastAPI does this automatically) |
  | 429 | `rate_limited` | 30 generations per day reached; `retry_after_seconds` is set |
  | 502 | `generation_failed` | Gemini error or timeout |

- **Lists.** These return `Page[T] { items, next_cursor, total? }`. To get the next page, pass `?cursor=<next_cursor>`.
- **Versioning.** Fields are only ever **added**, and always as optional with a default. Renaming or removing a field is a breaking change, because old phones keep running old frontend code for a while after a deploy.

## Endpoints

The 17 endpoints are defined in [`backend/app/routers/`](../backend/app/routers/) (one file per resource; `app/main.py` wires them up). Each function's signature is the contract: path, method, request body, query params, response model and error codes. Its docstring names the screen and button that calls it. The bodies are stubs that return `501` until the slice that implements them.

To browse them with request/response examples and a "Try it out" button:
```
cd backend
uv run fastapi dev app/main.py     # then open http://127.0.0.1:8000/docs
```
The raw schema that `openapi-typescript` will read is at `/openapi.json`. `tests/test_api.py` fails if an endpoint is added or removed without updating its `CONTRACT` list.

### Behaviour notes

- **`GET /me`** returns `profile: null` for a new user, and the frontend then sends them to onboarding. It also carries `usage` ("Recipes left today 27 / 30") and `saved_count` (the "Saved 12" badge), so the app shell needs only one request.
- **`PUT /profile`** replaces the whole editable profile. Onboarding keeps its answers in the browser across the 6 steps and sends them once at the end with `complete_onboarding: true`. A half-finished onboarding therefore leaves nothing behind.
- **`POST /chats/{id}/messages`** returns Server-Sent Events. This is one HTTP response that stays open, and the server writes a line each time something happens:
  ```
  data: {"type":"message","message":{...the user's message, now saved...}}
  data: {"type":"status","stage":"researching"}
  data: {"type":"status","stage":"writing"}
  data: {"type":"status","stage":"checking_allergens"}
  data: {"type":"status","stage":"saving"}
  data: {"type":"message","message":{...assistant message with kind:"recipe"...}}
  data: {"type":"done","latency_ms":14200,"usage_remaining":26}
  ```
  **Errors come in two kinds.** Once the first event is sent, the HTTP status (`200`) can't change. So checks that can be made up front (unknown chat → `404`, limit reached → `429`) run in FastAPI dependencies **before** the stream opens, and return a normal `ErrorResponse`. Anything that fails after that (Gemini error, the allergen check failing twice) is sent as `{"type":"error",...}` inside the stream, which then closes. The rate-limit counter goes up **before** Gemini is called, so failed requests still count.
  Tweaks are plain messages. The server sends the last few messages and the profile context to the agent, so the client doesn't send any history.
- **`POST /chats/{id}/clear`** keeps the chat itself but deletes its messages and any **unsaved** recipes from it. Saved recipes have their `chat_id` set to null. Events and the profile are kept, as the confirm dialog (screen 5) says.
- **`DELETE /profile/activity`** deletes the user's `events` and `user_features`. Saved recipes stay, and the user state on each recipe (saved, cooked, rating) is left as it is.
- **`GET /profile/export`** returns a `DataExport` (profile, chats with messages, recipes, events) as a file download.
- **`DELETE /profile`** deletes everything for the uid: the profile, chats, messages, recipes, events, features and usage, and finally the Firebase Auth user.
- **`POST /feedback`** works as a toggle. Sending `thumbs_up` while the rating is already `"up"` clears it. Every call appends an event either way.
- **Saved page search and filters** (Cooked, Under 30 min, Vegetarian, Liked) run in the browser over the `RecipeSummary` list. Firestore has no full-text search, and pilot users will have dozens of recipes, not thousands.

## Screen → endpoint and field mapping

### 1. Sign in
- "Continue with Google" uses the Firebase Auth SDK in the browser (no backend endpoint), then calls `GET /me`.
- ⚠️ The mockup still shows email/password, "Create an account" and "Forgot password?". These are **out of scope** (Google only) and should be removed.

### 2. Onboarding (6 steps)
| Step | UI | Field |
|---|---|---|
| 1 Food rules | Allergy chips, "None" | `hard.allergens` (empty list = None) |
| | "Something else?" | `hard.other_allergens` |
| | Dietary chips, "No rules" | `hard.dietary_rules` (empty list = No rules) |
| 2 Cuisines | likes / dislikes | `soft.cuisines` (+0.5 / −0.5) |
| 3 Spice | | `soft.spice_tolerance` |
| 4 Skill and time | | `practical.cooking_skill`, `practical.typical_time_minutes` |
| 5 Kitchen kit | | `practical.equipment` |
| 6 Household | people, budget | `practical.household_size`, `practical.budget_level` |
| Chip labels | | `GET /vocab` |
| Finish | | `PUT /profile` with `complete_onboarding: true` |

### 3. Home / new session
| UI | Source |
|---|---|
| "What do you want to cook, Sam?" | `MeResponse.profile.display_name` |
| "Using your profile" chips | `profile.hard.allergens`, `practical.cooking_skill`, `practical.typical_time_minutes`, `practical.household_size` |
| Recipe / Restaurants toggle | `SendMessageRequest.mode` (only `"recipe"` for now) |
| "Serves 2", "Max 30 min" | `SendMessageRequest.servings`, `.max_minutes` (defaults come from the profile) |
| Suggestion cards | static text in the frontend; clicking one fills the prompt box |
| Recent recipes | `GET /recipes?limit=3` → `title`, `total_minutes`, `cuisine_id` |
| Send | `POST /chats`, then `POST /chats/{id}/messages` |

### 4 and 8. Session with a recipe (desktop and mobile)
| UI | Source |
|---|---|
| Header title, "Started 18:42 · 1 recipe" | `Chat.title`, `Chat.created_at`, `Chat.recipe_count` |
| User bubble | `ChatMessage{role:"user"}.content.text` |
| ✓ progress chips | `StatusEvent.stage` while streaming; once done, all are shown as ticked |
| "14.2 s" | `DoneEvent.latency_ms` (live) / `StoredRecipe.generation.latency_ms` |
| "Checked: no peanuts" | `StoredRecipe.allergen_check.checked_allergens` |
| "Contains: milk" | `Recipe.allergens_present` |
| "Turkish-inspired" | `Recipe.cuisine_id` → label from `/vocab` |
| Title, summary | `Recipe.title`, `.summary` |
| Prep / Cook / Total | `prep_minutes`, `cook_minutes` (Total = sum, computed in the frontend) |
| Serves / Difficulty (Level) / Spice | `servings`, `difficulty`, `spice_level` |
| Ingredient rows | `ingredients[].quantity`, `.unit`, `.name`, `.notes` |
| Method | `steps[]` |
| "Swap: …" | `substitutions[]` |
| Inspired by | `sources[].title`, `.domain`, `.url` |
| Google Search suggestions slot | `generation.search_entry_point_html` |
| Save / I cooked it / 👍 👎 (on/off state) | `StoredRecipe.user_state` |
| Tweak chips | `Recipe.suggested_tweaks` |
| Clear session button | `POST /chats/{id}/clear` |

### 5. Clear session (confirm)
- "Clear session" calls `POST /chats/{id}/clear`. "Nothing to clear yet" is shown when `Chat.recipe_count == 0` and there are no messages.

### 6. Saved
| UI | Source |
|---|---|
| "Recipes · 12" | `MeResponse.saved_count` |
| Restaurants SOON tab | static for now |
| Card: cuisine, title, summary | `RecipeSummary.cuisine_id`, `.title`, `.summary` |
| "Cooked" / "Not cooked" | `.cooked` |
| "28 min · Serves 2 · Saved today" | `.total_minutes`, `.servings`, `.saved_at` |
| Filters: Cooked / Under 30 min / Vegetarian / Liked | `.cooked`, `.total_minutes <= 30`, `"vegetarian" in .dietary_tags`, `.rating == "up"` |
| Search | client-side over `.title` + `.summary` |

### 7. Profile
| Section | UI | Source |
|---|---|---|
| Personal details | Name | `profile.display_name` |
| | Email, Signed in with | `MeResponse.email`, `.auth_provider` (read-only) |
| | People you usually cook for | `practical.household_size` |
| Food rules | Allergies, Dietary rules | `hard.allergens`, `hard.dietary_rules` |
| Preferences | Cuisines you like | `soft.cuisines` (selected = +0.5) |
| | Ingredients you avoid | `soft.ingredients` (−1.0); "+ Add" searches `/vocab` ingredients |
| | Spice, Cooking skill, Usual time, Budget | `soft.spice_tolerance`, `practical.cooking_skill`, `.typical_time_minutes`, `.budget_level` |
| | Kitchen kit | `practical.equipment` |
| Save changes | | `PUT /profile` |
| Data and privacy | Request download / Clear history / Delete profile | `GET /profile/export`, `DELETE /profile/activity`, `DELETE /profile` |

### 9. Mobile menu drawer / sidebar
| UI | Source |
|---|---|
| Chat / Saved (count) / Profile | navigation; count from `MeResponse.saved_count` |
| Sessions list | `GET /chats` → `title`, `updated_at` |
| Recipes left today | `MeResponse.usage.used` / `.limit` (updated live by `DoneEvent.usage_remaining`) |
| Name, email, initials | `profile.display_name`, `MeResponse.email` |

## Open questions

1. **Free-text allergens** (`other_allergens`) can only be string-matched against ingredient names, so they aren't guaranteed. Should the UI warn about this when someone adds one?
2. **Onboarding cuisine dislikes.** The onboarding step says "likes and dislikes", but the profile page only shows "Cuisines you like". Should the profile page also show dislikes?
3. **Assistant text replies.** The mockups only show recipe replies. `kind: "text"` is reserved for clarifying questions or "I can't do that safely" answers. Do we want those in the MVP, or should every reply be a recipe?
