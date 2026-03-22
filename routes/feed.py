from flask import Blueprint, render_template, session, url_for, redirect, request, jsonify
from datetime import datetime
import secrets
from types import SimpleNamespace
from sqlalchemy import func

feed_bp = Blueprint("feed", __name__)

# Try importing models, but don't completely hide failure
MODEL_IMPORT_ERROR = None
try:
    from __init__ import db
    from models import (Post, Reel, Story, User, Follow, VibePoint,
                        Reaction, ReactionPack, ReactionPackOwned,
                        VibeFusion, VerifiedCircle, CircleMember)
except Exception as e:
    MODEL_IMPORT_ERROR = e
    Post = Reel = Story = User = Follow = VibePoint = None
    Reaction = ReactionPack = ReactionPackOwned = None
    VibeFusion = VerifiedCircle = CircleMember = None
    db = None


@feed_bp.get("/feed")
def feed_page():
    # Require a logged-in user so the feed always shows a real
    # profile instead of a generic "Guest" placeholder.
    username = (session.get("username") or "").strip()
    if not username:
        return redirect(url_for("login"))

    # -------- current user view --------
    def _current_user_view():
        username = (session.get("username") or "").strip()

        avatar_url = session.get("avatar_url")
        if not avatar_url:
            avatar_url = url_for("static", filename="VFlogo_clean.png")

        bio = "VybeFlow member."
        account_type = "regular"
        trust_score = 50
        is_verified_human = False
        anonymous_posting_enabled = False

        display_name = username  # fallback

        # Only enrich from DB if user is logged in AND models exist
        if User is not None and username != "Guest":
            try:
                db_user = User.query.filter_by(username=username).first()
                if db_user:
                    avatar_url = getattr(db_user, "avatar_url", None) or avatar_url
                    bio = getattr(db_user, "bio", None) or bio
                    display_name = getattr(db_user, "display_name", None) or username
                    username = getattr(db_user, "username", None) or username
                    account_type = getattr(db_user, "account_type", "regular") or "regular"
                    trust_score = getattr(db_user, "trust_score", 50) or 50
                    is_verified_human = getattr(db_user, "is_verified_human", False) or False
                    anonymous_posting_enabled = getattr(db_user, "anonymous_posting_enabled", False) or False
            except Exception as e:
                # keep feed rendering, but don't die
                print(f"[feed] user lookup failed: {e}")

        return SimpleNamespace(username=username, display_name=display_name, bio=bio, avatar_url=avatar_url, account_type=account_type,
                               trust_score=trust_score, is_verified_human=is_verified_human, anonymous_posting_enabled=anonymous_posting_enabled)

    current_user = _current_user_view()

    # Check if user has AI Assist enabled
    ai_assist_enabled = False
    if User is not None and username:
        try:
            _ai_user = User.query.filter_by(username=username).first()
            if _ai_user:
                ai_assist_enabled = bool(getattr(_ai_user, "ai_assist", False))
        except Exception:
            pass

    posts, reels, users, stories = [], [], [], []

    # Optional: surface model import error in console so you actually know
    if MODEL_IMPORT_ERROR:
        print(f"[feed] models import failed: {MODEL_IMPORT_ERROR}")

    # -------- posts --------
    if Post is not None:
        try:
            # ── Feed Mode Logic ──
            feed_mode = session.get("feed_mode", "trending")
            if User is not None and username:
                try:
                    _fm_user = User.query.filter_by(username=username).first()
                    if _fm_user and hasattr(_fm_user, "feed_mode"):
                        feed_mode = getattr(_fm_user, "feed_mode", "trending") or "trending"
                except Exception:
                    pass

            if feed_mode == "chronological":
                # Pure chronological — newest first
                base_q = Post.query.order_by(Post.created_at.desc()) if hasattr(Post, "created_at") else Post.query.order_by(Post.id.desc())
            elif feed_mode == "friends":
                # Friends only — posts from people user follows
                friend_ids = []
                if Follow is not None and User is not None and username:
                    try:
                        _f_user = User.query.filter_by(username=username).first()
                        if _f_user:
                            friend_ids = [f.following_id for f in Follow.query.filter_by(follower_id=_f_user.id).all()]
                            friend_ids.append(_f_user.id)  # include own posts
                    except Exception as e:
                        print(f"[feed] friends lookup failed: {e}")
                if friend_ids:
                    base_q = Post.query.filter(Post.author_id.in_(friend_ids)).order_by(Post.id.desc())
                else:
                    base_q = Post.query.order_by(Post.id.desc())  # fallback if no friends
            else:
                # Trending — order by engagement (likes + comments + views)
                base_q = Post.query.order_by(
                    (Post.like_count + Post.comment_count + Post.view_count).desc()
                    if hasattr(Post, "like_count") and hasattr(Post, "view_count")
                    else Post.id.desc()
                )

            # ── Adult content filtering ──
            # Check if the logged-in user is a verified adult
            _pref_adult = False
            if User is not None and username:
                try:
                    _u = User.query.filter_by(username=username).first()
                    if _u:
                        _pref_adult = (
                            getattr(_u, "adult_verified", False)
                            and not getattr(_u, "adult_access_revoked", False)
                        )
                except Exception:
                    pass

            if not _pref_adult:
                # Hide ALL adult posts from unverified users
                if hasattr(Post, "is_adult"):
                    base_q = base_q.filter(
                        (Post.is_adult == False)  # noqa: E712
                    )
            else:
                # Verified adults still can't see unapproved adult posts
                if hasattr(Post, "is_adult") and hasattr(Post, "needs_review"):
                    base_q = base_q.filter(
                        (Post.is_adult == False)  # noqa: E712
                        | (
                            (Post.needs_review == False)  # noqa: E712
                            & (Post.approved_at != None)  # noqa: E711
                        )
                    )

            posts = base_q.limit(50).all()
        except Exception as e:
            print(f"[feed] posts query failed: {e}")

    # -------- reels --------
    if Reel is not None:
        try:
            # some older DBs may not have author_id/created_at; fall back
            if hasattr(Reel, "created_at"):
                reels = Reel.query.order_by(Reel.created_at.desc()).limit(20).all()
            else:
                reels = Reel.query.order_by(Reel.id.desc()).limit(20).all()
        except Exception as e:
            # never break the feed if the reel schema is out of date
            print(f"[feed] reels query failed: {e}")
            reels = []

    # -------- users --------
    if User is not None:
        try:
            users_q = User.query.limit(8).all()
            users = [{
                "username": u.username,
                "email": getattr(u, "email", "") or "",
                "is_friend": False
            } for u in users_q]
        except Exception as e:
            print(f"[feed] users query failed: {e}")

    # -------- stories (no N+1 queries) --------
    if Story is not None:
        try:
            # Pull a recent batch then filter by expiry in Python,
            # because Story.expires_at is a method, not a column.
            raw_stories = (
                Story.query
                .order_by(Story.id.desc())
                .limit(50)
                .all()
            )

            # Filter out expired stories safely
            filtered_stories = []
            for s in raw_stories:
                expires_attr = getattr(s, "expires_at", None)
                if callable(expires_attr):
                    try:
                        exp_val = expires_attr()
                        if isinstance(exp_val, datetime) and exp_val > datetime.utcnow():
                            filtered_stories.append(s)
                    except Exception:
                        # If expiry calculation fails, skip that story
                        continue
                else:
                    # If no method, just keep the record as-is
                    filtered_stories.append(s)

            # Collect author ids safely
            author_ids = []
            for s in filtered_stories:
                aid = getattr(s, "author_id", None) or getattr(s, "user_id", None)
                if aid:
                    author_ids.append(aid)

            authors_by_id = {}
            if User is not None and author_ids:
                try:
                    # single query for authors
                    author_rows = User.query.filter(User.id.in_(author_ids)).all()
                    authors_by_id = {a.id: a for a in author_rows}
                except Exception as e:
                    print(f"[feed] author batch query failed: {e}")

            current_username = (session.get("username") or "").strip()

            def _normalize_vis(value: str) -> str:
                key = (value or "Public").strip().lower()
                if key in ("public", "everyone"):
                    return "Public"
                if key in ("followers", "follower"):
                    return "Followers"
                if key in ("only me", "only_me", "private", "draft"):
                    return "Only Me"
                return "Public"

            for s in filtered_stories:
                aid = getattr(s, "author_id", None) or getattr(s, "user_id", None)
                author = authors_by_id.get(aid) if aid else None
                username = getattr(author, "username", None) or "User"

                # Story visibility: show Public to all, Followers to logged-in followers,
                # and Only Me only to the owner.
                vis_raw = getattr(s, "visibility", "Public")
                vis = _normalize_vis(vis_raw)
                if vis == "Only Me" and username != current_username:
                    continue

                media_url = getattr(s, "media_url", None) or ""
                media_type = getattr(s, "media_type", None) or (
                    "video" if str(media_url).lower().endswith((".mp4", ".mov", ".webm", ".m4v")) else "image"
                )

                # Compute ISO expiry if available
                expires_iso = ""
                expires_attr = getattr(s, "expires_at", None)
                if callable(expires_attr):
                    try:
                        exp_val = expires_attr()
                        if isinstance(exp_val, datetime):
                            expires_iso = exp_val.isoformat()
                    except Exception:
                        expires_iso = ""
                elif isinstance(expires_attr, datetime):
                    expires_iso = expires_attr.isoformat()

                stories.append({
                    "id": getattr(s, "id", None),
                    "username": username,
                    "title": username,
                    "caption": getattr(s, "caption", "") or "",
                    "media_type": media_type,
                    "media_url": media_url,
                    "music_track": getattr(s, "music_track", "") or "",
                    "music_preview_url": getattr(s, "music_preview_url", "") or "",
                    "music_file_url": getattr(s, "music_file_url", "") or "",
                    "story_font": getattr(s, "story_font", "") or "neon",
                    "expires_at": expires_iso,
                })
        except Exception as e:
            print(f"[feed] stories query failed: {e}")

    return render_template(
        "feed.html",
        posts=posts,
        reels=reels,
        current_user=current_user,
        users=users,
        stories=stories,
        notification_counts={"messages": 0, "live_invites": 0},
        friend_usernames=[],
        active_theme={},
        ai_assist_enabled=ai_assist_enabled,
    )


