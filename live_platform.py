import os
from flask import Flask, request, jsonify
from flask_login import login_required, current_user
from flask_socketio import SocketIO, join_room, emit
import redis

# LiveKit SDK
from livekit import api as lkapi  # livekit-api

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    message_queue=REDIS_URL,   # <-- Redis pub/sub for multi-instance scaling
    async_mode="eventlet"
)

LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "devsecret")


def make_livekit_token(identity: str, room_name: str, can_publish=True, can_subscribe=True):
    at = lkapi.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    at.with_identity(identity)
    at.with_name(identity)

    grant = lkapi.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=can_publish,
        can_subscribe=can_subscribe
    )
    at.with_grants(grant)
    return at.to_jwt()


# ---------- Simple Redis rate limit (events) ----------

def allow_event(user_id: str, key: str, limit: int, window_sec: int) -> bool:
    bucket = f"rl:{key}:{user_id}"
    count = r.incr(bucket)
    if count == 1:
        r.expire(bucket, window_sec)
    return count <= limit


# ---------- Live room metadata ----------
# In production you'd store this in DB. For now Redis is fine.

def room_key(room_name):
    return f"live:room:{room_name}"


@app.post("/api/live/create")
@login_required
def live_create():
    data = request.json or {}
    room_name = data.get("room_name") or f"room_{current_user.id}"
    title = data.get("title", "Live on VybeFlow")
    is_public = bool(data.get("is_public", True))

    r.hset(room_key(room_name), mapping={
        "host_id": str(current_user.id),
        "title": title,
        "is_public": "1" if is_public else "0",
        "delay": str(0),
        "is_live": "1"
    })

    token = make_livekit_token(str(current_user.id), room_name, can_publish=True, can_subscribe=True)
    return jsonify({"ok": True, "room_name": room_name, "token": token, "livekit_url": LIVEKIT_URL})


@app.post("/api/live/join")
@login_required
def live_join():
    data = request.json or {}
    room_name = data["room_name"]

    meta = r.hgetall(room_key(room_name))
    if not meta or meta.get("is_live") != "1":
        return jsonify({"ok": False, "error": "room_offline"}), 404

    # privacy check
    if meta.get("is_public") != "1":
        # TODO: implement invite list / followers check here
        return jsonify({"ok": False, "error": "private_room"}), 403

    token = make_livekit_token(str(current_user.id), room_name, can_publish=False, can_subscribe=True)
    return jsonify({"ok": True, "room_name": room_name, "token": token, "livekit_url": LIVEKIT_URL})


@app.post("/api/live/set_privacy")
@login_required
def live_set_privacy():
    data = request.json or {}
    room_name = data["room_name"]
    is_public = bool(data["is_public"])

    meta = r.hgetall(room_key(room_name))
    if meta.get("host_id") != str(current_user.id):
        return jsonify({"ok": False, "error": "not_host"}), 403

    r.hset(room_key(room_name), "is_public", "1" if is_public else "0")
    socketio.emit("room:privacy", {"room": room_name, "is_public": is_public}, to=f"ws:{room_name}")
    return jsonify({"ok": True})


@app.post("/api/live/set_delay")
@login_required
def live_set_delay():
    data = request.json or {}
    room_name = data["room_name"]
    delay = int(data.get("delay", 0))
    delay = max(0, min(delay, 10))

    meta = r.hgetall(room_key(room_name))
    if meta.get("host_id") != str(current_user.id):
        return jsonify({"ok": False, "error": "not_host"}), 403

    r.hset(room_key(room_name), "delay", str(delay))
    socketio.emit("room:delay", {"room": room_name, "delay": delay}, to=f"ws:{room_name}")
    return jsonify({"ok": True})


@app.post("/api/live/kill")
@login_required
def live_kill():
    data = request.json or {}
    room_name = data["room_name"]

    meta = r.hgetall(room_key(room_name))
    if meta.get("host_id") != str(current_user.id):
        return jsonify({"ok": False, "error": "not_host"}), 403

    r.hset(room_key(room_name), "is_live", "0")
    socketio.emit("room:killed", {"room": room_name}, to=f"ws:{room_name}")
    return jsonify({"ok": True})


# ---------- WebSocket events (heatmap reactions, pulse, moments, DJ) ----------

@socketio.on("connect")
def ws_connect():
    emit("ws:ok", {"ok": True})


@socketio.on("room:join")
def ws_room_join(data):
    room_name = data["room_name"]
    join_room(f"ws:{room_name}")
    emit("room:joined", {"room": room_name})


@socketio.on("react:tap")
def ws_react_tap(data):
    room_name = data["room_name"]
    emoji = data.get("emoji", "🔥")
    x = float(data.get("x", 0.5))
    y = float(data.get("y", 0.5))

    # rate limit: 12 taps per 3 seconds per user
    user_id = str(data.get("user_id") or "anon")
    if not allow_event(user_id, "react", limit=12, window_sec=3):
        return

    payload = {"emoji": emoji, "x": x, "y": y}
    emit("react:heat", payload, to=f"ws:{room_name}")


@socketio.on("pulse:set")
def ws_pulse_set(data):
    room_name = data["room_name"]
    mood = data.get("mood", "hype")

    user_id = str(data.get("user_id") or "anon")
    if not allow_event(user_id, "pulse", limit=6, window_sec=5):
        return

    # store pulse counts
    k = f"pulse:{room_name}:{mood}"
    r.incr(k)
    r.expire(k, 120)

    emit("pulse:update", {"mood": mood}, to=f"ws:{room_name}")


@socketio.on("moment:pin")
def ws_moment_pin(data):
    room_name = data["room_name"]
    label = (data.get("label") or "").strip()[:80]
    ts = float(data.get("timestamp", 0))

    if not label:
        return

    emit("moment:pin", {"label": label, "timestamp": ts}, to=f"ws:{room_name}")


@socketio.on("dj:trigger")
def ws_dj_trigger(data):
    room_name = data["room_name"]
    event = data.get("event", "airhorn")

    user_id = str(data.get("user_id") or "anon")
    if not allow_event(user_id, "dj", limit=4, window_sec=4):
        return

    emit("dj:trigger", {"event": event}, to=f"ws:{room_name}")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
