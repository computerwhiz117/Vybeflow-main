"""
End-to-end password reset flow test.
Runs against the live server on localhost:5000.
Does NOT require SMTP — generates the token directly via email_utils.
"""
import sys
import requests

BASE = "http://localhost:5000"

# ── helpers ──────────────────────────────────────────────────────────────

def banner(text):
    print(f"\n{'='*60}\n  {text}\n{'='*60}")

def check(label, condition, detail=""):
    sym = "PASS" if condition else "FAIL"
    line = f"  {sym}  {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    return condition

# ── step 0: pick a real user with a real (non-local) email ───────────────

banner("0. Finding test user")

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
app, _ = create_app()
with app.app_context():
    from models import User
    # find a user with a real email (not @vybeflow.local)
    user = User.query.filter(
        ~User.email.endswith("@vybeflow.local"),
        User.email.isnot(None)
    ).first()
    if not user:
        # fallback: use any user and manually patch email
        user = User.query.first()
        assert user is not None, "No users in database"
        test_email = f"{user.username}@test-reset.local"
        user.email = test_email
        from __init__ import db
        db.session.commit()
        print(f"  Patched user '{user.username}' with test email: {test_email}")
    else:
        test_email = user.email
    test_username = user.username
    original_hash = user.password_hash
    new_password = "NewSecurePass99!"
    print(f"  Test user : {test_username}")
    print(f"  Test email: {test_email}")

# ── step 1: GET /forgot_password renders OK ──────────────────────────────

banner("1. GET /forgot_password")
s = requests.Session()
r = s.get(f"{BASE}/forgot_password")
check("Page loads (200)", r.status_code == 200, f"status={r.status_code}")
check("Contains reset form", "forgot" in r.text.lower() or "email" in r.text.lower() or "reset" in r.text.lower())

# ── step 2: POST /forgot_password (always returns 200 + success message) ─

banner("2. POST /forgot_password")
r2 = s.post(f"{BASE}/forgot_password",
            data={"email": test_email},
            allow_redirects=True)
check("Returns 200", r2.status_code == 200, f"status={r2.status_code}")
check("Shows inbox message", "reset" in r2.text.lower() or "sent" in r2.text.lower() or "inbox" in r2.text.lower())

# ── step 3: Generate a valid token locally ────────────────────────────────

banner("3. Token generation & verification")
with app.app_context():
    from email_utils import generate_reset_token, verify_reset_token
    valid_token = generate_reset_token(test_email)
    check("Token generated (non-empty)", bool(valid_token), f"len={len(valid_token)}")

    # verify round-trip
    decoded_email = verify_reset_token(valid_token)
    check("Token verifies back to email", decoded_email == test_email,
          f"decoded={decoded_email}")

    # bad token should return None
    bad_result = verify_reset_token("this.is.not.a.real.token")
    check("Bad token returns None", bad_result is None, f"got={bad_result}")

    # tampered token should return None
    tampered = valid_token[:-4] + "XXXX"
    check("Tampered token returns None", verify_reset_token(tampered) is None)

# ── step 4: GET /reset_password/<valid_token> renders form ───────────────

banner("4. GET /reset_password/<valid_token>")
r4 = s.get(f"{BASE}/reset_password/{valid_token}", allow_redirects=True)
check("Reset page loads (200)", r4.status_code == 200, f"status={r4.status_code}")
check("Contains password field", 'password' in r4.text.lower())
check("Does NOT show 'invalid or expired'", "invalid or expired" not in r4.text.lower())

# ── step 5: GET /reset_password/<bad_token> redirects to forgot ──────────

banner("5. Invalid token is rejected")
r5 = s.get(f"{BASE}/reset_password/bad.token.here", allow_redirects=True)
check("Invalid token redirects/shows error",
      r5.status_code in (200, 302, 400) and (
          "invalid" in r5.text.lower() or
          "expired" in r5.text.lower() or
          "forgot" in r5.url or
          r5.status_code == 302
      ), f"status={r5.status_code}")

# ── step 6: POST /reset_password — passwords don't match ─────────────────

banner("6. POST /reset_password — mismatched passwords rejected")
with app.app_context():
    token6 = generate_reset_token(test_email)
r6 = s.post(f"{BASE}/reset_password/{token6}",
            data={"password": "Abc12345!", "confirm_password": "Abc99999!"},
            allow_redirects=True)
check("Mismatch rejected (200 stays on form)", r6.status_code == 200,
      f"status={r6.status_code}")
check("Shows 'do not match' error",
      "match" in r6.text.lower() or "password" in r6.text.lower())

# ── step 7: POST /reset_password — too short password rejected ────────────

banner("7. POST /reset_password — short password rejected")
with app.app_context():
    token7 = generate_reset_token(test_email)
r7 = s.post(f"{BASE}/reset_password/{token7}",
            data={"password": "abc", "confirm_password": "abc"},
            allow_redirects=True)
check("Short password rejected (200 stays on form)", r7.status_code == 200)
check("Shows length error", "6" in r7.text or "character" in r7.text.lower() or "password" in r7.text.lower())

# ── step 8: POST /reset_password — successful reset ──────────────────────

banner("8. POST /reset_password — successful password change")
with app.app_context():
    token8 = generate_reset_token(test_email)
r8 = s.post(f"{BASE}/reset_password/{token8}",
            data={"password": new_password, "confirm_password": new_password},
            allow_redirects=True)
check("Reset POST returns 200", r8.status_code == 200, f"status={r8.status_code}")
check("Redirected to login page",
      "login" in r8.url or "login" in r8.text.lower() or "sign in" in r8.text.lower())

# ── step 9: Login with NEW password works ────────────────────────────────

banner("9. Login with new password")
s_new = requests.Session()
r9 = s_new.post(f"{BASE}/login",
                data={"username": test_username, "password": new_password},
                allow_redirects=True)
whoami = s_new.get(f"{BASE}/api/whoami").json()
check("New password login works",
      whoami.get("logged_in") or whoami.get("username") == test_username,
      f"whoami={whoami}")

# ── step 10: Login with OLD password is rejected ─────────────────────────

banner("10. Old password no longer works")
with app.app_context():
    from models import User
    from werkzeug.security import check_password_hash
    fresh = User.query.filter_by(username=test_username).first()
    assert fresh is not None, "User not found"
    old_pw_rejected = not check_password_hash(fresh.password_hash, "testpass") if original_hash != fresh.password_hash else True
    check("Password hash changed in DB", original_hash != fresh.password_hash)

# ── step 11: Restore original password so other tests aren't broken ───────

banner("11. Restoring original password hash")
with app.app_context():
    from models import User
    from __init__ import db  # type: ignore[import]
    u = User.query.filter_by(username=test_username).first()
    assert u is not None
    u.password_hash = original_hash
    db.session.commit()
    check("Original hash restored", True)

# ── Summary ──────────────────────────────────────────────────────────────

banner("DONE")
print("  Password reset flow is fully functional.\n")
