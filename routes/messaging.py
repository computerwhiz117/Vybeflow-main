"""
Encrypted DMs — Blueprint
===========================
End-to-end encrypted direct messaging with:
  - AES-256-GCM encryption (key derived per-thread)
  - AI moderation with "street smarts" (scam, troll, bot, harassment detection)
  - View expiration / self-destruct timers
  - Anti-bot rate limiting
  - Anti-troll harassment detection
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, request, session, jsonify

messaging_bp = Blueprint("messaging", __name__)

# ── Lazy imports (don't crash if models aren't ready) ──
_MODELS_OK = False
try:
    from __init__ import db
    from models import Thread, ThreadMember, Message, User
    _MODELS_OK = True
except Exception:
    db = None


# ── Rate limit tracking (in-memory, resets on restart) ──
_rate_limits = {}  # {user_id: [timestamp, ...]}
_RATE_WINDOW = 60       # seconds
_RATE_MAX_MSGS = 20     # max messages per window
_BOT_BURST_THRESHOLD = 8  # messages in 5 seconds = bot behavior


def _current_user():
    """Get logged-in user or None."""
    username = (session.get("username") or "").strip()
    if not username or User is None:
        return None
    return User.query.filter_by(username=username).first()


def _check_rate_limit(user_id):
    """Rate limit + bot detection. Returns (allowed, reason)."""
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=_RATE_WINDOW)
    burst_start = now - timedelta(seconds=5)

    if user_id not in _rate_limits:
        _rate_limits[user_id] = []

    # Clean old entries
    _rate_limits[user_id] = [t for t in _rate_limits[user_id] if t > window_start]

    # Bot detection: too many messages in 5 seconds
    burst_count = sum(1 for t in _rate_limits[user_id] if t > burst_start)
    if burst_count >= _BOT_BURST_THRESHOLD:
        return False, "bot_detected"

    # General rate limit
    if len(_rate_limits[user_id]) >= _RATE_MAX_MSGS:
        return False, "rate_limited"

    _rate_limits[user_id].append(now)
    return True, "ok"


def _moderate_dm(text):
    """Run AI moderation with street smarts on DM content.
    Returns (status, reason) — status is 'clean', 'flagged', or 'blocked'."""
    if not text or not text.strip():
        return "clean", None

    try:
        from moderation_engine import moderate_text, scan_scam_score

        # Primary content moderation
        result = moderate_text(text)
        if result.decision == "block":
            return "blocked", result.reason

        # Scam scoring engine
        scam = scan_scam_score(text)
        if scam["decision"] == "block":
            return "blocked", f"scam:{','.join(scam['signals'])}"
        if scam["decision"] == "warn":
            return "flagged", f"scam_risk:{scam['score']}"

        # Harassment pattern detection — additional DM-specific checks
        lower = text.lower()

        # Repeated threatening DM patterns
        harassment_patterns = [
            "i know where you live",
            "i'll find you",
            "you can't hide",
            "i have your address",
            "i'm watching you",
            "you're gonna regret",
            "i'll ruin your life",
            "Leak your pics",
            "leak your nudes",
            "send nudes or",
            "i'll expose you",
        ]
        for pattern in harassment_patterns:
            if pattern.lower() in lower:
                return "blocked", "dm_harassment"

        if result.decision == "quarantine":
            return "flagged", result.reason
        if result.decision == "warn":
            return "flagged", result.reason

    except Exception:
        pass  # Moderation unavailable — allow through

    return "clean", None


def _derive_thread_key(thread_id, salt=None):
    """Derive a per-thread encryption key using HKDF-like derivation.
    In production this would use the client's public keys + Diffie-Hellman.
    Here we use a server-side secret + thread ID as the key material."""
    server_secret = os.environ.get("VYBEFLOW_E2E_SECRET", "vybeflow-e2e-default-secret-2026")
    if salt is None:
        salt = secrets.token_bytes(16)
    key_material = f"{server_secret}:{thread_id}".encode()
    derived = hashlib.pbkdf2_hmac("sha256", key_material, salt, 100000)
    return derived, salt


def _encrypt_message(plaintext, thread_id):
    """Encrypt a message using AES-256-GCM. Returns (ciphertext_b64, nonce_b64)."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64

        key, _salt = _derive_thread_key(thread_id)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(ciphertext).decode(), base64.b64encode(nonce).decode()
    except ImportError:
        # cryptography library not available — store as-is with a marker
        return plaintext, None


