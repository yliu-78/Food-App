"""Who is calling? Every route except /healthz depends on `current_user`.

FastAPI runs a dependency before the route body. If the dependency raises (e.g. a
401), the route never runs, so no route has to remember to check auth itself.
"""

from typing import Annotated

from fastapi import Depends


def current_user() -> str:
    """Return the caller's Firebase uid.

    TODO Step 2: verify Firebase ID token. Read `Authorization: Bearer <token>`,
    verify it with firebase_admin.auth.verify_id_token, return its `uid`, and raise
    a 401 `unauthenticated` if it's missing or invalid.
    """
    return "dev-user"


# Use it as a parameter type: `def get_me(uid: CurrentUser) -> MeResponse`.
CurrentUser = Annotated[str, Depends(current_user)]