# ═══════════════════════════════════════════════════
# VIBE-BASED FEED FILTERING
# ═══════════════════════════════════════════════════

@feed_bp.post("/api/feed/vibe-filter")
def vibe_filter():
    """Filter feed posts by vibe/mood tag."""
    data = request.get_json(silent=True) or {}
    vibe = (data.get("vibe") or "all").strip().lower()

    if Post is None:
        return jsonify({"posts": [], "vibe": vibe})

    try:
        if vibe == "all":
            q = Post.query.order_by(Post.id.desc()).limit(50)
        else:
            q = Post.query.filter(
                (Post.vibe_tag == vibe) if hasattr(Post, "vibe_tag") else True
            ).order_by(Post.id.desc()).limit(50)
        posts = q.all()
        return jsonify({"posts": [p.id for p in posts], "vibe": vibe, "count": len(posts)})
    except Exception as e:
        print(f"[feed] vibe filter failed: {e}")
        return jsonify({"posts": [], "vibe": vibe, "error": str(e)})


@feed_bp.post("/api/feed/smart-filter")
def smart_filter():
    """Smart filter: friends, interest groups, or trending."""
    data = request.get_json(silent=True) or {}
    filter_type = (data.get("filter") or "all").strip().lower()
    username = (session.get("username") or "").strip()

    if Post is None or not username:
        return jsonify({"filter": filter_type, "post_ids": []})

    try:
        if filter_type == "friends":
            friend_ids = []
            if Follow is not None and User is not None:
                u = User.query.filter_by(username=username).first()
                if u:
                    friend_ids = [f.following_id for f in Follow.query.filter_by(follower_id=u.id).all()]
                    friend_ids.append(u.id)
            posts = Post.query.filter(Post.author_id.in_(friend_ids)).order_by(Post.id.desc()).limit(50).all() if friend_ids else []
        elif filter_type == "trending":
            posts = Post.query.order_by((Post.like_count + Post.comment_count + Post.view_count).desc()).limit(50).all()
        else:
            posts = Post.query.order_by(Post.id.desc()).limit(50).all()

        return jsonify({"filter": filter_type, "post_ids": [p.id for p in posts], "count": len(posts)})
    except Exception as e:
        return jsonify({"filter": filter_type, "post_ids": [], "error": str(e)})


