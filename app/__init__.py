from flask import Flask
from .extensions import db, login_manager, migrate
from config import config
from . import models  # noqa: F401


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    from .main.routes import main_bp
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
