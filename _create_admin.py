from app import create_app
from werkzeug.security import generate_password_hash

app, _ = create_app()
with app.app_context():
    from models import User
    from __init__ import db
    # Create or update admin user
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        pw = generate_password_hash("AdminPass123!", method="pbkdf2:sha256")
        admin = User(
            username="admin",
            email="admin@vybeflow.local",
            password_hash=pw,
            bio="Admin account",
        )
        db.session.add(admin)
    try:
        admin.is_admin = True
    except Exception as e:
        print(f"Could not set is_admin: {e}")
    db.session.commit()
    print(f"Admin user ready: admin / AdminPass123!")

    # Also reset testuser password
    testuser = User.query.filter_by(username="testuser").first()
    if testuser:
        testuser.password_hash = generate_password_hash("Test1234!", method="pbkdf2:sha256")
        db.session.commit()
        print(f"testuser password reset to: Test1234!")
