import subprocess
import time
import os

# Bot to force the server to start
# You can adjust the server start command as needed

SERVER_COMMAND = ["python", "Vybeflow-main/VybeFlowapp.py"]  # Corrected path to main server file

# Try absolute path as fallback
if not os.path.exists(SERVER_COMMAND[1]):
    SERVER_COMMAND[1] = os.path.join(os.path.dirname(__file__), "VybeFlowapp.py")
RETRY_DELAY = 5  # seconds


def is_server_running():
    # Simple check: look for a process or try to connect to the port
    # Here, we just check if the process is running (basic example)
    # You can improve this to check a port or HTTP endpoint
    return False  # Always force restart for demo


def start_server():
    print("[BOT] Attempting to start the server...")
    try:
        subprocess.Popen(SERVER_COMMAND)
        print("[BOT] Server start command issued.")
    except Exception as e:
        print(f"[BOT] Failed to start server: {e}")


def bot_loop():
    while True:
        if not is_server_running():
            start_server()
        else:
            print("[BOT] Server already running.")
        time.sleep(RETRY_DELAY)


if __name__ == "__main__":
    print("[BOT] Server start bot running...")
    bot_loop()
