# Progress log

The running record of work on this project, so any new Claude Code session (or I) can pick up where the last one left off. HANDOFF.md is the **spec**; this file is the **state**.

**How to use it (for Claude):** read "Current status" and "Next steps" before starting work. At the end of each piece of work, add a dated entry at the top of the Log (newest first), update "Current status" and "Next steps", and add any decision to the Decisions table. Keep entries short: what changed, where, and anything surprising.

---

## Current status
- **Phase:** Step 0 (screens + API contract). Models and stub routers written and commented; **under the user's review**, with a code review planned before the first push.
- **Done:** mockups (`frontend-design/`), Pydantic models (`backend/app/models/`), stub routers for all 17 endpoints (`backend/app/routers/`, `app/main.py`, `app/auth.py`, `app/errors.py`), API contract (`docs/api-contract.md`), tests passing (12/12: 7 model + 5 API).
- **Not committed:** everything beyond the initial commit is untracked. There's no `.gitignore` yet, so `__pycache__/` and `.pytest_cache/` would be committed (and `.venv/` after `uv sync`).
- **Not started:** Step 1 (recipe agent spike), infra, frontend code.

## Next steps

### ▶ NEXT TASK: code review, then first push
1. Add a `.gitignore` (Python now, Node later) before the first commit. Offered; waiting for the user's yes.
2. The user runs a code reviewer over `backend/`, then commits and pushes. Fix anything it finds.
3. The user has questions about the routers. Walk them through **using chat.py/chats.py as the worked example** (the top of `chats.py` has a "how to read a route" guide). They learn best from annotated JSON, request flows, and "which button calls this". Teaching points: why `send_message` uses a `not_implemented` dependency instead of raising 501 in its body (see Log), and how the `CurrentUser` dependency works.

### After that
1. The user finishes reviewing the models and routers and answers the open questions at the bottom of `docs/api-contract.md`.
2. The user installs `uv`, then runs `cd backend; uv sync; uv run pytest` (pin Python 3.12 or 3.13).
3. The user removes the email/password parts from mockup 1 (Google sign-in only).
4. Step 1 (HANDOFF §11): `infra/setup.sh`, `app/vocab/` + `safety/allergens.py` with tests first, the research→writer ADK pipeline. **Check the current ADK and Gemini docs first.**

## Teaching notes (where the user's understanding is)
The user is a backend AI engineer learning fullstack (see HANDOFF "About me"). As of 2026-11-21 they understand:
- The frontend and backend are two programs talking HTTP + JSON. The contract and Pydantic models define the shapes; FastAPI → `/openapi.json` → `openapi-typescript` → TS types.
- Why `models/` is a separate package: it's imported by routers, agents, db and safety alike.
- **Four roles of model classes:** request body (`FeedbackRequest`), response body (`RecipeUserState`, `ChatDetail`), stored-only document (`Event`, sent over the API only inside `DataExport`), and nested building block (`TextContent`, `Ingredient`). A class is "top-level" if it appears in a router signature (`body:` or `->`).
- Request models act as whitelists: `ProfileUpdate` vs `UserProfile`, so the client can't set server-owned fields.
- The full chat round trip: `GET /chats` → `POST /chats` → `POST /chats/{id}/messages` streaming status/message/done → `GET /chats/{id}` returning the history.