# ═══════════════════════════════════════════════════
# VIBE POINTS (KARMA) SYSTEM
# ═══════════════════════════════════════════════════

@feed_bp.post("/api/comments/<int:comment_id>/vibe-point")
def award_vibe_point(comment_id):
    """Award a vibe point to a comment (helpful, funny, insightful, supportive)."""
    username = (session.get("username") or "").strip()
    if not username:
        return jsonify({"error": "Login required"}), 401

    data = request.get_json(silent=True) or {}
    category = (data.get("category") or "helpful").strip().lower()
    if category not in ("helpful", "funny", "insightful", "supportive"):
        category = "helpful"

    if VibePoint is None or User is None or db is None:
        return jsonify({"error": "Feature unavailable"}), 500

    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        vp = VibePoint(user_id=user.id, comment_id=comment_id, awarded_by=user.id, points=1, category=category)
        db.session.add(vp)
        db.session.commit()

        total = db.session.query(func.sum(VibePoint.points)).filter_by(comment_id=comment_id).scalar() or 0
        return jsonify({"ok": True, "total_points": total, "category": category})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@feed_bp.get("/api/users/<username>/vibe-points")
def get_user_vibe_points(username):
    """Get total vibe points for a user."""
    if VibePoint is None or User is None:
        return jsonify({"total": 0, "breakdown": {}})

    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"total": 0, "breakdown": {}})

        total = db.session.query(func.sum(VibePoint.points)).filter_by(user_id=user.id).scalar() or 0
        breakdown = {}
        for cat in ("helpful", "funny", "insightful", "supportive"):
            count = db.session.query(func.sum(VibePoint.points)).filter_by(user_id=user.id, category=cat).scalar() or 0
            breakdown[cat] = count

        return jsonify({"total": total, "breakdown": breakdown, "username": username})
    except Exception as e:
        return jsonify({"total": 0, "breakdown": {}, "error": str(e)})


