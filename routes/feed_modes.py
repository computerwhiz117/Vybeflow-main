"""
Feed Modes — Blueprint
=======================
No Algorithm Mode toggle: Trending, Friends Only, Chronological.
"""

from flask import (
    Blueprint, request, session, redirect, url_for, jsonify,
)
from __init__ import db

feed_modes_bp = Blueprint("feed_modes", __name__, url_prefix="/feed-modes")


def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None
    return uid


# ---------------------------------------------------------------------------
# Set feed mode (AJAX endpoint)
# ---------------------------------------------------------------------------
@feed_modes_bp.route("/set", methods=["POST"])
def set_feed_mode():
    uid = _require_login()
    if uid is None:
        return jsonify({"error": "Login required"}), 401

    from models import User

    mode = request.form.get("mode") or request.json.get("mode", "trending") if request.is_json else request.form.get("mode", "trending")
    mode = mode.strip().lower()

    valid_modes = ("trending", "friends", "chronological")
    if mode not in valid_modes:
        return jsonify({"error": f"Invalid mode. Choose from: {', '.join(valid_modes)}"}), 400

    user = User.query.get(uid)
    if user:
        user.feed_mode = mode
        db.session.commit()

    session["feed_mode"] = mode
    return jsonify({"status": "ok", "mode": mode})


# ---------------------------------------------------------------------------
# Get current feed mode
# ---------------------------------------------------------------------------
@feed_modes_bp.get("/current")
def get_feed_mode():
    uid = _require_login()
    if uid is None:
        return jsonify({"mode": "trending"})

    from models import User

    user = User.query.get(uid)
    mode = getattr(user, "feed_mode", "trending") if user else "trending"
    return jsonify({"mode": mode})
