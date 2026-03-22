"""
DM SocketIO handlers — real-time encrypted messaging
=====================================================
Events:
  dm:join     — join a thread room
  dm:leave    — leave a thread room
  dm:send     — send a message (with AI moderation)
  dm:typing   — broadcast typing indicator
  dm:read     — mark thread as read
"""

from flask_socketio import join_room, leave_room, emit
from flask import session


def register_dm_socketio(socketio):
    """Register Socket.IO events for real-time DM."""

    @socketio.on("dm:join")
    def on_dm_join(data):
        thread_id = data.get("thread_id")
        if not thread_id:
            return
        username = (session.get("username") or "").strip()
        if not username:
            return

        # Verify membership
        try:
            from models import ThreadMember, User
            user = User.query.filter_by(username=username).first()
            if not user:
                return
            member = ThreadMember.query.filter_by(thread_id=thread_id, user_id=user.id).first()
            if not member:
                return
        except Exception:
            return

        room = f"dm:{thread_id}"
        join_room(room)
        emit("dm:presence", {"type": "join", "user": username}, room=room)

    @socketio.on("dm:leave")
    def on_dm_leave(data):
        thread_id = data.get("thread_id")
        if not thread_id:
            return
        username = (session.get("username") or "").strip()
        room = f"dm:{thread_id}"
        leave_room(room)
        emit("dm:presence", {"type": "leave", "user": username}, room=room)

    @socketio.on("dm:typing")
    def on_dm_typing(data):
        thread_id = data.get("thread_id")
        if not thread_id:
            return
        username = (session.get("username") or "").strip()
        if not username:
            return
        room = f"dm:{thread_id}"
        emit("dm:typing", {"user": username}, room=room, include_self=False)

    @socketio.on("dm:send")
    def on_dm_send(data):
        """Real-time message send via socket (mirrors the REST endpoint)."""
        thread_id = data.get("thread_id")
        content = (data.get("content") or "").strip()
        if not thread_id or not content:
            return

        username = (session.get("username") or "").strip()
        if not username:
            emit("dm:error", {"error": "Not authenticated"})
            return

        try:
            from models import ThreadMember, Message, Thread, User
            from __init__ import db
            from datetime import datetime

            user = User.query.filter_by(username=username).first()
            if not user:
                emit("dm:error", {"error": "User not found"})
                return

            member = ThreadMember.query.filter_by(thread_id=thread_id, user_id=user.id).first()
            if not member:
                emit("dm:error", {"error": "Not a member"})
                return

            # AI moderation
            from routes.messaging import _moderate_dm, _check_rate_limit, _encrypt_message
            allowed, reason = _check_rate_limit(user.id)
            if not allowed:
                emit("dm:error", {"error": "Rate limited", "reason": reason})
                return

            mod_status, mod_reason = _moderate_dm(content)
            if mod_status == "blocked":
                emit("dm:error", {"error": "Message blocked", "reason": mod_reason})
                return

            # Encrypt
            thread = Thread.query.get(thread_id)
            encrypted_content = content
            nonce = None
            if getattr(thread, "is_encrypted", True):
                encrypted_content, nonce = _encrypt_message(content, thread_id)

            msg = Message(
                thread_id=thread_id,
                sender_id=user.id,
                content=encrypted_content,
                is_encrypted=getattr(thread, "is_encrypted", True),
                encryption_nonce=nonce,
                moderation_status=mod_status,
            )
            db.session.add(msg)
            thread.last_message_at = datetime.utcnow()
            member.last_read_at = datetime.utcnow()
            db.session.commit()

            room = f"dm:{thread_id}"
            emit("dm:message", {
                "id": msg.id,
                "content": content,  # Send plaintext to connected clients
                "sender": username,
                "is_encrypted": getattr(msg, "is_encrypted", False),
                "moderation": mod_status,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }, room=room)

        except Exception as e:
            emit("dm:error", {"error": str(e)})

    @socketio.on("dm:read")
    def on_dm_read(data):
        thread_id = data.get("thread_id")
        if not thread_id:
            return
        username = (session.get("username") or "").strip()
        if not username:
            return
        try:
            from models import ThreadMember, User
            from __init__ import db
            from datetime import datetime

            user = User.query.filter_by(username=username).first()
            if not user:
                return
            member = ThreadMember.query.filter_by(thread_id=thread_id, user_id=user.id).first()
            if member:
                member.last_read_at = datetime.utcnow()
                db.session.commit()

            room = f"dm:{thread_id}"
            emit("dm:read", {"user": username}, room=room, include_self=False)
        except Exception:
            pass