**Pending quiz (the user asked to come back to it):** using `chat.py`:
1. When the user hits send, which class is the request body? (`SendMessageRequest`)
2. Which class is stored for each message? (`ChatMessage`)
3. Why does `SendMessageRequest` have no `role` field when `ChatMessage` does? (The server sets `role="user"` itself, since the client can't post as the assistant. This is the whitelist idea again.)

## Decisions
| Date | Decision | Why |
|---|---|---|
| 2026-11-21 | Google sign-in only (the mockup's email/password is out of scope) | Less to build; matches HANDOFF |
| 2026-11-21 | **Chat sessions** replace "single prompt + regenerate"; a tweak is the next message | The user's choice, from the user flow + mockups |
| 2026-11-21 | Restaurants deferred, but extensible via `mode`, a `kind` union and `ItemType` | MVP scope; mockups show "SOON" |
| 2026-11-21 | Data and privacy: export, clear activity history, delete profile | GDPR, real UK pilot users; in the mockups |
| 2026-11-21 | "Clear session" empties a chat (messages + unsaved recipes); it doesn't delete the chat | Matches the mockup confirm dialog |
| 2026-11-21 | Saved-page search and filters run client-side | No full-text search in Firestore; small data |
| 2026-11-21 | Wireframes = the `frontend-design/` mockups (no `docs/wireframes.md`) | Already done in another format |
| 2026-11-21 | Write stub routers in Step 0; models stay open to change until the routers are done | Endpoint needs shape the models; seeing both side by side helps the user learn |
| 2026-11-21 | SSE via FastAPI's native `fastapi.sse.EventSourceResponse` (FastAPI ≥ 0.135), not hand-rolled `StreamingResponse` | Built in; the `StreamEvent` union appears in OpenAPI with no workarounds |
| 2026-11-21 | `POST /chats/{id}/messages`: 404/429 are checked in dependencies **before** the stream opens; failures during generation are an in-stream `ErrorEvent` | Once a stream starts, the 200 status can't be changed |
| 2026-11-21 | Until a route is implemented, it references models **by name only** (in its signature), never by field | The models are still changing; field changes then need no router edits |

## Log

### 2026-11-21 (evening): stub routers
- Added `app/main.py`, `app/auth.py` (`CurrentUser` = `Annotated[str, Depends(current_user)]`, returns `"dev-user"`), `app/errors.py` (`errors(401, 404)` builds the `responses=` dict) and `app/routers/{me,profile,vocab,chats,recipes,feedback}.py`. Paths use `{chat_id}` / `{recipe_id}`.
- **Surprise:** raising `HTTPException(501)` inside an SSE generator returns **200 with an empty body**, because the status line goes out before the generator runs. So real 404/429 checks must go in dependencies.
- The `send_message` stub first yielded an `ErrorEvent`, which tied it to that model's fields. At the user's request it now uses a `not_implemented` dependency (`app/errors.py`), so it returns a real 501. **Rule: routers reference models by name only (in signatures) until implemented, so models can change freely.** Verified: adding a required field, renaming `Chat.recipe_count` and renaming `ErrorEvent.message` all leave the router code and `test_api.py` passing.
- Model change: new `DataExport` (`app/models/export.py`) for `GET /profile/export`. It's the one place `Event` is sent over the API.
- Deps: `fastapi[standard]>=0.135` (SSE + the `fastapi dev` CLI), `httpx` (dev, for `TestClient`). Latest FastAPI is 0.165.0.
- Tests: split into `test_models.py` and a new `test_api.py` (every contract path exists, nothing extra, SSE schema in OpenAPI, `/healthz` 200, stubs return 501). Run in a temporary pip venv, since `uv` still isn't installed.
- `docs/api-contract.md`: replaced the endpoint table with a pointer to `app/routers/` and `/docs`; added the two kinds of streaming errors.
- Commented every backend file for the pre-push code review: module docstrings on each router, a "how to read a route" guide at the top of `chats.py`, and notes on `prefix`, 204, query params and `Query`.
- TODO Step 2 (also in `main.py`): CORS, and exception handlers so errors return `ErrorResponse` instead of FastAPI's default `{"detail": ...}`.

### 2026-11-21 (later): model walkthrough, stub routers agreed
- Taught the user how `models/` relates to endpoints (see Teaching notes). The user's key insight: models and endpoints should be designed together, which led to the decision to write stub routers next.
- Updated HANDOFF §4, §6, §8, §11 and §14 so the later steps match chat sessions (routers `me/vocab/chats`, frontend routes `/chats/[id]` and `/saved`, Slices 1–5 re-cut by endpoint).
- `CLAUDE.md` @-imports HANDOFF.md + this file, about 6–7k tokens per session. The user cares about context use; if it becomes a problem, import only this file.

### 2026-11-21: Step 0 drafted
- Checked Step 0: nothing existed except the mockups. Explained Pydantic → OpenAPI → TypeScript to the user (new to frontend).
- Added an "About me" section to HANDOFF.md: the user is a backend AI engineer learning fullstack + deployment. **Explain frontend and deploy concepts from first principles.**
- Read all 9 mockup PNGs and derived extra fields: `display_name`, `other_allergens`, `AllergenCheck`, `RecipeUserState`, `suggested_tweaks`, `latency_ms`, `search_entry_point_html`, `GET /me` (usage + saved count), `GET /vocab`.
- Created `backend/pyproject.toml`, `app/vocab/ids.py`, `app/models/{common,profile,recipe,chat,event}.py`, `tests/test_models.py`, `docs/api-contract.md`.
- Updated HANDOFF.md §4, §5, §6, §8, §11 and §14 for chat sessions and the new endpoints; created `CLAUDE.md` + this file.
- Note: `uv` isn't installed locally, so the tests ran in a temporary pip venv. The local Python is 3.15.

### Note for adding to progress.md file
- Ensure this file remains streamlined: do not add anything that is not required and contistently prune unneeded information from here
- Add to this file after every major update or decision and/or when requested