# ─────────────────────────── Phase 2 API Endpoints ───────────────────────────

# ── Helper: get current user from session ──
def _current_user():
    username = (session.get("username") or "").strip()
    if not username or User is None:
        return None
    return User.query.filter_by(username=username).first()


# ═══════════════════════ Reaction Packs ═══════════════════════

@feed_bp.post("/api/reaction-packs")
def create_reaction_pack():
    """Create a custom reaction pack (max 8 emojis)."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    if ReactionPack is None:
        return jsonify({"error": "Feature unavailable"}), 503

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    emojis = data.get("emojis", [])
    rarity = (data.get("rarity") or "common").strip().lower()

    if not name or len(name) > 60:
        return jsonify({"error": "Pack name required (max 60 chars)"}), 400
    if not emojis or not isinstance(emojis, list) or len(emojis) > 8:
        return jsonify({"error": "Provide 1-8 emojis"}), 400
    if rarity not in ("common", "rare", "epic", "legendary"):
        rarity = "common"

    import json
    pack = ReactionPack(
        creator_id=user.id,
        name=name,
        emojis_json=json.dumps(emojis[:8]),
        rarity=rarity,
    )
    db.session.add(pack)
    db.session.commit()
    return jsonify({"ok": True, "pack_id": pack.id, "name": name, "rarity": rarity})


@feed_bp.get("/api/reaction-packs")
def list_reaction_packs():
    """List available reaction packs (public marketplace)."""
    if ReactionPack is None:
        return jsonify([])

    import json
    packs = ReactionPack.query.order_by(ReactionPack.created_at.desc()).limit(50).all()
    result = []
    for p in packs:
        creator = User.query.get(p.creator_id)
        result.append({
            "id": p.id,
            "name": p.name,
            "emojis": json.loads(p.emojis_json) if p.emojis_json else [],
            "rarity": p.rarity,
            "trade_price": p.trade_price,
            "times_traded": p.times_traded,
            "uses_count": p.uses_count,
            "creator": getattr(creator, "username", "unknown"),
        })
    return jsonify(result)


@feed_bp.get("/api/reaction-packs/mine")
def my_reaction_packs():
    """List packs owned by current user."""
    user = _current_user()
    if not user or ReactionPackOwned is None:
        return jsonify([])

    import json
    owned = ReactionPackOwned.query.filter_by(user_id=user.id).all()
    result = []
    for o in owned:
        pack = ReactionPack.query.get(o.pack_id)
        if pack:
            result.append({
                "id": pack.id,
                "name": pack.name,
                "emojis": json.loads(pack.emojis_json) if pack.emojis_json else [],
                "rarity": pack.rarity,
                "acquired_via": o.acquired_via,
            })
    return jsonify(result)


@feed_bp.post("/api/reaction-packs/<int:pack_id>/acquire")
def acquire_reaction_pack(pack_id):
    """Acquire (trade/collect) a reaction pack."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    if ReactionPack is None:
        return jsonify({"error": "Feature unavailable"}), 503

    pack = ReactionPack.query.get(pack_id)
    if not pack:
        return jsonify({"error": "Pack not found"}), 404

    existing = ReactionPackOwned.query.filter_by(user_id=user.id, pack_id=pack_id).first()
    if existing:
        return jsonify({"error": "Already owned"}), 409

    owned = ReactionPackOwned(user_id=user.id, pack_id=pack_id, acquired_via="traded")
    pack.times_traded = (pack.times_traded or 0) + 1
    db.session.add(owned)
    db.session.commit()
    return jsonify({"ok": True, "pack_id": pack_id, "acquired_via": "traded"})


