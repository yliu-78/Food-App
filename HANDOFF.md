# Project Hand-off: AI Food App (MVP)

> Context for Claude Code. This file describes the product, the decisions already made, the architecture, and the build order. Treat the **Decisions** section as settled unless I say otherwise. Treat anything marked **VERIFY** as something to check against current docs before writing code, because the Google Cloud and Gemini APIs change quickly.

---

## About me, and why this app exists

**Background.** I'm an AI engineer. Most of my work has been backend and Python, and mostly local builds: models, pipelines and scripts that run on my own machine. I have little experience deploying things to the cloud. My only frontend experience is Streamlit apps, so I've never built a separate frontend that talks to a backend over HTTP, and I haven't used TypeScript, React, Next.js or CSS frameworks.

**Why I'm building this.** It's a real product with real pilot users, but it's also how I'm **learning fullstack development, with a particular focus on deployment**: Cloud Run, Firebase, IAM, secrets, CI/CD, and running a frontend and backend as separate services. Understanding how the pieces fit together matters as much as shipping them.

**How to work with me:**
- Explain frontend and deployment concepts from first principles, using Python, Streamlit or backend analogies where they help. Don't assume I know frontend or cloud vocabulary.
- When you introduce a new tool, pattern or command, briefly say **why** it's needed and what problem it solves, not only how to use it.
- On backend and Python work, you can be terser. That's my home ground, and I'm happy to write parts of it myself and have you review them.
- Prefer approaches I can understand and debug myself over clever ones I'd have to take on trust.

## 1. Product summary

An AI food app. Each user has a **profile** (preferences, constraints and behaviour data), and that profile drives recipe creation.

**Recipe creation (the MVP).** The user asks for something ("quick high-protein dinner with what's in my fridge"). An LLM agent researches the web and returns an original, structured recipe tailored to the user's profile.

**Restaurant recommendations are deferred until after the MVP** (see §7). The data model and recommendation pipeline are designed so they can be added later without rework.

The profile and the behaviour data behind it are the core asset. The long-term goal is a **recommender system working alongside an LLM agent**: the recommender ranks candidates, and the agent filters and explains them using extra context. The MVP uses simple heuristics, but it is structured so that swapping in a trained model doesn't require new infrastructure (see §5 and §6).

## 2. Constraints

