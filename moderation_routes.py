from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy import func

from models_moderation import db, ModerationEvent, get_or_create_restriction
from moderation_engine import moderate_text

mod_bp = Blueprint("mod_bp", __name__)

# You need tables for Post/Comment in your app. Replace these imports with yours.
# from your_models import Post, Comment

def _now():
    return datetime.utcnow()

def _add_event(user_id: int, content_type: str, content_id: int | None, action: str, reason: str, score=None):
    ev = ModerationEvent(
        user_id=user_id, content_type=content_type, content_id=content_id,
        action=action, reason=reason, score=score
    )
    db.session.add(ev)
    db.session.commit()

def _reset_strikes_if_needed(r):
    now = _now()
    if r.strikes_reset_at and now >= r.strikes_reset_at:
        r.strikes_24h = 0
        r.strikes_reset_at = now + timedelta(hours=24)

def _apply_strike_and_cooldown(user_id: int, kind: str, seconds: int):
    r = get_or_create_restriction(user_id)
    _reset_strikes_if_needed(r)
    r.strikes_24h += 1

    until = _now() + timedelta(seconds=seconds)
    if kind == "post":
        r.can_post_after = max(r.can_post_after or _now(), until)
    else:
        r.can_comment_after = max(r.can_comment_after or _now(), until)

    # escalating penalties (automatic)
    if r.strikes_24h >= 3:
        # short lock
        r.can_comment_after = max(r.can_comment_after or _now(), _now() + timedelta(minutes=30))
    if r.strikes_24h >= 6:
        r.can_post_after = max(r.can_post_after or _now(), _now() + timedelta(hours=6))

    db.session.commit()

def _user_rate_limited(user_id: int, content_type: str) -> bool:
    # per user per minute
    one_min_ago = _now() - timedelta(minutes=1)
    cnt = (db.session.query(func.count(ModerationEvent.id))
           .filter(ModerationEvent.user_id == user_id,
                   ModerationEvent.content_type == content_type,
                   ModerationEvent.created_at >= one_min_ago)
           .scalar())
    return cnt >= 15

def _reply_storm(target_key: str) -> bool:
    # target_key can be "post:123" or "user:45" etc. store it in reason field or content_id mapping
    # We'll use reason tag format: "dogpile_target=<target_key>"
    one_min_ago = _now() - timedelta(seconds=60)
    cnt = (db.session.query(func.count(ModerationEvent.id))
           .filter(ModerationEvent.reason == f"dogpile_target={target_key}",
                   ModerationEvent.created_at >= one_min_ago)
           .scalar())
    return cnt >= 8

@mod_bp.post("/api/moderate/comment")
def moderate_comment_api():
    # Replace with your auth
    payload = request.get_json(silent=True) or {}
    user_id = int(payload.get("user_id") or 0)  # replace with current_user.id
    text = (payload.get("text") or "")[:5000]
    target_post_id = payload.get("post_id")
    target_user_id = payload.get("target_user_id")  # optional: who they reply to

    if not user_id:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    r = get_or_create_restriction(user_id)
    if r.is_blocked("comment"):
        return jsonify({"ok": False, "error": "cooldown_active"}), 429

    if _user_rate_limited(user_id, "comment"):
        _add_event(user_id, "comment", None, "throttle", "rate_limit_user")
        _apply_strike_and_cooldown(user_id, "comment", 60)
        return jsonify({"ok": False, "error": "slow_down"}), 429

    # Dogpile throttle: too many replies to same target in short time
    if target_post_id and _reply_storm(f"post:{target_post_id}"):
        _add_event(user_id, "comment", None, "throttle", f"dogpile_target=post:{target_post_id}")
        _apply_strike_and_cooldown(user_id, "comment", 120)
        return jsonify({"ok": False, "error": "thread_is_hot_try_later"}), 429

    if target_user_id and _reply_storm(f"user:{target_user_id}"):
        _add_event(user_id, "comment", None, "throttle", f"dogpile_target=user:{target_user_id}")
        _apply_strike_and_cooldown(user_id, "comment", 180)
        return jsonify({"ok": False, "error": "user_is_being_piled_on_try_later"}), 429

    mod = moderate_text(text)

    if mod.decision == "allow":
        _add_event(user_id, "comment", None, "allow", "ok", score=mod.score)
        return jsonify({"ok": True, "action": "allow"}), 200

    if mod.decision == "quarantine":
        _add_event(user_id, "comment", None, "quarantine", mod.reason, score=mod.score)
        # quarantine: save but only show to author + moderators
        return jsonify({"ok": True, "action": "quarantine", "reason": mod.reason}), 200

    # block or throttle
    _add_event(user_id, "comment", None, "block", mod.reason, score=mod.score)
    _apply_strike_and_cooldown(user_id, "comment", 300)
    return jsonify({"ok": False, "error": "blocked", "reason": mod.reason}), 403