# ═══════════════════════ Vibe Fusion ═══════════════════════

@feed_bp.post("/api/posts/<int:post_id>/vibe-fusion")
def create_vibe_fusion(post_id):
    """Create a vibe fusion combo on a post (3 emojis combined)."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    if VibeFusion is None:
        return jsonify({"error": "Feature unavailable"}), 503

    data = request.get_json(silent=True) or {}
    emojis = data.get("emojis", [])
    label = (data.get("label") or "").strip()

    if not isinstance(emojis, list) or len(emojis) < 2 or len(emojis) > 5:
        return jsonify({"error": "Provide 2-5 emojis for a fusion"}), 400

    combo_key = "".join(sorted(emojis))
    # Determine tier based on combo length
    tier = "basic"
    if len(emojis) >= 4:
        tier = "legendary"
    elif len(emojis) >= 3:
        tier = "rare"

    existing = VibeFusion.query.filter_by(post_id=post_id, combo_key=combo_key, user_id=user.id).first()
    if existing:
        return jsonify({"error": "You already fused this combo here"}), 409

    fusion = VibeFusion(
        post_id=post_id,
        user_id=user.id,
        combo_key=combo_key,
        combo_label=label[:60] if label else None,
        combo_tier=tier,
    )
    db.session.add(fusion)
    db.session.commit()
    return jsonify({
        "ok": True, "fusion_id": fusion.id,
        "combo_key": combo_key, "combo_label": fusion.combo_label,
        "combo_tier": tier, "emojis": emojis,
    })


@feed_bp.get("/api/posts/<int:post_id>/vibe-fusions")
def get_vibe_fusions(post_id):
    """List all vibe fusions on a post."""
    if VibeFusion is None:
        return jsonify([])

    fusions = VibeFusion.query.filter_by(post_id=post_id).order_by(VibeFusion.created_at.desc()).limit(30).all()
    result = []
    for f in fusions:
        creator = User.query.get(f.user_id) if f.user_id else None
        result.append({
            "id": f.id,
            "combo_key": f.combo_key,
            "combo_label": f.combo_label,
            "combo_tier": f.combo_tier,
            "creator": getattr(creator, "username", "anon"),
            "created_at": f.created_at.isoformat() if f.created_at else None,
        })
    return jsonify(result)


# ═══════════════════════ Verified Circles ═══════════════════════

@feed_bp.post("/api/circles/create")
def create_circle():
    """Create a verified circle (private crew feed)."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    if VerifiedCircle is None:
        return jsonify({"error": "Feature unavailable"}), 503

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    max_members = min(int(data.get("max_members", 50)), 200)

    if not name or len(name) > 80:
        return jsonify({"error": "Circle name required (max 80 chars)"}), 400

    invite_code = secrets.token_urlsafe(8)
    circle = VerifiedCircle(
        name=name,
        description=description[:200] if description else None,
        creator_id=user.id,
        invite_code=invite_code,
        max_members=max_members,
    )
    db.session.add(circle)
    db.session.flush()

    # Creator auto-joins as 'creator' role
    member = CircleMember(circle_id=circle.id, user_id=user.id, role="creator")
    db.session.add(member)
    db.session.commit()
    return jsonify({
        "ok": True, "circle_id": circle.id,
        "name": name, "invite_code": invite_code,
    })