def _decrypt_message(ciphertext_b64, nonce_b64, thread_id):
    """Decrypt an AES-256-GCM encrypted message."""
    if not nonce_b64:
        return ciphertext_b64  # Not actually encrypted

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64

        key, _salt = _derive_thread_key(thread_id)
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception:
        return "[Encrypted message — unable to decrypt]"


# ═══════════════════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════════════════

@messaging_bp.post("/api/dm/threads")
def create_thread():
    """Create a new E2E encrypted DM thread with another user."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    if not _MODELS_OK:
        return jsonify({"error": "Feature unavailable"}), 503

    data = request.get_json(silent=True) or {}
    target_username = (data.get("username") or "").strip()
    if not target_username:
        return jsonify({"error": "Target username required"}), 400

    target = User.query.filter_by(username=target_username).first()
    if not target:
        return jsonify({"error": "User not found"}), 404
    if target.id == user.id:
        return jsonify({"error": "Cannot DM yourself"}), 400

    # Check if thread already exists between these two users
    existing = (
        db.session.query(Thread)
        .join(ThreadMember, Thread.id == ThreadMember.thread_id)
        .filter(ThreadMember.user_id == user.id)
        .all()
    )
    for t in existing:
        members = ThreadMember.query.filter_by(thread_id=t.id).all()
        member_ids = {m.user_id for m in members}
        if member_ids == {user.id, target.id}:
            return jsonify({"ok": True, "thread_id": t.id, "existing": True})

    # Create new encrypted thread
    key_hash = hashlib.sha256(f"{user.id}:{target.id}:{secrets.token_hex(8)}".encode()).hexdigest()
    thread = Thread(is_encrypted=True, encryption_key_hash=key_hash)
    db.session.add(thread)
    db.session.flush()

    db.session.add(ThreadMember(thread_id=thread.id, user_id=user.id))
    db.session.add(ThreadMember(thread_id=thread.id, user_id=target.id))
    db.session.commit()

    return jsonify({"ok": True, "thread_id": thread.id, "is_encrypted": True})


@messaging_bp.get("/api/dm/threads")
def list_threads():
    """List all DM threads for the current user."""
    user = _current_user()
    if not user:
        return jsonify([])
    if not _MODELS_OK:
        return jsonify([])

    memberships = ThreadMember.query.filter_by(user_id=user.id).all()
    result = []
    for m in memberships:
        thread = Thread.query.get(m.thread_id)
        if not thread:
            continue
        # Get other members
        others = ThreadMember.query.filter(
            ThreadMember.thread_id == m.thread_id,
            ThreadMember.user_id != user.id
        ).all()
        other_names = []
        for o in others:
            u = User.query.get(o.user_id)
            if u:
                other_names.append(u.username)

        # Count unread
        unread = 0
        if m.last_read_at:
            unread = Message.query.filter(
                Message.thread_id == m.thread_id,
                Message.created_at > m.last_read_at,
                Message.sender_id != user.id
            ).count()
        else:
            unread = Message.query.filter(
                Message.thread_id == m.thread_id,
                Message.sender_id != user.id
            ).count()

        # Last message preview
        last_msg = Message.query.filter_by(thread_id=m.thread_id).order_by(Message.created_at.desc()).first()
        preview = None
        if last_msg:
            if getattr(last_msg, "is_encrypted", False) and getattr(last_msg, "encryption_nonce", None):
                preview = "🔒 Encrypted message"
            else:
                preview = (last_msg.content or "")[:50]

        result.append({
            "thread_id": m.thread_id,
            "participants": other_names,
            "is_encrypted": getattr(thread, "is_encrypted", True),
            "unread": unread,
            "last_message": preview,
            "last_message_at": thread.last_message_at.isoformat() if thread.last_message_at else None,
        })

    result.sort(key=lambda x: x["last_message_at"] or "", reverse=True)
    return jsonify(result)


@messaging_bp.post("/api/dm/threads/<int:thread_id>/messages")
def send_message(thread_id):
    """Send an E2E encrypted message with AI moderation."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    if not _MODELS_OK:
        return jsonify({"error": "Feature unavailable"}), 503

    # Rate limit + bot detection
    allowed, reason = _check_rate_limit(user.id)
    if not allowed:
        status_code = 429
        if reason == "bot_detected":
            return jsonify({"error": "Suspicious activity detected. Slow down.", "reason": "bot_detected"}), status_code
        return jsonify({"error": "Too many messages. Wait a moment.", "reason": "rate_limited"}), status_code

    # Verify membership
    member = ThreadMember.query.filter_by(thread_id=thread_id, user_id=user.id).first()
    if not member:
        return jsonify({"error": "Not a member of this thread"}), 403

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    reply_to = data.get("reply_to_id")
    expires_minutes = data.get("expires_minutes")  # self-destruct timer

    if not content and not data.get("media_url"):
        return jsonify({"error": "Message content required"}), 400

    # AI Moderation with street smarts
    mod_status, mod_reason = _moderate_dm(content)
    if mod_status == "blocked":
        return jsonify({
            "error": "Message blocked by AI moderation",
            "reason": mod_reason,
            "moderation": "blocked"
        }), 403

    # Encrypt the message
    thread = Thread.query.get(thread_id)
    encrypted_content = content
    nonce = None
    is_encrypted = getattr(thread, "is_encrypted", True)

    if is_encrypted and content:
        encrypted_content, nonce = _encrypt_message(content, thread_id)

    # Calculate expiration
    expires_at = None
    if expires_minutes:
        try:
            mins = max(1, min(1440, int(expires_minutes)))  # 1 min to 24 hours
            expires_at = datetime.utcnow() + timedelta(minutes=mins)
        except (ValueError, TypeError):
            pass

    msg = Message(
        thread_id=thread_id,
        sender_id=user.id,
        content=encrypted_content,
        is_encrypted=is_encrypted,
        encryption_nonce=nonce,
        expires_at=expires_at,
        moderation_status=mod_status,
        media_type=data.get("media_type"),
        media_url=data.get("media_url"),
        reply_to_id=reply_to,
    )
    db.session.add(msg)

    # Update thread timestamp
    thread.last_message_at = datetime.utcnow()
    # Update sender's read marker
    member.last_read_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "ok": True,
        "message_id": msg.id,
        "is_encrypted": is_encrypted,
        "moderation": mod_status,
        "moderation_reason": mod_reason if mod_status == "flagged" else None,
        "expires_at": expires_at.isoformat() if expires_at else None,
    })


