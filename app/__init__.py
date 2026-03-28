from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_marshmallow import Marshmallow

from config import config_map

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
ma = Marshmallow()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_name=None):
    import os
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_map[config_name])
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)
    CORS(app)  # Allow cross-origin requests (needed for mobile apps)
    limiter.init_app(app)

    from app.api.v1 import api_v1_blueprint
    app.register_blueprint(api_v1_blueprint, url_prefix="/api/v1")
    from app.middleware.error_handler import register_error_handlers
    register_error_handlers(app)

    @app.route("/api/v1/health")
    def health_check():
        return {"status": "healthy", "version": "1.0.0"}, 200

    return app
