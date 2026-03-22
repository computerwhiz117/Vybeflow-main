import requests
s = requests.Session()
r = s.post("http://localhost:5000/login", data={"username": "admin", "password": "AdminPass123!"}, allow_redirects=True)
print("Login status:", r.status_code)
r2 = s.get("http://localhost:5000/admin/moderation", allow_redirects=True, timeout=5)
print("Admin route:", r2.status_code)
