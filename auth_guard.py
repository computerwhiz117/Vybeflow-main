"""
auth_guard.py  — Hard decorators for VybeFlow adult + auth enforcement.

verified_adult_required:
    Requires the user to be logged in AND 18+-verified (via a trusted
    provider, not a simple checkbox) AND not have adult access revoked.

    Returns JSON 401/403 on failure so API callers get clean errors.
"""

from functools import wraps
from flask import jsonify, session


def _get_current_user():
    """Retrieve the current user from the DB via session username.

    Imports are done lazily so this module can be imported early
    without triggering circular-import problems.
    """
    from models import User
    username = session.get("username")
    if not username:
        return None
    return User.query.filter_by(username=username).first()


def login_required_json(fn):
    """Like @login_required but returns JSON 401 instead of a redirect."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = _get_current_user()
        if not user:
            return jsonify({"ok": False, "error": "Login required"}), 401
        return fn(*args, _current_user=user, **kwargs)
    return wrapper


def verified_adult_required(fn):
    """Decorator: user must be authenticated AND 18+-verified."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = _get_current_user()
        if not user:
            return jsonify({"ok": False, "error": "Login required"}), 401
        if not getattr(user, "adult_verified", False):
            return jsonify({"ok": False, "error": "18+ verification required"}), 403
        if getattr(user, "adult_access_revoked", False):
            return jsonify({"ok": False, "error": "Adult access revoked"}), 403
        return fn(*args, _current_user=user, **kwargs)
    return wrapper
