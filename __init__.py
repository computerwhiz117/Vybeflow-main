"""
VybeFlow - Social Media Platform for Urban Artists
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration
    from config import Config
    app.config.from_object(Config)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    # Existing blueprints (if any)
    try:
        from .main import main_bp
        app.register_blueprint(main_bp)
    except ImportError:
        pass
    try:
        from vybeflow_loginpage.src.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
    except ImportError:
        pass
    try:
        from vybeflow_loginpage.src.routes.messaging import messaging_bp
        app.register_blueprint(messaging_bp, url_prefix='/messaging')
    except ImportError:
        pass
    try:
        from music_api import bp as music_bp
        app.register_blueprint(music_bp)
    except ImportError:
        pass

    # Register posts_api blueprint
    from routes.posts_api import posts_api
    app.register_blueprint(posts_api)

    return app