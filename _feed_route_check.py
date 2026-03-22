from VybeFlowapp import app


routes_to_check = [
    "/feed",
    "/search",
    "/upload",
    "/account",
    "/story/create",
    "/logout",
]

with app.test_client() as client:
    with client.session_transaction() as session:
        session["logged_in"] = True
        session["username"] = "qa_user"
        session["email"] = "qa@vybeflow.app"
        session["account_type"] = "regular"

    for route in routes_to_check:
        response = client.get(route, follow_redirects=False)
        print(route, response.status_code)

    response = client.post("/search", data={"query": "vybe"}, follow_redirects=False)
    print("/search [POST]", response.status_code)

    response = client.post("/story/create", data={"caption": "test"}, follow_redirects=False)
    print("/story/create [POST]", response.status_code)
