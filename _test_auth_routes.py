import requests

BASE = "http://localhost:5000"

def run():
    s = requests.Session()
    # Login as regular user
    r = s.post(BASE + "/login", data={"username": "testuser", "password": "Test1234!"}, allow_redirects=True)
    whoami = s.get(BASE + "/api/whoami").json()
    print(f"Logged in as: {whoami.get('username', 'UNKNOWN')} (logged_in={whoami.get('logged_in')})")

    protected_user = [
        "/api/friends/list",
        "/api/trust/score",
    ]
    print("\n-- User-auth-required routes --")
    for p in protected_user:
        r = s.get(BASE + p, allow_redirects=True, timeout=5)
        print(f"  {r.status_code:3d}  GET  {p}")

    # Login as admin
    s2 = requests.Session()
    s2.post(BASE + "/login", data={"username": "admin", "password": "AdminPass123!"}, allow_redirects=True)
    whoami2 = s2.get(BASE + "/api/whoami").json()
    print(f"\nLogged in as: {whoami2.get('username', 'UNKNOWN')} (is_admin={whoami2.get('is_admin')})")

    admin_routes = [
        "/admin/moderation",
    ]
    print("\n-- Admin-auth-required routes --")
    for p in admin_routes:
        r = s2.get(BASE + p, allow_redirects=True, timeout=5)
        print(f"  {r.status_code:3d}  GET  {p}")

if __name__ == "__main__":
    run()
