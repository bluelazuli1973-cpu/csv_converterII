from flask import Flask
from .extensions import db, login_manager, migrate
from . import models  # noqa: F401


def create_app():
    app = Flask(__name__)

    # Simple dev config (we can move to config.py later)
    app.config["SECRET_KEY"] = "CHANGE_ME_TO_A_RANDOM_SECRET"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bi.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    from .auth.auth_routes import auth_bp
    from .ingest.ingest_routes import ingest_bp
    from .analytics.analytics_routes import analytics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(ingest_bp)
    app.register_blueprint(analytics_bp)

    # Create tables automatically for MVP (later: use migrations)
    with app.app_context():
        db.create_all()

    return app
