"""
Circles (Private Crews) — Blueprint
====================================
Create, manage, invite, and post inside private crew circles.
"""

from datetime import datetime
from flask import (
    Blueprint, request, session, redirect, url_for,
    render_template, flash, jsonify,
)
from __init__ import db

circles_bp = Blueprint("circles", __name__, url_prefix="/circles")


def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None
    return uid


# ---------------------------------------------------------------------------
# List all circles the current user belongs to + discover public ones
# ---------------------------------------------------------------------------
@circles_bp.get("/")
def circles_home():
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import Circle, User, circle_members

    user = User.query.get(uid)
    my_circles = user.circles if user else []

    # Public / discoverable circles the user hasn't joined
    discover = (
        Circle.query
        .filter(Circle.privacy == "public")
        .filter(~Circle.members.any(id=uid))
        .order_by(Circle.created_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "circles.html",
        my_circles=my_circles,
        discover=discover,
        current_user=user,
    )


# ---------------------------------------------------------------------------
# Create a new circle
# ---------------------------------------------------------------------------
@circles_bp.route("/create", methods=["GET", "POST"])
def create_circle():
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    if request.method == "POST":
        from models import Circle, User

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        privacy = request.form.get("privacy", "private").strip()
        vibe = request.form.get("vibe", "").strip()
        max_members = int(request.form.get("max_members", 50))

        if not name:
            flash("Circle name is required.", "error")
            return redirect(url_for("circles.create_circle"))

        circle = Circle(
            name=name,
            description=description,
            creator_id=uid,
            privacy=privacy,
            vibe=vibe,
            max_members=max_members,
        )
        creator = User.query.get(uid)
        circle.members.append(creator)
        db.session.add(circle)
        db.session.commit()

        flash(f"Circle '{name}' created! 🔥", "success")
        return redirect(url_for("circles.view_circle", circle_id=circle.id))

    return render_template("circle_create.html")


# ---------------------------------------------------------------------------
# View a circle + its posts
# ---------------------------------------------------------------------------
@circles_bp.get("/<int:circle_id>")
def view_circle(circle_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import Circle, CirclePost, User

    circle = Circle.query.get_or_404(circle_id)
    is_member = any(m.id == uid for m in circle.members)

    posts = []
    if is_member:
        posts = (
            CirclePost.query
            .filter_by(circle_id=circle_id)
            .order_by(CirclePost.created_at.desc())
            .limit(50)
            .all()
        )

    return render_template(
        "circle_view.html",
        circle=circle,
        posts=posts,
        is_member=is_member,
        current_user=User.query.get(uid),
    )


# ---------------------------------------------------------------------------
# Post inside a circle
# ---------------------------------------------------------------------------
@circles_bp.route("/<int:circle_id>/post", methods=["POST"])
def circle_post(circle_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import Circle, CirclePost

    circle = Circle.query.get_or_404(circle_id)
    if not any(m.id == uid for m in circle.members):
        flash("You must be a member to post.", "error")
        return redirect(url_for("circles.view_circle", circle_id=circle_id))

    content = request.form.get("content", "").strip()
    media_url = request.form.get("media_url", "").strip() or None

    if not content and not media_url:
        flash("Post can't be empty.", "error")
        return redirect(url_for("circles.view_circle", circle_id=circle_id))

    post = CirclePost(
        circle_id=circle_id,
        author_id=uid,
        content=content,
        media_url=media_url,
    )
    db.session.add(post)
    db.session.commit()
    flash("Posted to crew! 🔥", "success")
    return redirect(url_for("circles.view_circle", circle_id=circle_id))


# ---------------------------------------------------------------------------
# Invite a user to a circle
# ---------------------------------------------------------------------------
@circles_bp.route("/<int:circle_id>/invite", methods=["POST"])
def invite_member(circle_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import Circle, CircleInvite, User

    circle = Circle.query.get_or_404(circle_id)
    if not any(m.id == uid for m in circle.members):
        flash("Only crew members can invite.", "error")
        return redirect(url_for("circles.view_circle", circle_id=circle_id))

    username = request.form.get("username", "").strip()
    invitee = User.query.filter_by(username=username).first()
    if not invitee:
        flash("User not found.", "error")
        return redirect(url_for("circles.view_circle", circle_id=circle_id))

    if any(m.id == invitee.id for m in circle.members):
        flash(f"{username} is already in the crew.", "info")
        return redirect(url_for("circles.view_circle", circle_id=circle_id))

    existing = CircleInvite.query.filter_by(
        circle_id=circle_id, invitee_id=invitee.id, status="pending"
    ).first()
    if existing:
        flash("Invite already sent.", "info")
        return redirect(url_for("circles.view_circle", circle_id=circle_id))

    invite = CircleInvite(
        circle_id=circle_id,
        inviter_id=uid,
        invitee_id=invitee.id,
    )
    db.session.add(invite)
    db.session.commit()
    flash(f"Invited {username}! 📩", "success")
    return redirect(url_for("circles.view_circle", circle_id=circle_id))


# ---------------------------------------------------------------------------
# Accept / decline an invite
# ---------------------------------------------------------------------------
@circles_bp.route("/invite/<int:invite_id>/accept", methods=["POST"])
def accept_invite(invite_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import CircleInvite, Circle, User

    invite = CircleInvite.query.get_or_404(invite_id)
    if invite.invitee_id != uid:
        flash("Not your invite.", "error")
        return redirect(url_for("circles.circles_home"))

    circle = Circle.query.get(invite.circle_id)
    user = User.query.get(uid)
    circle.members.append(user)
    invite.status = "accepted"
    db.session.commit()
    flash(f"Joined {circle.name}! 🎉", "success")
    return redirect(url_for("circles.view_circle", circle_id=circle.id))


@circles_bp.route("/invite/<int:invite_id>/decline", methods=["POST"])
def decline_invite(invite_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import CircleInvite

    invite = CircleInvite.query.get_or_404(invite_id)
    if invite.invitee_id != uid:
        flash("Not your invite.", "error")
        return redirect(url_for("circles.circles_home"))

    invite.status = "declined"
    db.session.commit()
    flash("Invite declined.", "info")
    return redirect(url_for("circles.circles_home"))


# ---------------------------------------------------------------------------
# Join a public circle
# ---------------------------------------------------------------------------
@circles_bp.route("/<int:circle_id>/join", methods=["POST"])
def join_circle(circle_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import Circle, User

    circle = Circle.query.get_or_404(circle_id)
    if circle.privacy != "public":
        flash("This circle is invite-only.", "error")
        return redirect(url_for("circles.circles_home"))

    user = User.query.get(uid)
    if not any(m.id == uid for m in circle.members):
        circle.members.append(user)
        db.session.commit()
    flash(f"Joined {circle.name}! 🎉", "success")
    return redirect(url_for("circles.view_circle", circle_id=circle.id))


# ---------------------------------------------------------------------------
# Leave a circle
# ---------------------------------------------------------------------------
@circles_bp.route("/<int:circle_id>/leave", methods=["POST"])
def leave_circle(circle_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import Circle, User

    circle = Circle.query.get_or_404(circle_id)
    user = User.query.get(uid)
    if user in circle.members:
        circle.members.remove(user)
        db.session.commit()
    flash(f"Left {circle.name}.", "info")
    return redirect(url_for("circles.circles_home"))
