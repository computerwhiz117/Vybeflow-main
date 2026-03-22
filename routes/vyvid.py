"""
routes/vyvid.py — Vyvid: VybeFlow's mature-content video platform

Content Policy
--------------
ALLOWED:
  • Explicit sexual language and adult discussions
  • Adult comedy and podcasts
  • Relationship or sexual education content
  • Swearing and mature conversation

NOT ALLOWED (hard-blocked by moderation):
  • Graphic violence against others (killings, severe injury, torture, gore)
  • Violence being encouraged or glorified

Content Ratings:
  general — safe for all audiences (no verification needed)
  teen    — mild profanity / mild themes (no verification needed)
  mature  — explicit language, adult content (18+ verified required)

Advertiser Tiers (advertisers choose which tier their ads appear in):
  family  — family-friendly brands → general content only
  podcast — podcasts / mature discussions → teen + general
  adult   — adult-targeted brands → mature + teen + general
"""

import os
from datetime import datetime, date
from flask import (
    # NOTE: current_app used below for scanner
# noqa — imports below
    Blueprint, render_template, session, redirect, url_for,
    request, jsonify, flash, abort, current_app,
)
from __init__ import db

vyvid_bp = Blueprint("vyvid", __name__, url_prefix="/vyvid")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_user():
    """Return the logged-in User ORM object or None."""
    from models import User
    uid = session.get("user_id")
    if uid:
        return User.query.get(uid)
    username = session.get("username")
    if username:
        return User.query.filter_by(username=username).first()
    return None


def _require_login():
    user = _current_user()
    if not user:
        return None, redirect(url_for("login"))
    return user, None


def _is_age_verified(user) -> bool:
    """Return True if user has passed 18+ age verification (DOB self-declaration is enough for viewing)."""
    return bool(getattr(user, "adult_verified", False)) and not bool(getattr(user, "adult_access_revoked", False))


def _is_id_verified(user) -> bool:
    """Return True if user has submitted a government-issued ID that has been approved.

    Required for uploading any video to Vyvid (regardless of content rating).
    We check the UserVerification record's id_verified flag.
    """
    if user is None:
        return False
    try:
        from models import UserVerification
        uv = UserVerification.query.filter_by(user_id=user.id).first()
        if uv and uv.id_verified:
            return True
    except Exception:
        pass
    return False


def _can_view_rating(user, rating: str) -> bool:
    """Return True if user is allowed to view content at the given rating."""
    if rating in ("general", "teen"):
        return True  # open to all logged-in users
    if rating == "mature":
        return user is not None and _is_age_verified(user)
    return False


# ---------------------------------------------------------------------------
# Main Vyvid hub
# ---------------------------------------------------------------------------

@vyvid_bp.get("/")
def vyvid_home():
    user = _current_user()
    if not user:
        return redirect(url_for("login"))

    from models import VyvidVideo, VyvidLike

    age_verified = _is_age_verified(user)

    # Determine which ratings the user can see
    allowed_ratings = ["general", "teen"]
    if age_verified:
        allowed_ratings.append("mature")

    # Active filter from query params
    rating_filter = request.args.get("rating", "all")
    category_filter = request.args.get("category", "all")
    sort = request.args.get("sort", "new")  # new | popular

    # Build query
    q = VyvidVideo.query.filter(
        VyvidVideo.visibility == "public",
        VyvidVideo.is_approved == True,
        VyvidVideo.content_rating.in_(allowed_ratings),
    )

    if rating_filter != "all" and rating_filter in allowed_ratings:
        q = q.filter(VyvidVideo.content_rating == rating_filter)

    if category_filter != "all":
        q = q.filter(VyvidVideo.category == category_filter)

    if sort == "popular":
        q = q.order_by(VyvidVideo.views_count.desc(), VyvidVideo.created_at.desc())
    else:
        q = q.order_by(VyvidVideo.created_at.desc())

    videos = q.limit(60).all()

    # IDs the user has liked
    liked_ids = set()
    try:
        likes = VyvidLike.query.filter_by(user_id=user.id).all()
        liked_ids = {lk.video_id for lk in likes}
    except Exception:
        pass

    from models import VYVID_CATEGORIES
    return render_template(
        "vyvid.html",
        user=user,
        videos=videos,
        age_verified=age_verified,
        rating_filter=rating_filter,
        category_filter=category_filter,
        sort=sort,
        liked_ids=liked_ids,
        categories=VYVID_CATEGORIES,
        allowed_ratings=allowed_ratings,
    )