@feed_bp.post("/api/circles/<invite_code>/join")
def join_circle(invite_code):
    """Join a verified circle via invite code."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    if VerifiedCircle is None:
        return jsonify({"error": "Feature unavailable"}), 503

    circle = VerifiedCircle.query.filter_by(invite_code=invite_code, is_active=True).first()
    if not circle:
        return jsonify({"error": "Invalid or inactive invite code"}), 404

    existing = CircleMember.query.filter_by(circle_id=circle.id, user_id=user.id).first()
    if existing:
        return jsonify({"error": "Already a member"}), 409

    member_count = CircleMember.query.filter_by(circle_id=circle.id).count()
    if member_count >= (circle.max_members or 50):
        return jsonify({"error": "Circle is full"}), 403

    member = CircleMember(circle_id=circle.id, user_id=user.id, role="member")
    db.session.add(member)
    db.session.commit()
    return jsonify({"ok": True, "circle_id": circle.id, "circle_name": circle.name})


@feed_bp.get("/api/circles/mine")
def my_circles():
    """List circles the current user belongs to."""
    user = _current_user()
    if not user or CircleMember is None:
        return jsonify([])

    memberships = CircleMember.query.filter_by(user_id=user.id).all()
    result = []
    for m in memberships:
        circle = VerifiedCircle.query.get(m.circle_id)
        if circle:
            count = CircleMember.query.filter_by(circle_id=circle.id).count()
            result.append({
                "id": circle.id,
                "name": circle.name,
                "description": circle.description,
                "role": m.role,
                "invite_code": circle.invite_code if m.role in ("creator", "admin") else None,
                "member_count": count,
                "max_members": circle.max_members,
            })
    return jsonify(result)


@feed_bp.get("/api/circles/<int:circle_id>/feed")
def circle_feed(circle_id):
    """Get posts from a verified circle (only members can view)."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    if CircleMember is None:
        return jsonify({"error": "Feature unavailable"}), 503

    member = CircleMember.query.filter_by(circle_id=circle_id, user_id=user.id).first()
    if not member:
        return jsonify({"error": "Not a member of this circle"}), 403

    circle = VerifiedCircle.query.get(circle_id)
    if not circle or not circle.is_active:
        return jsonify({"error": "Circle not found"}), 404

    # Get posts from all circle members
    member_ids = [m.user_id for m in CircleMember.query.filter_by(circle_id=circle_id).all()]
    posts = Post.query.filter(Post.user_id.in_(member_ids)).order_by(Post.created_at.desc()).limit(50).all()

    result = []
    for p in posts:
        author = User.query.get(p.user_id)
        result.append({
            "id": p.id,
            "caption": p.caption,
            "image_url": getattr(p, "image_url", None),
            "video_url": getattr(p, "video_url", None),
            "vibe_tag": getattr(p, "vibe_tag", None),
            "micro_vibe": getattr(p, "micro_vibe", None),
            "author": getattr(author, "username", "unknown"),
            "avatar_url": getattr(author, "avatar_url", None),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return jsonify(result)


# ═══════════════════════ Gangsta Alias / Pseudonym ═══════════════════════

@feed_bp.post("/api/users/gangsta-alias")
def set_gangsta_alias():
    """Set or update the user's gangsta alias (pseudonym)."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401

    data = request.get_json(silent=True) or {}
    alias = (data.get("alias") or "").strip()

    if not alias or len(alias) > 80:
        return jsonify({"error": "Alias required (max 80 chars)"}), 400

    # Check uniqueness
    existing = User.query.filter(User.gangsta_alias == alias, User.id != user.id).first()
    if existing:
        return jsonify({"error": "Alias already taken"}), 409

    user.gangsta_alias = alias
    db.session.commit()
    return jsonify({"ok": True, "alias": alias})


@feed_bp.get("/api/users/gangsta-alias")
def get_gangsta_alias():
    """Get current user's gangsta alias."""
    user = _current_user()
    if not user:
        return jsonify({"alias": None})
    return jsonify({"alias": getattr(user, "gangsta_alias", None)})


# ═══════════════════════ Reaction Intensity (3D Smileys) ═══════════════════════

@feed_bp.post("/api/posts/<int:post_id>/react")
def react_to_post(post_id):
    """React to a post with an emoji at a given intensity (1-5 for 3D animation)."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    if Reaction is None:
        return jsonify({"error": "Feature unavailable"}), 503

    data = request.get_json(silent=True) or {}
    emoji = (data.get("emoji") or "").strip()
    intensity = max(1, min(5, int(data.get("intensity", 1))))

    if not emoji:
        return jsonify({"error": "Emoji required"}), 400

    existing = Reaction.query.filter_by(post_id=post_id, user_id=user.id).first()
    if existing:
        existing.emoji = emoji
        existing.intensity = intensity
    else:
        reaction = Reaction(post_id=post_id, user_id=user.id, emoji=emoji, intensity=intensity)
        db.session.add(reaction)

    db.session.commit()

    # Return aggregated reactions for this post
    reactions = Reaction.query.filter_by(post_id=post_id).all()
    agg = {}
    for r in reactions:
        if r.emoji not in agg:
            agg[r.emoji] = {"count": 0, "max_intensity": 0}
        agg[r.emoji]["count"] += 1
        agg[r.emoji]["max_intensity"] = max(agg[r.emoji]["max_intensity"], r.intensity or 1)

    return jsonify({"ok": True, "reactions": agg})
