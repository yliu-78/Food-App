"""Step 0 checks on the stub app: every endpoint in docs/api-contract.md exists, and
the OpenAPI schema (the input to the frontend's generated TypeScript types) builds."""

from fastapi.testclient import TestClient

from app.main import app

# Every endpoint in the contract: (method, path). 17 in total.
CONTRACT = [
    ("get", "/healthz"),
    ("get", "/me"),
    ("put", "/profile"),
    ("get", "/profile/export"),
    ("delete", "/profile/activity"),
    ("delete", "/profile"),
    ("get", "/vocab"),
    ("post", "/chats"),
    ("get", "/chats"),
    ("get", "/chats/{chat_id}"),
    ("post", "/chats/{chat_id}/messages"),
    ("post", "/chats/{chat_id}/clear"),
    ("get", "/recipes"),
    ("get", "/recipes/{recipe_id}"),
    ("put", "/recipes/{recipe_id}/save"),
    ("delete", "/recipes/{recipe_id}/save"),
    ("post", "/feedback"),
]


def test_openapi_has_every_contract_endpoint():
    """If FastAPI can build the OpenAPI schema, openapi-typescript can generate the
    frontend types from it later."""
    spec = app.openapi()
    for method, path in CONTRACT:
        assert method in spec["paths"].get(path, {}), f"missing {method.upper()} {path}"
    n_routes = sum(len(ops) for ops in spec["paths"].values())
    assert n_routes == len(CONTRACT), "an endpoint exists that isn't in the contract"

    schemas = spec["components"]["schemas"]
    for name in ["MeResponse", "StoredRecipe", "ChatDetail", "SendMessageRequest", "RecipeSummary",
                 "StatusEvent", "MessageEvent", "DoneEvent", "ErrorEvent", "ErrorResponse"]:
        assert name in schemas


def test_send_message_documents_the_event_stream():
    """The SSE endpoint's StreamEvent union must reach OpenAPI, or the frontend
    won't get a type for the events it parses."""
    op = app.openapi()["paths"]["/chats/{chat_id}/messages"]["post"]
    stream = op["responses"]["200"]["content"]["text/event-stream"]
    data_schema = stream["itemSchema"]["properties"]["data"]["contentSchema"]
    assert data_schema["discriminator"]["propertyName"] == "type"


client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_stub_returns_501():
    assert client.get("/me").status_code == 501


def test_stub_stream_returns_501():
    """No body sent: the stub dependency runs before body validation, so this
    test doesn't depend on SendMessageRequest's fields."""
    assert client.post("/chats/c1/messages").status_code == 501