- **Deadline:** deployed with real pilot users by **~22 Dec 2026**, then a code freeze (I'm away 28 Dec–5 Jan). A few pilot users are already signed up. The schedule is **fluid**: the timeline in §11 is the target, not a hard commitment.
- **Solo developer, spare time only** (assume about 12 hours a week). I'm an AI engineer, strong in Python, new to frontend and deployment (see "About me" above).
- **Everything runs on Google Cloud Platform**, using Google's SDKs for the agents (ADK + Gemini).
- **Web first.** Build a mobile-first, installable PWA. A native app (Expo/Capacitor wrapper) may come later and must be able to reuse the backend unchanged, so keep a clean API boundary.

## 3. Decisions (settled)

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router, TypeScript), Tailwind + shadcn/ui, mobile-first, PWA manifest (no offline caching in the MVP) |
| Frontend hosting | Firebase App Hosting (fallback: Cloud Run) |
| Auth | Firebase Auth, **Google sign-in only** for the MVP. The backend verifies Firebase ID tokens. |
| Database | Firestore (Native mode). See §5 for why. |
| Backend / agents | Python, FastAPI + Google **ADK** (Agent Development Kit), one service on **Cloud Run** |
| LLM | Gemini via Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI=True`) |
| Web research | Gemini **Grounding with Google Search** |
| API types | TS types generated from FastAPI's OpenAPI schema with `openapi-typescript`. Pydantic is the source of truth. |
| Secrets | Secret Manager |
| Observability | Structured JSON logs in Cloud Logging, plus a GCP billing budget alert. Cloud Trace / OTel is deferred. |
| Package mgmt | `uv` (Python, pin 3.12 or 3.13 to match the Cloud Run image; the local machine has 3.15), `pnpm` (frontend) |
| Region | `europe-west2` (London) for Cloud Run and Firestore. **VERIFY** which region or `global` endpoint supports the chosen Gemini model, and set the Vertex location separately if needed. |

Why Cloud Run rather than Agent Runtime (formerly Vertex AI Agent Engine): the agents and the app's REST API can live in one service, which keeps deployment and debugging simple. We can revisit this later if we need managed sessions or memory.

## 4. Repository layout

Use a monorepo:

```
food-app/
├── CLAUDE.md                 # auto-loaded by Claude Code; imports this file + docs/progress.md
├── HANDOFF.md                # this file: the spec
├── frontend-design/          # Step 0: mockups (PNG/PDF/HTML) + user flow (these are the wireframes)
├── docs/
│   ├── progress.md           # session log: what's done, decisions, next steps
│   └── api-contract.md       # Step 0: conventions, behaviour notes, screen → field mapping
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py           # FastAPI app, routers, CORS, auth dependency
│   │   ├── auth.py           # Firebase ID token verification (`CurrentUser` dependency)
│   │   ├── errors.py         # ErrorResponse docs helper (+ exception handlers in Step 2)
│   │   ├── config.py         # pydantic-settings (model name, MOCK_LLM, limits)
│   │   ├── db.py             # Firestore client + repositories
│   │   ├── vocab/            # fixed vocabularies: allergens, diets, cuisines, ingredients + synonyms
│   │   ├── models/           # Pydantic: common, profile, recipe, chat, event, export (+ features later)
│   │   ├── routers/          # me.py, profile.py, vocab.py, chats.py, recipes.py, feedback.py
│   │   ├── events.py         # event logger (append-only)
│   │   ├── features.py       # rebuild user_features from events
│   │   ├── recommend/        # CandidateSource / Ranker protocols + heuristic implementations
│   │   ├── agents/
│   │   │   └── recipe/       # ADK agents for recipe generation
│   │   └── safety/
│   │       └── allergens.py  # deterministic allergen check
│   ├── evals/                # prompt sets + scripts
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── app/                  # routes: / (new session), /onboarding, /chats/[id], /saved, /recipes/[id], /profile
│   ├── components/
│   ├── lib/                  # firebase client, generated api types + client, auth context
│   └── public/manifest.json
├── infra/
│   ├── setup.sh              # gcloud commands: enable APIs, service accounts, IAM, secrets
│   └── firestore.rules
└── .github/workflows/        # optional: deploy on push to main
```

## 5. Data model (Firestore)

### Why Firestore
The app's data is mostly small, structured records that are updated often. Firestore gives us queries ("last 20 recipes, newest first"), partial updates, transactions (for the rate-limit counter), security rules tied to Firebase Auth, a free tier, and zero cost when idle. Cloud Storage only stores whole files, so it's used only for things like eval outputs, exports and future model files. Firestore is weak at analytics, so when the recommender arrives, events are exported to BigQuery (a new paid service, so ask me first).

### Design principle: four layers
| Layer | Holds | MVP | Later |
|---|---|---|---|
| 1. Stated profile | What the user told us | `users/{uid}` with `schema_version` | Same document, new optional fields |
| 2. Event log | Everything the user did | Append-only `events` collection | Exported to BigQuery for training |
| 3. Derived features | What we inferred | `user_features/{uid}`, **rebuilt from events** | Embeddings or model outputs, same slot |
| 4. Profile view | What the agents see | `build_profile_context(uid)` | Same function, richer inputs |

Agents never read raw profile fields. They only call `build_profile_context()`.

### Collections
```
users/{uid}                        # stated profile (layer 1)
user_features/{uid}                # derived features (layer 3), rebuildable
users/{uid}/recipes/{recipeId}     # generated recipes (saved or not) + generation metadata + user_state; chat_id points back
users/{uid}/chats/{chatId}         # chat sessions (see §6 "Chat sessions")
users/{uid}/chats/{chatId}/messages/{messageId}
events/{eventId}                   # top-level, append-only (layer 2); top-level so export is one collection
usage/{uid}_{yyyymmdd}             # daily generation counter (rate limit)
```
Events are kept out of the user document because Firestore documents are capped at 1 MiB.

### Vocabularies (`app/vocab/`)
Every preference and recipe attribute refers to an ID from a fixed vocabulary, so it can be used as a feature later:
- Allergens: the UK 14, plus `other`
- Dietary rules: vegetarian, vegan, pescatarian, halal, kosher, gluten_free, dairy_free…
- Cuisines: about 40
- Canonical ingredients: start with about 300, each with a synonym map. The allergen checker shares this map.

Unknown values map to `other` and get logged, so the vocabularies can grow.

### UserProfile (layer 1)
```python
class HardConstraints(BaseModel):     # enforced in code, never only in the prompt
    allergens: list[AllergenId]
    dietary_rules: list[DietId]

