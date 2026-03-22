"""Simple VybeFlow server launcher.

This wraps the main Flask/SocketIO app so that existing
scripts like START_SERVER.bat (which call simple_server.py)
continue to work.

It now delegates to app.create_app(), which returns (app, socketio).
"""

from app import create_app


if __name__ == "__main__":
	app, socketio = create_app()

	# Start the background AI feed monitor (scans every 30s)
	from feed_monitor import start_feed_monitor
	start_feed_monitor(app)

	# Run the main app with SocketIO support
	socketio.run(app, host="127.0.0.1", port=5000, debug=True)