# ---------------------------------------------------------------------------
# Watch page
# ---------------------------------------------------------------------------

@vyvid_bp.get("/watch/<int:video_id>")
def vyvid_watch(video_id: int):
    user = _current_user()
    if not user:
        return redirect(url_for("login"))

    from models import VyvidVideo, VyvidLike, VyvidComment

    video = VyvidVideo.query.get_or_404(video_id)

    if not video.is_approved:
        # Allow the uploader to preview their own pending/rejected video
        if video.author_id != user.id:
            abort(404)

    if not _can_view_rating(user, video.content_rating):
        # Redirect to age gate for mature content
        if video.content_rating == "mature":
            flash("This video requires 18+ age verification.", "warning")
            return redirect(url_for("vyvid.vyvid_age_gate"))
        abort(403)

    # Increment view count
    try:
        video.views_count = (video.views_count or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()

    liked = False
    try:
        liked = VyvidLike.query.filter_by(user_id=user.id, video_id=video.id).first() is not None
    except Exception:
        pass

    comments = []
    try:
        comments = (VyvidComment.query
                    .filter_by(video_id=video.id, is_hidden=False)
                    .order_by(VyvidComment.created_at.desc())
                    .limit(50).all())
    except Exception:
        pass

    # Related videos (same category or rating, excluding current)
    related = []
    try:
        allowed_ratings = ["general", "teen"]
        if _is_age_verified(user):
            allowed_ratings.append("mature")
        related = (VyvidVideo.query
                   .filter(
                       VyvidVideo.id != video.id,
                       VyvidVideo.is_approved == True,
                       VyvidVideo.visibility == "public",
                       VyvidVideo.content_rating.in_(allowed_ratings),
                   )
                   .order_by(VyvidVideo.created_at.desc())
                   .limit(12).all())
    except Exception:
        pass

    return render_template(
        "vyvid_watch.html",
        user=user,
        video=video,
        liked=liked,
        comments=comments,
        related=related,
        age_verified=_is_age_verified(user),
    )


# ---------------------------------------------------------------------------
# Age gate / verification
# ---------------------------------------------------------------------------

@vyvid_bp.get("/verify-age")
def vyvid_age_gate():
    user = _current_user()
    if not user:
        return redirect(url_for("login"))

    # ?next=upload means user is going to upload — they need full ID verification.
    # ?next=mature  means user just wants to watch mature content — DOB is enough.
    next_action = request.args.get("next", "mature")

    # If user already has everything they need for the requested action, skip the gate.
    if next_action == "upload" and _is_id_verified(user):
        return redirect(url_for("vyvid.vyvid_upload_page"))
    if next_action != "upload" and _is_age_verified(user) and _is_id_verified(user):
        return redirect(url_for("vyvid.vyvid_home"))
    if next_action != "upload" and _is_age_verified(user):
        # Already age-verified but may still want to do mature viewing — let through.
        return redirect(url_for("vyvid.vyvid_home"))

    return render_template("vyvid_age_gate.html", user=user,
                           next_action=next_action,
                           id_verified=_is_id_verified(user),
                           age_verified=_is_age_verified(user))


@vyvid_bp.post("/verify-age")
def vyvid_age_gate_submit():
    """Process age + ID verification.

    For watching mature content: DOB self-declaration is sufficient.
    For uploading any video:     A government-issued ID document is REQUIRED.

    Privacy: We read the DOB from the form and note that an ID was submitted.
    The ID image is never stored on disk — only the User's verification status
    and date of birth are saved.
    """
    user = _current_user()
    if not user:
        return redirect(url_for("login"))

    next_action = request.form.get("next_action", "mature")

    dob_str = request.form.get("date_of_birth", "").strip()
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Please enter a valid date of birth (YYYY-MM-DD).", "error")
        return redirect(url_for("vyvid.vyvid_age_gate", next=next_action))

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 18:
        flash("You must be 18 or older to use Vyvid.", "error")
        return redirect(url_for("vyvid.vyvid_age_gate", next=next_action))

    # Check whether an ID document was uploaded
    id_file = request.files.get("id_document")
    id_submitted = bool(id_file and id_file.filename)

    # Uploading requires a real ID document — reject if missing
    if next_action == "upload" and not id_submitted:
        flash("A government-issued ID is required to upload videos to Vyvid.", "error")
        return redirect(url_for("vyvid.vyvid_age_gate", next="upload"))

    if id_submitted:
        provider = "id_upload_self_declared"
        ref = "vyvid-id-verified"
        # ID image is intentionally NOT saved — we only record that one was submitted.
        # In production, integrate Yoti/Veriff to extract DOB via OCR.
    else:
        provider = "self_declared"
        ref = "vyvid-dob-self"

    try:
        # Update User record — age verification
        user.adult_verified = True
        user.adult_verified_at = datetime.utcnow()
        user.adult_verification_provider = provider
        user.adult_verification_ref = ref
        user.date_of_birth = dob

        # If an ID was submitted, record it in UserVerification
        if id_submitted:
            from models import UserVerification
            uv = UserVerification.query.filter_by(user_id=user.id).first()
            if not uv:
                uv = UserVerification(user_id=user.id)  # type: ignore[call-arg]
                db.session.add(uv)
            uv.id_verified = True
            uv.id_verified_at = datetime.utcnow()
            uv.id_review_status = "approved"
            # ID image is NOT stored — privacy protected
            uv.id_document_url = None

        db.session.commit()

        if id_submitted:
            flash("ID verified! You can now upload videos and access all Vyvid content.", "success")
        else:
            flash("Age verified! You now have access to Vyvid mature content.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Verification failed. Please try again.", "error")
        current_app.logger.error(f"[vyvid] age gate commit failed: {e}")
        return redirect(url_for("vyvid.vyvid_age_gate", next=next_action))

    if next_action == "upload":
        return redirect(url_for("vyvid.vyvid_upload_page"))
    return redirect(url_for("vyvid.vyvid_home"))


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@vyvid_bp.get("/upload")
def vyvid_upload_page():
    user = _current_user()
    if not user:
        return redirect(url_for("login"))
    from models import VYVID_CATEGORIES
    id_verified = _is_id_verified(user)
    # Gate: ID verification is required for ALL uploads
    if not id_verified:
        flash("You must verify your identity with a government-issued ID before uploading to Vyvid.", "warning")
        return redirect(url_for("vyvid.vyvid_age_gate", next="upload"))
    return render_template("vyvid_upload.html", user=user, categories=VYVID_CATEGORIES, id_verified=True)


@vyvid_bp.post("/upload")
def vyvid_upload_submit():
    """Handle video upload form."""
    user = _current_user()
    if not user:
        return redirect(url_for("login"))

    from models import VyvidVideo

    # Re-check ID verification at submit time (defence-in-depth)
    if not _is_id_verified(user):
        flash("ID verification is required to upload videos to Vyvid.", "warning")
        return redirect(url_for("vyvid.vyvid_age_gate", next="upload"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    content_rating = request.form.get("content_rating", "general").strip()
    category = request.form.get("category", "other").strip()
    tags = request.form.get("tags", "").strip()

    if not title:
        flash("Please provide a video title.", "error")
        return redirect(url_for("vyvid.vyvid_upload_page"))

    if content_rating not in ("general", "teen", "mature"):
        content_rating = "general"

    # For mature content, user must also be age-verified
    if content_rating == "mature" and not _is_age_verified(user):
        flash("You must verify your age before uploading mature content.", "warning")
        return redirect(url_for("vyvid.vyvid_age_gate", next="mature"))

    # Advertiser tier maps from content rating
    tier_map = {"general": "family", "teen": "podcast", "mature": "adult"}
    advertiser_tier = tier_map.get(content_rating, "family")

    # Video file
    video_file = request.files.get("video_file")
    if not video_file or not video_file.filename:
        flash("Please select a video file to upload.", "error")
        return redirect(url_for("vyvid.vyvid_upload_page"))

    # Save to uploads folder
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "vyvid")
    os.makedirs(upload_dir, exist_ok=True)

    import uuid
    ext = os.path.splitext(video_file.filename)[1].lower()
    allowed_exts = {".mp4", ".webm", ".mov", ".m4v"}
    if ext not in allowed_exts:
        flash("Unsupported video format. Please upload MP4, WebM, or MOV.", "error")
        return redirect(url_for("vyvid.vyvid_upload_page"))

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    video_file.save(filepath)
    video_url = f"/static/uploads/vyvid/{filename}"

    # Optional thumbnail
    thumbnail_url = None
    thumb_file = request.files.get("thumbnail")
    if thumb_file and thumb_file.filename:
        thumb_ext = os.path.splitext(thumb_file.filename)[1].lower()
        if thumb_ext in {".jpg", ".jpeg", ".png", ".webp"}:
            thumb_filename = f"thumb_{uuid.uuid4().hex}{thumb_ext}"
            thumb_path = os.path.join(upload_dir, thumb_filename)
            thumb_file.save(thumb_path)
            thumbnail_url = f"/static/uploads/vyvid/{thumb_filename}"

    # All uploads go live immediately; AI scanner will flag and de-approve explicit content
    needs_review = False
    is_approved = True
    approved_at = datetime.utcnow()

    video = VyvidVideo(  # pyright: ignore[reportCallIssue]
        author_id=user.id,  # pyright: ignore[reportCallIssue]
        title=title,  # pyright: ignore[reportCallIssue]
        description=description,  # pyright: ignore[reportCallIssue]
        video_url=video_url,  # pyright: ignore[reportCallIssue]
        thumbnail_url=thumbnail_url,  # pyright: ignore[reportCallIssue]
        content_rating=content_rating,  # pyright: ignore[reportCallIssue]
        category=category,  # pyright: ignore[reportCallIssue]
        tags=tags,  # pyright: ignore[reportCallIssue]
        advertiser_tier=advertiser_tier,  # pyright: ignore[reportCallIssue]
        needs_review=needs_review,  # pyright: ignore[reportCallIssue]
        is_approved=is_approved,  # pyright: ignore[reportCallIssue]
        approved_at=approved_at,  # pyright: ignore[reportCallIssue]
    )
    try:
        db.session.add(video)
        db.session.commit()
        # Kick off background AI scan (filepath is already the absolute OS path)
        try:
            from video_scanner import scan_video_async
            scan_video_async(video.id, filepath, current_app._get_current_object())  # type: ignore[attr-defined]
        except Exception as scan_err:
            current_app.logger.warning(f"[vyvid] could not start scan: {scan_err}")

        flash("Video uploaded! Your video is now live.", "success")
        return redirect(url_for("vyvid.vyvid_watch", video_id=video.id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[vyvid] upload failed: {e}")
        flash("Upload failed. Please try again.", "error")
        return redirect(url_for("vyvid.vyvid_upload_page"))


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@vyvid_bp.post("/api/like/<int:video_id>")
def api_like(video_id: int):
    user = _current_user()
    if not user:
        return jsonify({"ok": False, "error": "Login required"}), 401

    from models import VyvidVideo, VyvidLike

    video = VyvidVideo.query.get_or_404(video_id)
    if not _can_view_rating(user, video.content_rating):
        return jsonify({"ok": False, "error": "Access denied"}), 403

    existing = VyvidLike.query.filter_by(user_id=user.id, video_id=video_id).first()
    if existing:
        # Unlike
        db.session.delete(existing)
        video.likes_count = max(0, (video.likes_count or 1) - 1)
        db.session.commit()
        return jsonify({"ok": True, "liked": False, "likes": video.likes_count})
    else:
        lk = VyvidLike(user_id=user.id, video_id=video_id)  # type: ignore[call-arg]
        db.session.add(lk)
        video.likes_count = (video.likes_count or 0) + 1
        db.session.commit()
        return jsonify({"ok": True, "liked": True, "likes": video.likes_count})


@vyvid_bp.post("/api/comment/<int:video_id>")
def api_comment(video_id: int):
    user = _current_user()
    if not user:
        return jsonify({"ok": False, "error": "Login required"}), 401

    from models import VyvidVideo, VyvidComment

    video = VyvidVideo.query.get_or_404(video_id)
    if not _can_view_rating(user, video.content_rating):
        return jsonify({"ok": False, "error": "Access denied"}), 403

    data = request.get_json(force=True) or {}
    body = (data.get("body") or "").strip()
    if not body or len(body) > 2000:
        return jsonify({"ok": False, "error": "Comment must be 1–2000 characters"}), 400

    comment = VyvidComment(video_id=video_id, author_id=user.id, body=body)  # type: ignore[call-arg]
    video.comments_count = (video.comments_count or 0) + 1
    db.session.add(comment)
    db.session.commit()

    return jsonify({
        "ok": True,
        "comment": {
            "id": comment.id,
            "body": comment.body,
            "author_username": user.username,
            "author_avatar": user.avatar_url,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
        }
    })


@vyvid_bp.get("/api/videos")
def api_videos():
    """JSON feed of Vyvid videos — respects the caller's verification level."""
    user = _current_user()
    if not user:
        return jsonify({"ok": False, "error": "Login required"}), 401

    age_verified = _is_age_verified(user)
    allowed_ratings = ["general", "teen"] + (["mature"] if age_verified else [])

    rating = request.args.get("rating", "all")
    category = request.args.get("category", "all")
    sort = request.args.get("sort", "new")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(int(request.args.get("per_page", 20)), 50)

    from models import VyvidVideo

    q = VyvidVideo.query.filter(
        VyvidVideo.visibility == "public",
        VyvidVideo.is_approved == True,
        VyvidVideo.content_rating.in_(allowed_ratings),
    )
    if rating != "all" and rating in allowed_ratings:
        q = q.filter(VyvidVideo.content_rating == rating)
    if category != "all":
        q = q.filter(VyvidVideo.category == category)
    if sort == "popular":
        q = q.order_by(VyvidVideo.views_count.desc(), VyvidVideo.created_at.desc())
    else:
        q = q.order_by(VyvidVideo.created_at.desc())

    total = q.count()
    videos = q.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "ok": True,
        "total": total,
        "page": page,
        "videos": [v.to_dict() for v in videos],
    })


# ---------------------------------------------------------------------------
# Real-time scan status (polled by the uploader after upload)
# ---------------------------------------------------------------------------

@vyvid_bp.get("/api/scan-status/<int:video_id>")
def api_scan_status(video_id: int):
    """
    Returns the current AI scan status and genre for a video.
    Only the uploader may query this endpoint (others get 403).
    Polled by the watch-page JS every 2 s while scan_status is pending/scanning.
    """
    user = _current_user()
    if not user:
        return jsonify({"ok": False, "error": "Login required"}), 401

    from models import VyvidVideo
    from video_scanner import GENRE_DISPLAY_NAMES

    video = VyvidVideo.query.get_or_404(video_id)
    if video.author_id != user.id:
        return jsonify({"ok": False, "error": "Forbidden"}), 403

    genre_key = video.scan_genre or "other"
    genre_label = GENRE_DISPLAY_NAMES.get(genre_key, "Other / General")

    return jsonify({
        "ok": True,
        "video_id": video.id,
        "scan_status": video.scan_status,            # pending|scanning|clean|suggestive|explicit|error
        "scan_score": video.scan_score,
        "scan_genre": genre_key,
        "scan_genre_label": genre_label,
        "is_approved": video.is_approved,
        "adult_id_required": bool(getattr(video, "adult_id_required", False)),
        "scan_completed": video.scan_completed_at is not None,
    })


# ---------------------------------------------------------------------------
# Adult-content ID verification (triggered by scanner when porn detected)
# ---------------------------------------------------------------------------

@vyvid_bp.get("/adult-id-verify/<int:video_id>")
def adult_id_verify_page(video_id: int):
    """
    Dedicated page shown to an uploader when the AI scanner detected
    explicit/adult content in their video and requires ID age confirmation.
    Explains clearly that ONLY the date of birth will be extracted.
    """
    user = _current_user()
    if not user:
        return redirect(url_for("login"))

    from models import VyvidVideo
    video = VyvidVideo.query.get_or_404(video_id)
    if video.author_id != user.id:
        abort(403)

    # Already verified for adult content — skip
    try:
        from models import UserVerification
        uv = UserVerification.query.filter_by(user_id=user.id).first()
        if uv and getattr(uv, "adult_content_verified", False):
            # Clear the flag and allow re-approval
            video.adult_id_required = False
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            flash("Adult content identity already verified. Your video is being reviewed.", "success")
            return redirect(url_for("vyvid.vyvid_watch", video_id=video_id))
    except Exception:
        pass

    return render_template(
        "vyvid_adult_id_verify.html",
        user=user,
        video=video,
        today=date.today(),
    )


@vyvid_bp.post("/adult-id-verify/<int:video_id>")
def adult_id_verify_submit(video_id: int):
    """
    Process ID submission for adult content verification.
    We only record the date of birth and that a valid-looking ID was presented.
    The ID IMAGE IS NEVER STORED on our servers — only the DOB is saved.
    """
    user = _current_user()
    if not user:
        return redirect(url_for("login"))

    from models import VyvidVideo, UserVerification

    video = VyvidVideo.query.get_or_404(video_id)
    if video.author_id != user.id:
        abort(403)

    dob_str = request.form.get("date_of_birth", "").strip()
    id_file  = request.files.get("id_document")

    # Validate date of birth
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Please enter a valid date of birth (YYYY-MM-DD).", "error")
        return redirect(url_for("vyvid.adult_id_verify_page", video_id=video_id))

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 18:
        flash("You must be 18 or older to publish adult content.", "error")
        return redirect(url_for("vyvid.adult_id_verify_page", video_id=video_id))

    # Require an ID document to be uploaded (it will NOT be stored)
    if not id_file or not id_file.filename:
        flash("A government-issued ID document is required. Only your date of birth will be recorded.", "error")
        return redirect(url_for("vyvid.adult_id_verify_page", video_id=video_id))

    # Validate ID file type (image only — simple extension check)
    id_ext = os.path.splitext(id_file.filename)[1].lower()
    if id_ext not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
        flash("Please upload a JPG, PNG, WebP, or PDF image of your ID.", "error")
        return redirect(url_for("vyvid.adult_id_verify_page", video_id=video_id))

    # Read the file to confirm it is non-empty — then DISCARD it immediately (privacy)
    id_file.stream.seek(0, os.SEEK_END)
    id_size = id_file.stream.tell()
    id_file.stream.seek(0)
    if id_size < 1024:  # under 1 KB is almost certainly not a real ID
        flash("The uploaded file appears to be empty or too small. Please upload a clear ID photo.", "error")
        return redirect(url_for("vyvid.adult_id_verify_page", video_id=video_id))
    # The ID stream is intentionally never written to disk.

    try:
        # Update user's DOB and mark as adult-content verified
        user.adult_verified = True
        user.adult_verified_at = datetime.utcnow()
        user.adult_verification_provider = "adult_content_id_upload"
        user.adult_verification_ref = f"vyvid-adult-video-{video_id}"
        user.date_of_birth = dob

        uv = UserVerification.query.filter_by(user_id=user.id).first()
        if not uv:
            uv = UserVerification(user_id=user.id)  # type: ignore[call-arg]
            db.session.add(uv)
        uv.id_verified              = True
        uv.id_verified_at           = datetime.utcnow()
        uv.id_review_status         = "approved"
        uv.id_document_url          = None   # NEVER stored — privacy protected
        uv.adult_content_verified   = True
        uv.adult_content_verified_at = datetime.utcnow()

        # Clear the flag on the video so it moves to admin review (not blocked by missing ID)
        video.adult_id_required = False
        video.needs_review      = True   # still needs human moderation review
        video.is_approved       = False  # stays off-platform until admin approves

        db.session.commit()

        flash(
            "Identity verified for adult content. Your video has been submitted for review "
            "and will go live once approved by our moderation team.",
            "success"
        )
        return redirect(url_for("vyvid.vyvid_watch", video_id=video_id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[vyvid] adult_id_verify_submit failed: {e}")
        flash("Verification failed. Please try again.", "error")
        return redirect(url_for("vyvid.adult_id_verify_page", video_id=video_id))
