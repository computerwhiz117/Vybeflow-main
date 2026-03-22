import subprocess
import time
import os
import sys

# --- FORCE FIX LOGIC ---
def force_fix():
    print("[TOOL] Running static URL and code auto-fix...")
    try:
        result = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), '..', 'fix_static_url_for.py')], check=True, capture_output=True, text=True)
        print(result.stdout)
        print("[TOOL] Auto-fix completed.")
    except subprocess.CalledProcessError as e:
        print("[TOOL] Auto-fix failed:", e.stderr)
        return False
    return True

# --- SERVER START LOGIC ---
SERVER_COMMAND = [sys.executable, os.path.join(os.path.dirname(__file__), 'VybeFlowapp.py')]

RETRY_DELAY = 5  # seconds


def is_server_running():
    # TODO: Implement a real check (e.g., HTTP request to localhost:5000)
    return False  # Always force restart for now


def start_server():
    print("[TOOL] Attempting to start the server...")
    try:
        subprocess.Popen(SERVER_COMMAND)
        print("[TOOL] Server start command issued.")
    except Exception as e:
        print(f"[TOOL] Failed to start server: {e}")


def main():
    print("[TOOL] FORCE FIX + SERVER START")
    if force_fix():
        time.sleep(1)
        start_server()
    else:
        print("[TOOL] Fix failed. Server not started.")

if __name__ == "__main__":
    main()
