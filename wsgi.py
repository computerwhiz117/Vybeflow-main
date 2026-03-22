"""WSGI entry point for the VybeFlow application."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vybeflow_minimal import app


socketio = None

if __name__ == "__main__":
    if socketio is not None:
        socketio.run(app, host="0.0.0.0", port=5000, debug=False)
    else:
        app.run(host="0.0.0.0", port=5000, debug=False)