class SoftPreferences(BaseModel):     # weights in [-1, 1]; onboarding chips set ±0.5
    cuisines: dict[CuisineId, float] = {}
    ingredients: dict[IngredientId, float] = {}
    spice_tolerance: Literal["none", "mild", "medium", "hot"] | None = None

class Practical(BaseModel):
    cooking_skill: Literal["beginner", "intermediate", "advanced"] | None = None
    equipment: list[EquipmentId] = []
    typical_time_minutes: int | None = None
    household_size: int | None = None
    budget_level: Literal["low", "medium", "high"] | None = None

class UserProfile(BaseModel):
    schema_version: int = 1
    hard: HardConstraints
    soft: SoftPreferences = SoftPreferences()
    practical: Practical = Practical()
    created_at: datetime
    updated_at: datetime
```
New fields are always optional with defaults, so old documents keep loading. Soft weights act as **cold-start priors** that a future model blends with what it learns.

### Event (layer 2)
```python
class Event(BaseModel):
    event_id: str
    uid: str
    ts: datetime
    type: Literal["impression", "view", "save", "cooked", "thumbs_up",
                  "thumbs_down", "swap", "regenerate", "dismiss"]
    item_type: Literal["recipe", "restaurant"]   # restaurant reserved for later
    item_id: str
    item_features: dict      # snapshot: cuisine_id, ingredient_ids, minutes, spice, difficulty
    context: dict            # request text, time of day, (later) location bucket
    request_id: str
    source: str              # "llm_v1", "heuristic_v1"... which system produced the item
    position: int | None     # rank in the list shown
```
Rules:
- **Log impressions.** Without them, "didn't like it" can't be told apart from "never saw it".
- **Snapshot `item_features` into each event.** Generated recipes are one-offs, so learning happens over attributes, not recipe IDs.
- **Record `source` and `position` from day one** for comparing model versions and correcting for position bias later.

### Derived features (layer 3)
`features.rebuild(uid)` recomputes `user_features/{uid}` from the event log. For the MVP it uses time-decayed counts and scores per cuisine and ingredient, plus a rejected-ingredients list. It's deterministic with no LLM. Because the features can always be rebuilt from events, we can change the logic or swap in a model and recompute everyone's features.

### Recipe documents
Store `Recipe.model_dump()` together with generation metadata: the user's prompt, model name, prompt and pipeline version, research notes, grounding sources, token counts, latency, allergen check result and `schema_version`. This doubles as debugging, eval and training data.

## 6. Recipe agent

### Behaviour
- Input: the user's free-text request, plus `build_profile_context(uid)` (loaded server-side, never trusted from the client).
- It researches the web for ideas and technique through Google Search grounding, then writes an **original** recipe. It must not copy recipe text from websites. It includes links to the sources that inspired it.
- Output: a **structured** `Recipe` object that the frontend renders as a card. No free-form markdown.

### Recipe schema
```python
class Ingredient(BaseModel):
    name: str
    ingredient_id: IngredientId | None   # mapped to the vocabulary
    quantity: float | None
    unit: str | None
    notes: str | None

class Recipe(BaseModel):
    schema_version: int = 1
    title: str
    summary: str
    cuisine_id: CuisineId
    servings: int
    prep_minutes: int
    cook_minutes: int
    difficulty: Literal["easy", "medium", "hard"]
    spice_level: Literal["none", "mild", "medium", "hot"]
    ingredients: list[Ingredient]
    main_ingredient_ids: list[IngredientId]
    steps: list[str]
    equipment: list[str]
    dietary_tags: list[DietId]
    allergens_present: list[AllergenId]   # model's declaration, double-checked by code
    substitutions: list[str]
    sources: list[SourceLink]             # {title, url} from grounding metadata
