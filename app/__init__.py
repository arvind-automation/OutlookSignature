from flask import Flask, jsonify

from app.config import Config
from app.extensions import db, migrate


def create_app(config_object=Config):
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401
    from app.routes.admin_routes import admin_bp
    from app.routes.api_routes import api_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.generator_routes import generator_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(generator_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
