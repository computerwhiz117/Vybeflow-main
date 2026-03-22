import time
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session
from __init__ import db
from models import Post, Story, StoryView, StoryLike, User as DbUser

story_routes = Blueprint("story_routes", __name__)

# --- In-memory demo store (replace with DB/Redis) ---
STICKER_PACKS = [
    {
        "id": "vf-core",
        "name": "VybeFlow Core",
        "items": [
            {"id": "fire", "label": "🔥 Fire"},
            {"id": "vibe", "label": "✨ Vibe"},
            {"id": "wave", "label": "🌊 Wave"},
            {"id": "money", "label": "💸 Money"},
        ],
    },
    {
        "id": "memes",
        "name": "Memes + Roast",
        "items": [
            {"id": "cap", "label": "🧢 CAP"},
            {"id": "W", "label": "✅ W"},
            {"id": "L", "label": "❌ L"},
            {"id": "ratio", "label": "📉 ratio"},
        ],
    },
    {
        "id": "animated",
        "name": "Animated",
        "items": [
            {"id": "fire", "label": "Fire", "type": "lottie", "src": "/static/lottie/fire.json"},
            {"id": "pulse", "label": "Pulse", "type": "lottie", "src": "/static/lottie/pulse.json"},
            {"id": "heart", "label": "Heart", "type": "lottie", "src": "/static/lottie/heart.json"},
        ],
    },
]

# story_id -> state
STORY_STATE = {}  # { story_id: { "updated_at":..., "state": {...}} }


@story_routes.get("/stories")
def stories_page():
    """Render the main Stories viewer page.

    This powers the dedicated /stories screen that shows the
    circular tray and full-screen viewer from templates/stories.html.
    """
    current_user = session.get("username") or "User"

    story_tray = []
    try:
        # Try to load any non-expired stories; if the schema or
        # helper methods are missing, fall back to an empty tray
        if Story is not None:
            stories = Story.query.filter(Story.created_at.isnot(None)).all()
        else:
            stories = []

        for s in stories:
            try:
                is_expired = getattr(s, "is_expired", None)
                if callable(is_expired) and is_expired():
                    continue
            except Exception:
                # If expiry logic blows up, still show the story
                pass

            story_tray.append({
                "id": s.id,
                "username": getattr(getattr(s, "author", None), "username", None)
                             or getattr(getattr(s, "user", None), "username", None)
                             or current_user,
                "avatar_url": getattr(getattr(s, "author", None), "avatar_url", None),
                "media_url": getattr(s, "media_url", None),
                "media_type": getattr(s, "media_type", None),
                "created_at": getattr(s, "created_at", None),
                "title": getattr(s, "title", None),
                "caption": getattr(s, "caption", None),
                "close_friends": getattr(s, "audience", "") == "close_friends",
                "seen": False,
            })
    except Exception as e:
        print(f"[stories] tray query failed: {e}")
        story_tray = []

    return render_template("stories.html", story_tray=story_tray, current_user=current_user)


@story_routes.get("/story/create/<story_id>")
def story_create(story_id):
    current_user = session.get('username') or 'User'
    return render_template("story_create.html", story_id=story_id, current_user=current_user)


@story_routes.get("/api/stickers/packs")
def sticker_packs():
    return jsonify({"packs": STICKER_PACKS})


@story_routes.get("/api/story/load")
def story_load():
    story_id = request.args.get("story_id", "").strip()
    if not story_id:
        return jsonify({"error": "missing story_id"}), 400

    rec = STORY_STATE.get(story_id)
    return jsonify({"story_id": story_id, "state": (rec["state"] if rec else None)})


@story_routes.post("/api/story/save")
def story_save():
    payload = request.get_json(silent=True) or {}
    story_id = (payload.get("story_id") or "").strip()
    state = payload.get("state")

    if not story_id or state is None:
        return jsonify({"error": "missing story_id/state"}), 400

    STORY_STATE[story_id] = {"updated_at": time.time(), "state": state}
    return jsonify({"ok": True})


@story_routes.post("/api/captions/transcribe")
def captions_transcribe():
    return jsonify({
        "ok": False,
        "message": "Server transcription not configured. Using on-device captions instead."
    })


@story_routes.get("/api/media/recents")
def media_recents():
    """
    Return user's recent photos/videos from DB-backed posts.
    Query params:
      - limit (default 60)
    """
    try:
        limit = int(request.args.get("limit", 60))
    except ValueError:
        limit = 60
    limit = max(1, min(limit, 200))

    email = (session.get("email") or "").strip().lower()
    username = (session.get("username") or "").strip()

    if not email and not username:
        return jsonify({"items": []})

    user = None
    if email:
        user = DbUser.query.filter_by(email=email).first()
    if not user and username:
        user = DbUser.query.filter_by(username=username).first()

    if not user:
        return jsonify({"items": []})

    posts = (
        Post.query
        .filter(Post.author_id == user.id)
        .filter(Post.media_url.isnot(None))
        .order_by(Post.created_at.desc())
        .limit(limit)
        .all()
    )

    items = []
    for post in posts:
        media_url = (post.media_url or "").strip()
        if not media_url:
            continue

        media_type = (post.media_type or "").strip().lower()
        if media_type not in ("image", "video"):
            lower = media_url.lower()
            media_type = "video" if lower.endswith((".mp4", ".mov", ".webm", ".m4v")) else "image"

        thumb = getattr(post, "thumbnail_url", None) or media_url

        items.append({
            "id": post.id,
            "type": media_type,
            "url": media_url,
            "thumb_url": thumb,
            "created_at": post.created_at.isoformat() if post.created_at else "",
        })

    return jsonify({"items": items})