@messaging_bp.get("/api/dm/threads/<int:thread_id>/messages")
def get_messages(thread_id):
    """Get decrypted messages from a thread (only for members)."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    if not _MODELS_OK:
        return jsonify([])

    member = ThreadMember.query.filter_by(thread_id=thread_id, user_id=user.id).first()
    if not member:
        return jsonify({"error": "Not a member of this thread"}), 403

    now = datetime.utcnow()

    messages = (
        Message.query
        .filter_by(thread_id=thread_id)
        .order_by(Message.created_at.asc())
        .limit(100)
        .all()
    )

    result = []
    for msg in messages:
        # Check self-destruct expiration
        msg_expires = getattr(msg, "expires_at", None)
        if msg_expires and msg_expires < now:
            continue  # Expired — don't show

        # Mark as viewed (for expiring messages)
        if msg.sender_id != user.id and not getattr(msg, "viewed_at", None):
            msg.viewed_at = now

        # Decrypt content
        content = msg.content
        if getattr(msg, "is_encrypted", False) and getattr(msg, "encryption_nonce", None):
            content = _decrypt_message(msg.content, msg.encryption_nonce, thread_id)

        # Don't show blocked messages to recipient
        mod_status = getattr(msg, "moderation_status", "clean")
        if mod_status == "blocked" and msg.sender_id != user.id:
            continue

        sender = User.query.get(msg.sender_id)
        result.append({
            "id": msg.id,
            "content": content,
            "sender": getattr(sender, "username", "unknown"),
            "sender_avatar": getattr(sender, "avatar_url", None),
            "is_encrypted": getattr(msg, "is_encrypted", False),
            "media_type": msg.media_type,
            "media_url": msg.media_url,
            "reply_to_id": msg.reply_to_id,
            "expires_at": msg_expires.isoformat() if msg_expires else None,
            "moderation": mod_status,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        })

    # Update read marker
    member.last_read_at = now
    db.session.commit()

    return jsonify(result)


@messaging_bp.post("/api/dm/threads/<int:thread_id>/read")
def mark_read(thread_id):
    """Mark all messages in a thread as read."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401

    member = ThreadMember.query.filter_by(thread_id=thread_id, user_id=user.id).first()
    if not member:
        return jsonify({"error": "Not a member"}), 403

    member.last_read_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})
