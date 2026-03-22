from flask import Blueprint, request, jsonify, session
from __init__ import db
from models import Game, User

games_api = Blueprint("games_api", __name__)


def _get_user_id():
    """Get authenticated user ID from session or request."""
    # Check session first (VybeFlow uses session-based auth)
    username = session.get('username')
    if username:
        user = User.query.filter_by(username=username).first()
        if user:
            return user.id
    
    # Fallback to header (for API clients)
    user_id = request.headers.get("X-User-Id")
    if user_id:
        return int(user_id)
    
    # Fallback to request attribute
    return getattr(request, "user_id", None)


@games_api.get("/api/games")
def list_games():
    """List games with optional search and pagination."""
    q = (request.args.get("q") or "").strip().lower()
    limit = int(request.args.get("limit", 60))
    limit = max(1, min(limit, 200))

    qry = Game.query
    if q:
        qry = qry.filter(Game.title.ilike(f"%{q}%"))

    games = qry.order_by(Game.created_at.desc()).limit(limit).all()

    return jsonify({
        "items": [{
            "id": g.id,
            "title": g.title,
            "description": g.description or "",
            "play_url": g.play_url,
            "thumbnail_url": g.thumbnail_url or "",
            "tags": g.tags or "",
            "plays_count": g.plays_count,
            "likes_count": g.likes_count,
            "created_at": g.created_at.isoformat() if g.created_at else "",
        } for g in games]
    })


@games_api.post("/api/games")
def create_game():
    """Create a new game entry."""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    play_url = (data.get("play_url") or "").strip()

    if not title or not play_url:
        return jsonify({"ok": False, "error": "title and play_url required"}), 400

    g = Game(
        owner_id=int(user_id),
        title=title,
        description=(data.get("description") or "").strip() or None,
        play_url=play_url,
        thumbnail_url=(data.get("thumbnail_url") or "").strip() or None,
        tags=(data.get("tags") or "").strip() or None,
    )
    db.session.add(g)
    db.session.commit()
    return jsonify({"ok": True, "id": g.id}), 201


@games_api.patch("/api/games/<int:game_id>")
def update_game(game_id):
    """Update game stats (plays, likes)."""
    user_id = _get_user_id()
    
    game = Game.query.get_or_404(game_id)
    
    # Allow owner or any logged-in user to update stats
    data = request.get_json(silent=True) or {}
    
    if "plays_count" in data:
        game.plays_count = int(data["plays_count"])
    
    if "likes_count" in data:
        game.likes_count = int(data["likes_count"])
    
    # Only owner can update metadata
    if user_id == game.owner_id:
        if "title" in data:
            game.title = (data["title"] or "").strip()
        if "description" in data:
            game.description = (data["description"] or "").strip() or None
        if "tags" in data:
            game.tags = (data["tags"] or "").strip() or None
    
    db.session.commit()
    return jsonify({"ok": True})


@games_api.delete("/api/games/<int:game_id>")
def delete_game(game_id):
    """Delete a game (owner only)."""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    
    game = Game.query.get_or_404(game_id)
    
    if game.owner_id != user_id:
        return jsonify({"ok": False, "error": "Forbidden"}), 403
    
    db.session.delete(game)
    db.session.commit()
    return jsonify({"ok": True})