@story_routes.post("/api/story/save")
def api_story_save():
    """Save or update story draft/state."""
    payload = request.get_json(silent=True) or {}
    
    # Validate minimal fields
    story_id = payload.get("story_id")
    content = payload.get("content", "")
    
    if not story_id:
        return jsonify({"ok": False, "error": "story_id required"}), 400
    
    # Get authenticated user
    username = session.get("username")
    if not username:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    
    user = DbUser.query.filter_by(username=username).first()
    if not user:
        return jsonify({"ok": False, "error": "User not found"}), 401
    
    # Store in STORY_STATE for real-time collaboration
    STORY_STATE[story_id] = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "state": payload,
        "user_id": user.id
    }
    
    # Optional: persist to database if story exists
    # Check if this is an existing story in DB
    if isinstance(story_id, int) or (isinstance(story_id, str) and story_id.isdigit()):
        story = Story.query.filter_by(id=int(story_id)).first()
        if story and story.author_id == user.id:
            # Update existing story
            if "caption" in payload:
                story.caption = payload["caption"]
            if "media_url" in payload:
                story.media_url = payload["media_url"]
            if "overlays_json" in payload:
                story.overlays_json = payload.get("overlays_json")
            if "music_track" in payload:
                story.music_track = payload["music_track"]
            
            db.session.commit()
    
    saved_at = datetime.utcnow().isoformat() + "Z"
    
    return jsonify({"ok": True, "saved_at": saved_at}), 200


@story_routes.post("/api/story/<int:story_id>/view")
def api_story_view(story_id: int):
    """Mark the current user as having viewed a story and return counts.

    This powers the IG-style "Seen" list.
    """
    username = (session.get("username") or "").strip()
    if not username:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    user = DbUser.query.filter_by(username=username).first()
    if not user:
        return jsonify({"ok": False, "error": "User not found"}), 401

    story = Story.query.get_or_404(story_id)

    existing = StoryView.query.filter_by(story_id=story.id, viewer_id=user.id).first()
    if not existing:
        existing = StoryView(story_id=story.id, viewer_id=user.id)
        db.session.add(existing)
        db.session.commit()

    total_views = StoryView.query.filter_by(story_id=story.id).count()
    return jsonify({"ok": True, "views": total_views}), 200


@story_routes.get("/api/story/<int:story_id>/views")
def api_story_views_list(story_id: int):
    """Return a lightweight list of who has seen a story."""
    story = Story.query.get_or_404(story_id)

    rows = (
        db.session.query(StoryView, DbUser)
        .join(DbUser, StoryView.viewer_id == DbUser.id)
        .filter(StoryView.story_id == story.id)
        .order_by(StoryView.created_at.desc())
        .limit(100)
        .all()
    )

    viewers = []
    for view, user in rows:
        viewers.append({
            "username": user.username,
            "display_name": getattr(user, "display_name", None) or user.username,
            "avatar_url": getattr(user, "avatar_url", None),
            "seen_at": view.created_at.isoformat() if view.created_at else None,
        })

    return jsonify({"ok": True, "total": len(viewers), "viewers": viewers}), 200


@story_routes.post("/api/story/<int:story_id>/like")
def api_story_like(story_id: int):
    """Toggle a like for the current user on a story and return counts."""
    username = (session.get("username") or "").strip()
    if not username:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    user = DbUser.query.filter_by(username=username).first()
    if not user:
        return jsonify({"ok": False, "error": "User not found"}), 401

    story = Story.query.get_or_404(story_id)

    existing = StoryLike.query.filter_by(story_id=story.id, user_id=user.id).first()
    liked = False
    if existing:
        db.session.delete(existing)
        db.session.commit()
    else:
        like = StoryLike(story_id=story.id, user_id=user.id)
        db.session.add(like)
        db.session.commit()
        liked = True

    total_likes = StoryLike.query.filter_by(story_id=story.id).count()
    return jsonify({"ok": True, "liked": liked, "likes": total_likes}), 200


@story_routes.get("/api/story/<int:story_id>/likes")
def api_story_likes_list(story_id: int):
    """Return a list of who liked a story."""
    story = Story.query.get_or_404(story_id)

    rows = (
        db.session.query(StoryLike, DbUser)
        .join(DbUser, StoryLike.user_id == DbUser.id)
        .filter(StoryLike.story_id == story.id)
        .order_by(StoryLike.created_at.desc())
        .limit(100)
        .all()
    )

    users = []
    for like, user in rows:
        users.append({
            "username": user.username,
            "display_name": getattr(user, "display_name", None) or user.username,
            "avatar_url": getattr(user, "avatar_url", None),
            "liked_at": like.created_at.isoformat() if like.created_at else None,
        })

    return jsonify({"ok": True, "total": len(users), "users": users}), 200
