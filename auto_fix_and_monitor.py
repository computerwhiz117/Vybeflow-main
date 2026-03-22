import subprocess
import time
import os
import sys
import socket
import requests

# --- CONFIG ---
SERVER_PORT = 5000
CHECK_URL = f"http://127.0.0.1:{SERVER_PORT}/"
RETRY_DELAY = 5  # seconds

# --- HELPERS ---
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def is_server_responding():
    try:
        r = requests.get(CHECK_URL, timeout=2)
        return r.status_code == 200
    except Exception:
        return False

def kill_port(port):
    # Windows only
    try:
        output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
        for line in output.splitlines():
            if 'LISTENING' in line or 'ESTABLISHED' in line:
                pid = int(line.strip().split()[-1])
                subprocess.run(f'taskkill /PID {pid} /F', shell=True)
    except Exception:
        pass

def force_fix():
    print("[AUTO-FIX] Running static URL and code auto-fix...")
    try:
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), '..', 'fix_static_url_for.py')], check=True)
        print("[AUTO-FIX] Auto-fix completed.")
    except Exception as e:
        print(f"[AUTO-FIX] Auto-fix failed: {e}")

def start_server():
    print("[AUTO-FIX] Attempting to start the server...")
    try:
        subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), 'VybeFlowapp.py')])
        print("[AUTO-FIX] Server start command issued.")
    except Exception as e:
        print(f"[AUTO-FIX] Failed to start server: {e}")

def main():
    print("[AUTO-FIX] VybeFlow server auto-fix and monitor running...")
    print(f"[AUTO-FIX] Server will be available at: http://{get_local_ip()}:{SERVER_PORT}")
    while True:
        if not is_server_responding():
            print("[AUTO-FIX] Server not responding. Forcing fix and restart...")
            kill_port(SERVER_PORT)
            force_fix()
            time.sleep(1)
            start_server()
            time.sleep(5)
        else:
            print(f"[AUTO-FIX] Server is up at http://{get_local_ip()}:{SERVER_PORT}")
        time.sleep(RETRY_DELAY)

if __name__ == "__main__":
    main()
