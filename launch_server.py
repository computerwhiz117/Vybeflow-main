"""Launcher for the main VybeFlow app.

This uses app.create_app(), which returns (app, socketio), and
runs the server with SocketIO so all real-time features work.
"""

from app import create_app


if __name__ == "__main__":
    app, socketio = create_app()
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)

