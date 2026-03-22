from VybeFlowapp import app

routes = [
    "/feed",
    "/search",
    "/search?query=studio",
    "/upload",
    "/account",
    "/settings",
    "/story/create",
]

with app.test_client() as client:
    with client.session_transaction() as session:
        session["logged_in"] = True
        session["username"] = "qa_user"
        session["email"] = "qa@vybeflow.app"
        session["account_type"] = "regular"

    for route in routes:
        response = client.get(route, follow_redirects=False)
        print(route, response.status_code)

    print("/search [POST]", client.post("/search", data={"query": "dance"}).status_code)
    print("/settings [POST]", client.post(
        "/settings",
        data={"ai_assist": "on", "safe_mode": "on", "default_visibility": "public"},
        follow_redirects=False,
    ).status_code)
