from VybeFlowapp import app

routes = ["/feed", "/account", "/search", "/upload", "/story/create"]

with app.test_client() as client:
    with client.session_transaction() as session:
        session["logged_in"] = True
        session["username"] = "qa_user"
        session["email"] = "qa@vybeflow.app"
        session["account_type"] = "regular"

    for route in routes:
        response = client.get(route)
        print(route, response.status_code)
