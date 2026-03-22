"""
adult_media.py  — Protected media streaming for adult content.

Never expose adult media URLs directly. Instead:
  1. Client requests a short-lived signed token via POST /api/media/token
  2. Client loads media from GET /m/<token> (token expires in 30 seconds)

Both endpoints enforce verified-18+ and post-approved checks.
"""

import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import Blueprint, current_app, abort, send_file, jsonify, request, session
from auth_guard import verified_adult_required

adult_media_bp = Blueprint("adult_media", __name__)


def _serializer():
    secret = current_app.config.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY missing")
    return URLSafeTimedSerializer(secret, salt="vybeflow-adult-media")


@adult_media_bp.post("/api/media/token")
@verified_adult_required
def create_media_token(_current_user=None, **kwargs):
    """Generate a 30-second signed token to stream a specific adult post's media."""
    from models import Post

    data = request.get_json(force=True) or {}
    post_id = int(data.get("post_id", 0))
    post = Post.query.get_or_404(post_id)

    # Must be an adult post
    if not post.is_adult:
        return jsonify({"ok": False, "error": "Not an adult post"}), 400

    # Must be approved by moderation
    if post.needs_review or not post.approved_at:
        return jsonify({"ok": False, "error": "Post not approved yet"}), 403

    # Must have stored media
    media_url = getattr(post, "media_url", None)
    if not media_url:
        return jsonify({"ok": False, "error": "No media"}), 404

    token = _serializer().dumps({"post_id": post.id})
    return jsonify({"ok": True, "token": token})


@adult_media_bp.get("/m/<token>")
def stream_adult_media(token: str):
    """Stream adult media using a short-lived signed token.

    Token expires after 30 seconds to prevent URL sharing.
    Even at stream time, we re-check that the user is verified 18+.
    """
    from models import Post, User

    # Re-verify the user at stream time
    username = session.get("username")
    user = User.query.filter_by(username=username).first() if username else None
    if not user:
        abort(401)
    if not getattr(user, "adult_verified", False):
        abort(403)
    if getattr(user, "adult_access_revoked", False):
        abort(403)

    # Validate the signed token
    try:
        payload = _serializer().loads(token, max_age=30)  # 30 seconds
    except SignatureExpired:
        abort(410)  # Gone
    except BadSignature:
        abort(404)

    post = Post.query.get_or_404(int(payload["post_id"]))

    # Double-check content controls at stream time
    if not post.is_adult:
        abort(400)
    if post.needs_review or not post.approved_at:
        abort(403)

    # Resolve the file on disk
    media_url = getattr(post, "media_url", "") or ""
    if not media_url:
        abort(404)

    # media_url may be a relative URL like /static/uploads/xxx or /uploads/xxx
    # Resolve to an absolute path
    if media_url.startswith("/static/uploads/"):
        rel = media_url[len("/static/uploads/"):]
        path = os.path.join(current_app.config.get("POST_UPLOAD_ABS", ""), rel)
    elif media_url.startswith("/uploads/"):
        rel = media_url[len("/uploads/"):]
        upload_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
        path = os.path.join(upload_dir, rel)
    else:
        path = media_url  # absolute path already

    path = os.path.abspath(path)
    if not os.path.exists(path):
        abort(404)

    import mimetypes
    guessed, _ = mimetypes.guess_type(path)
    mime = getattr(post, "media_mime", None) or guessed or "application/octet-stream"

    return send_file(path, mimetype=mime, conditional=True)