```

### Agent design
**VERIFY:** in ADK, the built-in `google_search` tool has historically had restrictions on being combined with other tools, and an agent with `output_schema` set can't use tools. Check the current ADK docs. If those restrictions still apply, use this two-stage pipeline:

1. `research_agent` (LlmAgent with the `google_search` tool) gathers ideas, techniques and typical ingredient ratios for the request and profile. It writes notes to session state (`output_key="research_notes"`).
2. `writer_agent` (LlmAgent with `output_schema=Recipe`, no tools) writes the original recipe from `research_notes` and the profile context.
3. Wrap both in a `SequentialAgent`.
4. **After generation, in plain Python:** run `safety/allergens.py`, which checks the ingredients (and the model's `allergens_present`) against the user's hard constraints using the vocabulary synonym map. If anything fails, regenerate once with an explicit correction. If it fails again, return an error to the user. Never show a recipe that fails the check.
5. Extract source URLs from the grounding metadata into `sources`. Also check Google's display requirements for Search grounding (search suggestions or attribution) and comply in the UI. **VERIFY.**

### ADK sessions
Use `InMemorySessionService` for the length of a single request. Firestore is the only source of truth. "Regenerate with a tweak" loads the previous recipe from Firestore and passes it in as context, so no persistent ADK sessions are needed. **VERIFY** the current session service options.

### Recommendation pipeline (the shape the recommender will slot into)
```
candidates = source.retrieve(user, context)    # MVP: the LLM recipe pipeline
candidates = hard_filter(candidates, profile)  # deterministic allergen/diet check, always runs
ranked     = ranker.rank(user, candidates)     # MVP: pass-through / weighted-preference heuristic
final      = llm_rerank_and_explain(ranked, extra_vars)   # later
```
`CandidateSource` and `Ranker` are small Python Protocols in `app/recommend/`. When the recommender arrives, a model-backed `Ranker` (and possibly a retrieval source) replaces the heuristic and nothing else changes. Later, Firestore's built-in vector search can hold recipe and user embeddings without adding a new service.

### Chat sessions (decided after the mockups, replaces "single prompt + regenerate")
The user works in **chat sessions**. Each user message gets an assistant reply whose content is a discriminated union on `kind` (`"recipe"` or `"text"`, with `"restaurants"` added later). A tweak ("make it vegetarian") is just the next message: the backend loads the last few messages from Firestore and passes them to the agent with `build_profile_context()`. ADK sessions are still per-request. "Clear session" empties a chat's messages and unsaved recipes but keeps saved recipes, events and the profile.

### Endpoints
**The endpoints are defined (as stubs) in `backend/app/routers/` and browsable at `/docs`; the shapes are in `backend/app/models/`; behaviour notes and the screen → field mapping are in [docs/api-contract.md](docs/api-contract.md).** SSE uses FastAPI's native `fastapi.sse.EventSourceResponse` (FastAPI ≥ 0.135). In summary: `GET /me`, `PUT /profile`, `GET /profile/export`, `DELETE /profile/activity`, `DELETE /profile`, `GET /vocab`, `POST|GET /chats`, `GET /chats/{id}`, `POST /chats/{id}/messages` (SSE stream), `POST /chats/{id}/clear`, `GET /recipes`, `GET /recipes/{id}`, `PUT|DELETE /recipes/{id}/save`, `POST /feedback`.
If pilots report generations that never finish (mobile browsers drop SSE connections when backgrounded), switch to writing status updates to a `generations/{id}` document that the client listens to.

### Feedback loop
- `POST /feedback` with `{item_id, type: "thumbs_up"|"thumbs_down"|"cooked"|"swap", detail?}` writes an event and updates the recipe's `user_state`.
- Events are append-only **except** for the user's own data-and-privacy actions ("Clear activity history", "Delete profile"), which delete that user's events.
- The backend also logs `impression`, `view`, `save` and `regenerate` events itself.
- `features.rebuild(uid)` updates `user_features/{uid}`, either after feedback or lazily before generation. A compact summary goes into the agent prompt through `build_profile_context()`. Don't use an LLM for this in the MVP.

### Mock mode
`MOCK_LLM=true` in config makes `POST /chats/{id}/messages` return a fixed recipe (still streaming the status events). Use it for frontend work and tests so they don't cost Gemini calls.

## 7. Restaurant recommendations (deferred until after the MVP)

Not part of the MVP. Already prepared for: `item_type: "restaurant"` in events, the `CandidateSource`/`Ranker` interface, and the `users/{uid}/places` collection. When it's picked up:
- `POST /restaurants/recommend` with `{lat, lng, occasion?, max_distance_km?, price?}`.
- One Gemini call using **Google Maps grounding** with `lat_lng` set, with the profile in the prompt. **VERIFY** regional availability and response shape (`groundingChunks` maps entries carry `uri`, `placeId` and `title`).
- Fallback: Places API (New) Text Search, then have Gemini rank and explain the results.
- Add `home_location` (coarse, with permission) to the profile as an optional field.

## 8. Frontend requirements

- **Mockups (the wireframes) are in `frontend-design/Food App Mockups-png/`**: 9 screens, plus the user flow. Every field and button is mapped to the API in [docs/api-contract.md](docs/api-contract.md). The sign-in mockup still shows email/password, which is out of scope (Google only).
- Mobile-first, so it must look good at 375px width. Desktop uses a sidebar layout (see the mockups).
- Screens:
  - Landing / sign-in (Google only)
  - Onboarding (multi-step, under 90 seconds: about 6 screens, mostly chips and toggles, everything except allergens and dietary rules skippable). **Fallback if time is short:** a single-page form.
  - App shell: a sidebar (a drawer on mobile) with New session, Chat / Saved / Profile, the sessions list, "Recipes left today" and the user's name
  - Home / new session: a "What do you want to cook?" prompt box with a Recipe/Restaurants (soon) toggle, serves and max-time controls, suggestion cards and recent recipes
  - Session (chat): user messages and recipe cards (ingredients, method, sources, allergen badges, save, "cooked it", thumbs), tweak chips, a "Clear session" confirm dialog
  - Saved: recipe cards with client-side search and filters
  - Profile edit: personal details, food rules, preferences, and data and privacy (download, clear history, delete)
- Progress UX while a recipe generates. Its design depends on the latency measured in Step 1. Skeleton states everywhere.
- PWA: manifest and icons for installability only. No service worker caching in the MVP.
- `lib/api.ts`: a typed client using the generated OpenAPI types that attaches the Firebase ID token to every request. The client talks to the backend API only, never Firestore directly (except possibly a `generations/{id}` status listener, see §6).

## 9. Security, cost and ops

- Every backend route except health checks requires a valid Firebase ID token. The `uid` comes from the token only.
- Firestore rules: a user can only read and write `users/{their uid}/**`. Everything else is denied to clients. The backend uses the Admin SDK with a service account.
- Rate limit: 30 recipe generations per user per day. Increment `usage/{uid}_{yyyymmdd}` in a transaction **before** calling Gemini, so failed or abandoned requests still count.
- Set a GCP billing budget alert during infra setup (`infra/setup.sh` should print a reminder or create it).
- Structured JSON logging with `uid`, `request_id`, latency, token counts and grounding usage.
- Keep secrets (if any beyond ADC) in Secret Manager. No API keys in the frontend apart from the public Firebase config.
- Cloud Run service account roles needed: Vertex AI User, Datastore User, Secret Manager accessor, Logs Writer.

## 10. Evals (lightweight, do not skip)

`backend/evals/recipe_prompts.yaml` holds 15–20 prompts paired with profiles. They must include:
- Allergy edge cases (nut allergy plus "pad thai", coeliac plus "pasta", dairy-free plus "carbonara")
- Vegetarian or vegan requests, time limits, beginner skill level and limited equipment

A script runs them all and checks: schema validity, allergen check passes, time within the limit, and that cuisine and ingredient IDs map to the vocabulary. It prints a pass/fail table along with **latency and token cost per prompt**. Run it before every deploy.

## 11. Build order and milestones

Principles: **reduce the biggest risk first** (the recipe agent's quality and latency), **deploy early and keep deploying** (so GCP issues show up one at a time), then build in **thin vertical slices** (UI + endpoint + data for one feature, then deploy).

Timeline assumes about 12 hours a week and is fluid.

### Step 0: Screen sketches and API contract (~2–3h), to 1 Dec. Models + stub routers drafted 21 Nov; awaiting review
Status: mockups are in `frontend-design/`, the contract is in `docs/api-contract.md`, the models are in `backend/app/models/` and the stub routers in `backend/app/routers/` (tests: `backend/tests/`).
Gets the benefit of designing frontend-first without building the frontend first.
- Wireframes: the mockups in `frontend-design/`, showing what data each screen shows and which actions it has (no separate `docs/wireframes.md`).
- The Pydantic models in `app/models/` plus stub routers in `app/routers/`: every endpoint's path and request/response shapes, browsable at `/docs`, with nothing implemented (each returns 501). Until a route is implemented it uses models by name only, so the models can still change. `docs/api-contract.md` holds the conventions and the screen → field mapping.
- Done when: every screen action maps to an endpoint and every displayed field maps to a model field.

### Step 1: Recipe agent spike (backend, local only), to 1 Dec
1. `infra/setup.sh`: project config, enable APIs (Vertex AI, Cloud Run, Cloud Build, Artifact Registry, Firestore, Secret Manager, Firebase), service account and IAM.
2. `app/vocab/` and `safety/allergens.py` **with tests written first**.
3. Research→writer pipeline running in `adk web`, plus a pytest.
4. Eval set and runner, passing.
5. **Write down the measured latency and cost per recipe.** These decide the progress UX in Slice 1.
- Done when: "quick vegetarian dinner for 2 under 30 minutes" with a peanut-allergy profile returns a valid `Recipe`, and the evals pass.

### Step 2: Walking skeleton, deployed, to 1 Dec
Deliberately tiny, but every connection in the stack runs in production.
- Backend: FastAPI with the auth dependency, `POST /chats` and `POST /chats/{id}/messages` (non-streaming JSON is fine here; SSE comes in Slice 1), on Cloud Run.
- Frontend: Next.js on Firebase App Hosting with Google sign-in, a text box, and the raw JSON response on screen.
- Done when: signing in on a phone and submitting a prompt returns a recipe from production. **From here on, every slice ends with a deploy.**

### Step 3: Vertical slices
| Slice | Content | Target |
|---|---|---|
| 1. Chat + recipe card | App shell and sidebar, `GET/POST /chats`, `GET /chats/{id}`, SSE progress chips, recipe card UI, recipe stored with generation metadata, `MOCK_LLM` mode, generated TS types | to 8 Dec |
| 2. Profile | Onboarding, `GET /me`, `PUT /profile`, `GET /vocab`, `build_profile_context()` feeding the agent, so the profile visibly changes the output | to 8 Dec |
| 3. Feedback & events | Event logger, impressions/views/saves, `POST /feedback` + save buttons with `user_state`, `features.rebuild()`, `recommend/` protocols with heuristic implementations | to 15 Dec |
| 4. Library | Saved page (`GET /recipes`), profile edit, tweaks as follow-up messages (chat history as context), clear session, data and privacy (export, clear history, delete profile) | to 15 Dec |
| 5. Pilot-ready | Rate limit + "Recipes left today", budget alert, structured logging, PWA manifest, error page, then **onboard pilot users (~13–15 Dec)** | to 15 Dec |

### Step 4: Pilot and freeze, to 22 Dec
Fix pilot feedback, improve latency, review costs. Code freeze.

**If time slips:** keep the pilot launch at around 15 Dec and cut onboarding polish first (use the single-page form fallback), then profile edit. Never cut the allergen checker, the evals or event logging. If the pilot can't happen before the break, move it to January rather than shipping something rushed.

## 12. Out of scope for MVP
Restaurant recommendations (deferred, see §7), the trained recommender model (designed for, not built), email-link sign-in, offline support / service worker caching, Cloud Trace, native app store builds, meal planning, shopping lists, social and sharing, image generation, nutrition calculation, payments, admin dashboards.

## 13. Working agreements for Claude Code
- Before writing code that touches ADK, Gemini grounding, Firebase App Hosting or Cloud Run deploy commands, **check the current official docs**. Model names, SDK syntax and product names (for example "Agent Engine" becoming "Agent Runtime") have changed recently. Use the latest stable Gemini Flash-tier model for generation unless quality requires Pro, and keep the model name in config.
- Prefer small, working, deployable increments over big scaffolds.
- Pydantic models are the source of truth. TS types are generated from the OpenAPI schema.
- Write tests for the allergen checker first, because it's the safety-critical piece.
- Agents read the profile only through `build_profile_context()`.
- Events are append-only. Derived features must always be rebuildable from events.
- Ask me before adding any new paid GCP service (including BigQuery) or third-party dependency outside this stack.

## 14. Current task
See **[docs/progress.md](docs/progress.md)** for what's done and what's next. (Step 0, the models and stub routers, has been drafted and is awaiting review.)
