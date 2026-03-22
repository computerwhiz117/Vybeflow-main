from app import create_app

app, socketio = create_app()
app.testing = True

if __name__ == "main" or __name__ == "__main__":
    from werkzeug.exceptions import HTTPException
    import traceback

    with app.test_client() as client:
        try:
            resp = client.get("/create_story")
            print("Status:", resp.status_code)
            print("Body snippet:\n", resp.get_data(as_text=True)[:600])
        except HTTPException as he:
            print("HTTPException:", he)
            traceback.print_exc()
        except Exception as e:
            print("Exception while requesting /create_story:", e)
            traceback.print_exc()
