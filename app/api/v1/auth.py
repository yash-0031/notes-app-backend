from flask import request, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    create_access_token,
)
from flask_limiter import Limiter
from marshmallow import ValidationError

from app.api.v1 import api_v1_blueprint
from app.schemas.auth_schema import RegisterSchema, LoginSchema
from app.services.auth_service import AuthService
from app import limiter

register_schema = RegisterSchema()
login_schema = LoginSchema()

@api_v1_blueprint.route("/auth/register", methods=["POST"])
@limiter.limit("10/hour")  # Prevent spam account creation
def register():

    json_data = request.get_json()

    if not json_data:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Request body must be JSON",
            "status_code": 400,
        }), 400
    
    try:
        data = register_schema.load(json_data)
    except ValidationError as err:
        return jsonify({
            "error": "VALIDATION_ERROR",
            "message": err.messages,
            "status_code": 422,
        }), 422
    
    try:
        user = AuthService.register(
            email=data["email"],
            password=data["password"],
            full_name=data.get("full_name"),
        )
    except ValueError as err:
        return jsonify({
            "error": "CONFLICT",
            "message": str(err),
            "status_code": 409,
        }), 409
    
    return jsonify({
        "message": "Account created successfully",
        "user": user.to_dict(),
    }), 201 

@api_v1_blueprint.route("/auth/login", methods=["POST"])
@limiter.limit("5/minute")  # Prevent brute-force password attacks
def login():

    json_data = request.get_json()

    if not json_data:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Request body must be JSON",
            "status_code": 400,
        }), 400

    try:
        data = login_schema.load(json_data)
    except ValidationError as err:
        return jsonify({
            "error": "VALIDATION_ERROR",
            "message": err.messages,
            "status_code": 422,
        }), 422

    try:
        result = AuthService.login(
            email=data["email"],
            password=data["password"],
        )
    except ValueError as err:
        return jsonify({
            "error": "UNAUTHORIZED",
            "message": str(err),
            "status_code": 401,
        }), 401

    return jsonify(result), 200


@api_v1_blueprint.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)  # This route requires a REFRESH token

def refresh():

    current_user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user_id)

    return jsonify({
        "access_token": new_access_token,
    }), 200

@api_v1_blueprint.route("/auth/me", methods=["GET"])
@jwt_required()  # This route requires a valid ACCESS token

def get_current_user():

    current_user_id = get_jwt_identity()

    try:
        user = AuthService.get_user_by_id(current_user_id)
    except ValueError:
        return jsonify({
            "error": "NOT_FOUND",
            "message": "User not found",
            "status_code": 404,
        }), 404

    return jsonify({"user": user.to_dict()}), 200