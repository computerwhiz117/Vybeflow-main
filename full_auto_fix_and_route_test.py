import os
import sys
import subprocess
import time
import requests
from pathlib import Path

# --- CONFIG ---
SERVER_PORT = 5000
CHECK_URL = f"http://127.0.0.1:{SERVER_PORT}"
ROUTES_FILE = os.path.join(os.path.dirname(__file__), 'all_routes.txt')
RETRY_DELAY = 5

# --- HELPERS ---
def kill_port(port):
    try:
        output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
        for line in output.splitlines():
            if 'LISTENING' in line or 'ESTABLISHED' in line:
                pid = int(line.strip().split()[-1])
                subprocess.run(f'taskkill /PID {pid} /F', shell=True)
    except Exception:
        pass

def force_fix():
    try:
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), '..', 'fix_static_url_for.py')], check=True)
    except Exception as e:
        print(f"[AUTO-FIX] Auto-fix failed: {e}")

def start_server():
    try:
        subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), 'VybeFlowapp.py')])
    except Exception as e:
        print(f"[AUTO-FIX] Failed to start server: {e}")

def get_routes():
    # Try to extract all routes from the Flask app
    try:
        result = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'scripts', 'verify_routes.py')], capture_output=True, text=True, timeout=20)
        routes = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith('/')]
        if routes:
            with open(ROUTES_FILE, 'w') as f:
                f.write('\n'.join(routes))
        return routes
    except Exception as e:
        print(f"[AUTO-FIX] Could not get routes: {e}")
        return []

def test_routes(routes):
    failed = []
    for route in routes:
        url = f"{CHECK_URL}{route}" if not route.startswith('http') else route
        try:
            r = requests.get(url, timeout=5)
            if r.status_code >= 400:
                print(f"[ROUTE TEST] {route} FAILED: {r.status_code}")
                failed.append(route)
            else:
                print(f"[ROUTE TEST] {route} OK: {r.status_code}")
        except Exception as e:
            print(f"[ROUTE TEST] {route} ERROR: {e}")
            failed.append(route)
    return failed

def main():
    print("[AUTO-FIX] Full auto-fix, restart, and route test tool running...")
    while True:
        kill_port(SERVER_PORT)
        force_fix()
        time.sleep(1)
        start_server()
        print("[AUTO-FIX] Waiting for server to start...")
        time.sleep(10)
        routes = get_routes()
        if not routes:
            print("[AUTO-FIX] No routes found. Check verify_routes.py script.")
            time.sleep(RETRY_DELAY)
            continue
        failed = test_routes(routes)
        if not failed:
            print("[AUTO-FIX] All routes OK! Server is up and healthy.")
            break
        else:
            print(f"[AUTO-FIX] {len(failed)} routes failed. Retrying full fix in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)

if __name__ == "__main__":
    main()
