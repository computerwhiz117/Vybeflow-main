"""
Vibe Rooms — Blueprint
=======================
Real-time audio/video rooms: rap cyphers, beat battles, prayer rooms,
business talk, late night chill, and custom rooms.
"""

from datetime import datetime
from flask import (
    Blueprint, request, session, redirect, url_for,
    render_template, flash, jsonify,
)
from __init__ import db

vibe_rooms_bp = Blueprint("vibe_rooms", __name__, url_prefix="/vibe-rooms")

ROOM_TYPES = {
    "rap_cypher":  {"label": "🎤 Rap Cypher",    "icon": "🎤", "color": "#ff4d00"},
    "beat_battle": {"label": "🥁 Beat Battle",   "icon": "🥁", "color": "#ff8226"},
    "prayer":      {"label": "🙏 Prayer Room",   "icon": "🙏", "color": "#ffb562"},
    "business":    {"label": "💼 Business Talk",  "icon": "💼", "color": "#4a90d9"},
    "chill":       {"label": "🌙 Late Night Chill", "icon": "🌙", "color": "#7c3aed"},
    "custom":      {"label": "✨ Custom Room",    "icon": "✨", "color": "#ff6a00"},
}


def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None
    return uid


# ---------------------------------------------------------------------------
# Room lobby – browse live & scheduled rooms
# ---------------------------------------------------------------------------
@vibe_rooms_bp.get("/")
def rooms_lobby():
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import VibeRoom, VibeRoomParticipant, User

    # Auto-end stale rooms: live for >24h or live with 0 participants
    stale_cutoff = datetime.utcnow()
    stale_rooms = VibeRoom.query.filter_by(is_live=True).all()
    for sr in stale_rooms:
        age_hours = (stale_cutoff - sr.created_at).total_seconds() / 3600
        pcount = VibeRoomParticipant.query.filter_by(room_id=sr.id).count()
        if age_hours > 24 or pcount == 0:
            sr.is_live = False
            sr.ended_at = stale_cutoff
    db.session.commit()

    live_rooms = (
        VibeRoom.query
        .filter_by(is_live=True)
        .order_by(VibeRoom.created_at.desc())
        .limit(30)
        .all()
    )

    scheduled_rooms = (
        VibeRoom.query
        .filter(VibeRoom.is_live == False, VibeRoom.scheduled_at != None, VibeRoom.ended_at == None)
        .order_by(VibeRoom.scheduled_at.asc())
        .limit(20)
        .all()
    )

    # Also get ended rooms so hosts can delete them
    ended_rooms = (
        VibeRoom.query
        .filter(VibeRoom.ended_at != None)
        .order_by(VibeRoom.ended_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "vibe_rooms.html",
        live_rooms=live_rooms,
        scheduled_rooms=scheduled_rooms,
        ended_rooms=ended_rooms,
        room_types=ROOM_TYPES,
        current_user=User.query.get(uid),
    )


# ---------------------------------------------------------------------------
# Create a Vibe Room
# ---------------------------------------------------------------------------
@vibe_rooms_bp.route("/create", methods=["GET", "POST"])
def create_room():
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    if request.method == "POST":
        from models import VibeRoom, VibeRoomParticipant

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        room_type = request.form.get("room_type", "chill").strip()
        max_speakers = int(request.form.get("max_speakers", 10))
        max_listeners = int(request.form.get("max_listeners", 100))
        go_live_now = request.form.get("go_live_now") == "on"
        scheduled_at_str = request.form.get("scheduled_at", "").strip()

        if not name:
            flash("Room name is required.", "error")
            return redirect(url_for("vibe_rooms.create_room"))

        room = VibeRoom(
            name=name,
            description=description,
            host_id=uid,
            room_type=room_type if room_type in ROOM_TYPES else "chill",
            max_speakers=max_speakers,
            max_listeners=max_listeners,
            is_live=go_live_now,
        )

        if scheduled_at_str and not go_live_now:
            try:
                room.scheduled_at = datetime.fromisoformat(scheduled_at_str)
            except ValueError:
                pass

        db.session.add(room)
        db.session.flush()

        # Auto-join creator as host
        participant = VibeRoomParticipant(
            room_id=room.id,
            user_id=uid,
            role="host",
            is_muted=False,
        )
        db.session.add(participant)
        db.session.commit()

        if go_live_now:
            flash(f"Room '{name}' is LIVE! 🔥", "success")
            return redirect(url_for("vibe_rooms.room_view", room_id=room.id))
        else:
            flash(f"Room '{name}' scheduled! 📅", "success")
            return redirect(url_for("vibe_rooms.rooms_lobby"))

    return render_template("vibe_room_create.html", room_types=ROOM_TYPES)


# ---------------------------------------------------------------------------
# View / join a room
# ---------------------------------------------------------------------------
@vibe_rooms_bp.get("/<int:room_id>")
def room_view(room_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import VibeRoom, VibeRoomParticipant, User

    room = VibeRoom.query.get_or_404(room_id)
    participants = VibeRoomParticipant.query.filter_by(room_id=room_id).all()

    # Enrich participant data
    user_ids = [p.user_id for p in participants]
    users_map = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

    participant_data = []
    for p in participants:
        u = users_map.get(p.user_id)
        participant_data.append({
            "user_id": p.user_id,
            "username": (u.display_name or u.username) if u else "Unknown",
            "avatar_url": (u.avatar_url if u else None) or url_for("static", filename="VFlogo_clean.png"),
            "role": p.role,
            "is_muted": p.is_muted,
        })

    is_participant = any(p.user_id == uid for p in participants)
    my_role = next((p.role for p in participants if p.user_id == uid), None)
    is_host = (room.host_id == uid)
    room_meta = ROOM_TYPES.get(room.room_type, ROOM_TYPES["custom"])

    return render_template(
        "vibe_room_view.html",
        room=room,
        participants=participant_data,
        is_participant=is_participant,
        my_role=my_role,
        is_host=is_host,
        room_meta=room_meta,
        current_user=User.query.get(uid),
    )


# ---------------------------------------------------------------------------
# Join room
# ---------------------------------------------------------------------------
@vibe_rooms_bp.route("/<int:room_id>/join", methods=["POST"])
def join_room(room_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import VibeRoom, VibeRoomParticipant

    room = VibeRoom.query.get_or_404(room_id)
    existing = VibeRoomParticipant.query.filter_by(room_id=room_id, user_id=uid).first()
    if existing:
        return redirect(url_for("vibe_rooms.room_view", room_id=room_id))

    participant = VibeRoomParticipant(
        room_id=room_id,
        user_id=uid,
        role="listener",
        is_muted=True,
    )
    db.session.add(participant)
    db.session.commit()
    return redirect(url_for("vibe_rooms.room_view", room_id=room_id))


# ---------------------------------------------------------------------------
# Leave room
# ---------------------------------------------------------------------------
@vibe_rooms_bp.route("/<int:room_id>/leave", methods=["POST"])
def leave_room(room_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import VibeRoomParticipant

    p = VibeRoomParticipant.query.filter_by(room_id=room_id, user_id=uid).first()
    if p:
        db.session.delete(p)
        db.session.commit()
    return redirect(url_for("vibe_rooms.rooms_lobby"))


# ---------------------------------------------------------------------------
# Request to speak / promote to speaker (host only)
# ---------------------------------------------------------------------------
@vibe_rooms_bp.route("/<int:room_id>/request-speak", methods=["POST"])
def request_speak(room_id):
    uid = _require_login()
    if uid is None:
        return jsonify({"error": "Login required"}), 401

    from models import VibeRoomParticipant

    p = VibeRoomParticipant.query.filter_by(room_id=room_id, user_id=uid).first()
    if not p:
        return jsonify({"error": "Not in room"}), 400

    # Auto-promote for now (in production, host would approve)
    p.role = "speaker"
    p.is_muted = False
    db.session.commit()

    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"status": "promoted", "role": "speaker"})
    flash("You're now a speaker! 🎤", "success")
    return redirect(url_for("vibe_rooms.room_view", room_id=room_id))


@vibe_rooms_bp.route("/<int:room_id>/end", methods=["POST"])
def end_room(room_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import VibeRoom

    room = VibeRoom.query.get_or_404(room_id)
    if room.host_id != uid:
        flash("Only the host can end the room.", "error")
        return redirect(url_for("vibe_rooms.room_view", room_id=room_id))

    room.is_live = False
    room.ended_at = datetime.utcnow()
    db.session.commit()
    flash("Room ended. 🎤🔥", "info")
    return redirect(url_for("vibe_rooms.rooms_lobby"))


# ---------------------------------------------------------------------------
# Delete room (host only)
# ---------------------------------------------------------------------------
@vibe_rooms_bp.route("/<int:room_id>/delete", methods=["POST"])
def delete_room(room_id):
    uid = _require_login()
    if uid is None:
        return jsonify({"error": "Login required"}), 401

    from models import VibeRoom, VibeRoomParticipant

    room = VibeRoom.query.get_or_404(room_id)
    if room.host_id != uid:
        return jsonify({"error": "Only the host can delete the room"}), 403

    VibeRoomParticipant.query.filter_by(room_id=room_id).delete()
    db.session.delete(room)
    db.session.commit()

    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"status": "deleted"})
    flash("Room deleted.", "info")
    return redirect(url_for("vibe_rooms.rooms_lobby"))
