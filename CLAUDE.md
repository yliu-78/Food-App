# Food App: Claude Code instructions

This file is loaded automatically at the start of every Claude Code session.

- **Spec:** @HANDOFF.md. Product, settled decisions, architecture and build order. Its "About me" section says how to work with me (I'm new to frontend and deployment, so explain from first principles).
- **State:** @docs/progress.md. What's done, the decisions made since the handoff, and the next steps. **Read it before starting work.**
- **API contract:** `docs/api-contract.md`. The Pydantic models in `backend/app/models/` are the source of truth.

## Session rules
- At the end of each piece of work, **update `docs/progress.md`**: add a dated log entry (newest first), refresh "Current status" and "Next steps", and add any new decisions to the Decisions table.
- If a decision changes the spec, update HANDOFF.md too, so the two never disagree.
- Run the backend tests with `cd backend; uv run pytest`.
