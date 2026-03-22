"""
Anti-Fake Account Verification — Blueprint
============================================
Phone verification, optional ID verification, and trust badges.
"""

import random
import string
from datetime import datetime, timedelta
from flask import (
    Blueprint, request, session, redirect, url_for,
    render_template, flash, jsonify,
)
from __init__ import db

verification_bp = Blueprint("verification", __name__, url_prefix="/verification")


def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None
    return uid


def _generate_code(length=6):
    """Generate a numeric verification code."""
    return "".join(random.choices(string.digits, k=length))


# ---------------------------------------------------------------------------
# Verification dashboard
# ---------------------------------------------------------------------------
@verification_bp.get("/")
def verification_home():
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import User, UserVerification

    user = User.query.get(uid)
    verification = UserVerification.query.filter_by(user_id=uid).first()

    return render_template(
        "verification.html",
        user=user,
        verification=verification,
    )


# ---------------------------------------------------------------------------
# Phone verification – Step 1: Send code
# ---------------------------------------------------------------------------
@verification_bp.route("/phone/send", methods=["POST"])
def phone_send_code():
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import UserVerification

    phone = request.form.get("phone", "").strip()
    if not phone or len(phone) < 7:
        flash("Please enter a valid phone number.", "error")
        return redirect(url_for("verification.verification_home"))

    verification = UserVerification.query.filter_by(user_id=uid).first()
    if not verification:
        verification = UserVerification(user_id=uid)
        db.session.add(verification)

    code = _generate_code()
    verification.phone_number = phone
    verification.phone_code = code
    verification.phone_code_expires = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()

    # In production, send SMS via Twilio/etc. For now, flash it.
    print(f"[VybeFlow Verify] Code for {phone}: {code}")
    flash(f"Verification code sent! (Demo: {code})", "success")
    return redirect(url_for("verification.verification_home"))


# ---------------------------------------------------------------------------
# Phone verification – Step 2: Verify code
# ---------------------------------------------------------------------------
@verification_bp.route("/phone/verify", methods=["POST"])
def phone_verify_code():
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import UserVerification

    code = request.form.get("code", "").strip()
    verification = UserVerification.query.filter_by(user_id=uid).first()

    if not verification or not verification.phone_code:
        flash("No pending verification. Send a code first.", "error")
        return redirect(url_for("verification.verification_home"))

    if verification.phone_code_expires and datetime.utcnow() > verification.phone_code_expires:
        flash("Code expired. Please request a new one.", "error")
        return redirect(url_for("verification.verification_home"))

    if code != verification.phone_code:
        flash("Invalid code. Try again.", "error")
        return redirect(url_for("verification.verification_home"))

    verification.phone_verified = True
    verification.phone_verified_at = datetime.utcnow()
    verification.phone_code = None
    verification.phone_code_expires = None

    # Award trust badge
    if verification.trust_badge == "none":
        verification.trust_badge = "phone_verified"
        verification.badge_awarded_at = datetime.utcnow()

    db.session.commit()
    flash("Phone verified! ✅ Trust badge awarded.", "success")
    return redirect(url_for("verification.verification_home"))


# ---------------------------------------------------------------------------
# ID verification – Upload document
# ---------------------------------------------------------------------------
@verification_bp.route("/id/submit", methods=["POST"])
def id_submit():
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import UserVerification
    import os
    from werkzeug.utils import secure_filename
    from flask import current_app

    verification = UserVerification.query.filter_by(user_id=uid).first()
    if not verification:
        verification = UserVerification(user_id=uid)
        db.session.add(verification)

    file = request.files.get("id_document")
    if not file or not file.filename:
        flash("Please upload a government-issued ID.", "error")
        return redirect(url_for("verification.verification_home"))

    # Save the document securely
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "id_verification")
    os.makedirs(upload_dir, exist_ok=True)

    filename = secure_filename(f"id_{uid}_{file.filename}")
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    verification.id_document_url = f"/static/uploads/id_verification/{filename}"
    verification.id_review_status = "pending"
    db.session.commit()

    flash("ID submitted for review. You'll be notified once verified. 📋", "success")
    return redirect(url_for("verification.verification_home"))


# ---------------------------------------------------------------------------
# Admin: Approve / reject ID verification
# ---------------------------------------------------------------------------
@verification_bp.route("/id/review/<int:verification_id>", methods=["POST"])
def id_review(verification_id):
    uid = _require_login()
    if uid is None:
        return redirect(url_for("login"))

    from models import User, UserVerification

    admin = User.query.get(uid)
    if not admin or not admin.is_admin:
        flash("Admin only.", "error")
        return redirect(url_for("verification.verification_home"))

    action = request.form.get("action", "").strip()
    verification = UserVerification.query.get_or_404(verification_id)

    if action == "approve":
        verification.id_verified = True
        verification.id_verified_at = datetime.utcnow()
        verification.id_review_status = "approved"
        verification.trust_badge = "id_verified"
        verification.badge_awarded_at = datetime.utcnow()
        flash("ID approved. ✅", "success")
    elif action == "reject":
        verification.id_review_status = "rejected"
        flash("ID rejected.", "info")
    else:
        flash("Invalid action.", "error")

    db.session.commit()
    return redirect(url_for("verification.verification_home"))


# ---------------------------------------------------------------------------
# API: Get trust badge for a user
# ---------------------------------------------------------------------------
@verification_bp.get("/badge/<int:user_id>")
def get_badge(user_id):
    from models import UserVerification

    v = UserVerification.query.filter_by(user_id=user_id).first()
    if not v:
        return jsonify({"badge": "none", "phone_verified": False, "id_verified": False})

    return jsonify({
        "badge": v.trust_badge or "none",
        "phone_verified": v.phone_verified,
        "id_verified": v.id_verified,
    })
