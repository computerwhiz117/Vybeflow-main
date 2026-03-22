"""
Comprehensive test for all new VybeFlow features:
  1. Ghost Mode API
  2. Shield Mode API
  3. Device Fingerprint Registration
  4. Appeal system (block + ban) — sends REAL admin emails with Approve/Deny links
  5. Appeal decide endpoint (token approve/deny)
"""

import os, sys, json

# ── Ensure we run from the right directory ──
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

from werkzeug.security import generate_password_hash
from app import create_app
from __init__ import db
from models import User

app, socketio = create_app()
PASS = 0
FAIL = 0
TESTS = []

def result(name, ok, detail=""):  # type: (str, bool, object) -> None
    global PASS, FAIL
    tag = "✅ PASS" if ok else "❌ FAIL"
    TESTS.append((name, ok, str(detail)))
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  {tag}  {name}" + (f"  ({detail})" if detail else ""))


def run():
    global PASS, FAIL
    with app.test_client() as c:
        with app.app_context():
            # ── Setup: ensure test user exists ──
            db.create_all()

            # Rollback any leftover failed transaction
            db.session.rollback()

            u = User.query.filter_by(username="test_appeal_user").first()
            if not u:
                # Check email not taken
                existing = User.query.filter_by(email="testappealuser@test.com").first()
                if existing:
                    u = existing
                    u.username = "test_appeal_user"
                else:
                    u = User(username="test_appeal_user", email="testappealuser@test.com",  # type: ignore[call-arg]
                             password_hash=generate_password_hash("Test1234!", method='pbkdf2:sha256:260000'))  # type: ignore[call-arg]
                    db.session.add(u)
            assert u is not None
            u.password_hash = generate_password_hash("Test1234!", method='pbkdf2:sha256:260000')  # type: ignore[assignment]
            u.is_banned = False  # type: ignore[assignment]
            u.is_suspended = False  # type: ignore[assignment]
            u.appeal_pending = False  # type: ignore[assignment]
            db.session.commit()

            admin = User.query.filter_by(username="admin_tester").first()
            if not admin:
                existing = User.query.filter_by(email="chatcirclebusiness16@gmail.com").first()
                if existing:
                    admin = existing
                else:
                    admin = User(username="admin_tester", email="chatcirclebusiness16@gmail.com", is_admin=True,  # type: ignore[call-arg]
                                 password_hash=generate_password_hash("Admin1234!", method='pbkdf2:sha256:260000'))  # type: ignore[call-arg]
                    db.session.add(admin)
            assert admin is not None
            admin.is_admin = True  # type: ignore[assignment]
            db.session.commit()

            ADMIN_USERNAME = admin.username

            # Login helper
            def login(username, password):
                return c.post("/login", data={"username": username, "password": password}, follow_redirects=True)

            def logout():
                return c.get("/logout", follow_redirects=True)

            # ===== 1. GHOST MODE =====
            print("\n═══════ 1. GHOST MODE ═══════")
            login("test_appeal_user", "Test1234!")

            r = c.post("/api/ghost/activate", json={"username": ADMIN_USERNAME, "scope": "person"})
            result("Ghost Activate", r.status_code in (200, 201) and r.get_json().get("ok"), r.get_json())

            r = c.get(f"/api/ghost/status/{ADMIN_USERNAME}")
            result("Ghost Status", r.status_code == 200 and r.get_json().get("ghost_active"), r.get_json())

            r = c.get("/api/ghost/list")
            result("Ghost List", r.status_code == 200 and isinstance(r.get_json().get("ghosted_users"), list), r.get_json())

            r = c.post("/api/ghost/deactivate", json={"username": ADMIN_USERNAME})
            result("Ghost Deactivate", r.status_code == 200, r.get_json())

            # ===== 2. SHIELD MODE =====
            print("\n═══════ 2. SHIELD MODE ═══════")

            r = c.post("/api/shield/toggle", json={"activate": True})
            result("Shield Enable", r.status_code == 200 and r.get_json().get("shield_active"), r.get_json())

            r = c.get("/api/shield/status")
            data = r.get_json()
            result("Shield Status (on)", r.status_code == 200 and data.get("shield_active") == True, data)

            r = c.post("/api/shield/toggle", json={"activate": False})
            result("Shield Disable", r.status_code == 200 and not r.get_json().get("shield_active"), r.get_json())

            # ===== 3. DEVICE FINGERPRINT =====
            print("\n═══════ 3. DEVICE FINGERPRINT ═══════")

            r = c.post("/api/device/register", json={
                "fingerprint_hash": "test_fp_abc123",
                "canvas_hash": "canvas_xyz",
                "screen_res": "1920x1080",
                "timezone": "America/New_York",
                "platform": "Win32",
            })
            result("Device Register", r.status_code == 200, r.get_json())

            # ===== 4. SAFETY VISIBILITY CHECK =====
            print("\n═══════ 4. SAFETY VISIBILITY ═══════")

            r = c.post("/api/safety/check-visibility", json={"username": ADMIN_USERNAME})
            result("Visibility Check", r.status_code == 200 and "visible" in r.get_json(), r.get_json())

            # ===== 5. APPEAL SYSTEM (sends REAL emails) =====
            print("\n═══════ 5. APPEAL SYSTEM ═══════")
            logout()

            # 6a. Block appeal (anonymous)
            r = c.post("/api/appeal", json={
                "username": "test_appeal_user",
                "reason": "This is an automated test appeal. I was blocked unfairly and would like to be reviewed."
            })
            data = r.get_json()
            result("Block Appeal Submit", r.status_code == 200 and data.get("ok"), data)
            print("    → [REAL EMAIL SENT to admin(s) for block appeal]")

            # 6b. Ban appeal (requires login as banned user)
            login("test_appeal_user", "Test1234!")
            u = User.query.filter_by(username="test_appeal_user").first()
            assert u is not None
            u.is_banned = True  # type: ignore[assignment]
            u.is_suspended = True  # type: ignore[assignment]
            u.negativity_warnings = 3  # type: ignore[assignment]
            u.appeal_pending = False  # type: ignore[assignment]
            u.suspension_reason = "Automated test ban"  # type: ignore[assignment]
            db.session.commit()

            r = c.post("/api/appeal/strike", json={
                "reason": "This is an automated test ban appeal. I believe I was banned incorrectly and want to be reviewed."
            })
            data = r.get_json()
            result("Ban Appeal Submit", r.status_code == 200 and data.get("ok"), data)
            print("    → [REAL EMAIL SENT to admin(s) for ban appeal with ✅ Approve / ❌ Deny buttons]")

            # 6c. Duplicate appeal should be rejected
            r = c.post("/api/appeal/strike", json={
                "reason": "Trying again right away"
            })
            data = r.get_json()
            result("Duplicate Appeal Rejected", r.status_code == 400 and "pending" in data.get("error", "").lower(), data)

            # ===== 6. APPEAL DECIDE TOKEN =====
            print("\n═══════ 6. APPEAL DECIDE (Token) ═══════")
            from email_utils import generate_appeal_token

            # Test approve
            token = generate_appeal_token("test_appeal_user", "approve")
            r = c.get(f"/api/appeal/decide/{token}")
            result("Appeal Approve via Token", r.status_code == 200 and b"UNBANNED" in r.data, r.status_code)

            # Verify user was actually unbanned
            u = User.query.filter_by(username="test_appeal_user").first()
            assert u is not None
            result("User Unbanned in DB", u.is_banned == False and u.is_suspended == False and u.appeal_pending == False,
                   f"banned={u.is_banned}, suspended={u.is_suspended}, appeal_pending={u.appeal_pending}")

            # Ban again and test deny
            u.is_banned = True  # type: ignore[assignment]
            u.is_suspended = True  # type: ignore[assignment]
            u.appeal_pending = True  # type: ignore[assignment]
            db.session.commit()

            token = generate_appeal_token("test_appeal_user", "deny")
            r = c.get(f"/api/appeal/decide/{token}")
            result("Appeal Deny via Token", r.status_code == 200 and b"DENIED" in r.data, r.status_code)

            u = User.query.filter_by(username="test_appeal_user").first()
            assert u is not None
            result("User Still Banned After Deny", u.is_banned == True and u.appeal_pending == False,
                   f"banned={u.is_banned}, appeal_pending={u.appeal_pending}")

            # Test expired/bad token
            r = c.get("/api/appeal/decide/this-is-a-bad-token")
            result("Bad Token Rejected", r.status_code == 400, r.status_code)

            # ===== 7. SUSPENSION STATUS =====
            print("\n═══════ 7. SUSPENSION STATUS ═══════")
            r = c.get("/api/suspension/status")
            data = r.get_json()
            result("Suspension Status", r.status_code == 200 and "suspended" in data, data)

            # ── Cleanup: unban test user ──
            u = User.query.filter_by(username="test_appeal_user").first()
            assert u is not None
            u.is_banned = False  # type: ignore[assignment]
            u.is_suspended = False  # type: ignore[assignment]
            u.appeal_pending = False  # type: ignore[assignment]
            u.negativity_warnings = 0  # type: ignore[assignment]
            db.session.commit()

    # ── Summary ──
    print("\n" + "═" * 60)
    print(f"  RESULTS:  {PASS} passed  /  {FAIL} failed  /  {PASS + FAIL} total")
    print("═" * 60)
    if FAIL:
        print("\n  FAILURES:")
        for name, ok, detail in TESTS:
            if not ok:
                print(f"    ❌ {name}: {detail}")
    print()
    return FAIL == 0

if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
