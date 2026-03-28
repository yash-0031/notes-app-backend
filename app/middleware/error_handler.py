from flask import jsonify
from marshmallow import ValidationError


def register_error_handlers(app):
    """Register error handlers with the Flask app."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "error": "BAD_REQUEST",
            "message": str(error.description) if hasattr(error, 'description') else "Bad request",
            "status_code": 400,
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "error": "UNAUTHORIZED",
            "message": "Authentication required",
            "status_code": 401,
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "error": "FORBIDDEN",
            "message": "You do not have permission to access this resource",
            "status_code": 403,
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "NOT_FOUND",
            "message": "The requested resource was not found",
            "status_code": 404,
        }), 404

    @app.errorhandler(429)
    def rate_limited(error):
        return jsonify({
            "error": "RATE_LIMITED",
            "message": "Too many requests. Please slow down.",
            "status_code": 429,
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "Something went wrong on our end",
            "status_code": 500,
        }), 500

    @app.errorhandler(ValidationError)
    def validation_error(error):
        return jsonify({
            "error": "VALIDATION_ERROR",
            "message": error.messages,
            "status_code": 422,
        }), 422