"""The FastAPI app. Run locally with `uv run fastapi dev app/main.py`, then open
http://127.0.0.1:8000/docs to browse and try every endpoint."""

from fastapi import FastAPI

from app.routers import chats, feedback, me, profile, recipes, vocab

app = FastAPI(title="Food App API")

# Each router module groups the endpoints for one resource. include_router adds
# them to the app, which is also what puts them in /openapi.json and /docs.
# TODO Step 2: CORS middleware (the frontend runs on another origin) and
# exception handlers that return ErrorResponse (see app/errors.py).
for module in (me, profile, vocab, chats, recipes, feedback):
    app.include_router(module.router)


@app.get("/healthz", tags=["ops"])
def healthz() -> dict[str, str]:
    """Cloud Run health check. The only route that needs no auth."""
    return {"status": "ok"}
