from app import create_app
from werkzeug.security import generate_password_hash

app, _ = create_app()
with app.app_context():
    from models import User
    users = User.query.all()
    if users:
        for u in users:
            print(f"  user: {u.username}, email: {u.email}, is_admin: {getattr(u, 'is_admin', False)}")
    else:
        print("No users - creating admin test user...")
        from __init__ import db
        pw = generate_password_hash("Test1234!", method="pbkdf2:sha256")
        admin = User(
            username="admin",
            email="admin@vybeflow.local",
            password_hash=pw,
            bio="Admin account",
        )
        try:
            admin.is_admin = True
        except Exception:
            pass
        db.session.add(admin)
        db.session.commit()
        print(f"  Created admin user: admin / Test1234!")
