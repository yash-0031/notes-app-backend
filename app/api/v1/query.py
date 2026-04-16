from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError

from app.api.v1 import api_v1_blueprint
from app.services.query_service import QueryService


class QuerySchema(Schema):
    question = fields.String(
        required=True,
        validate=validate.Length(min=3, max=1000),
        error_messages={"required": "A question is required"},
    )
    top_k = fields.Integer(
        load_default=5,
        validate=validate.Range(min=1, max=20),
    )


query_schema = QuerySchema()


@api_v1_blueprint.route("/query/status", methods=["GET"])
@jwt_required()
def query_index_status():

    current_user_id = get_jwt_identity()

    try:
        result = QueryService.get_index_status(user_id=current_user_id)
    except Exception as err:
        return jsonify({
            "error": "QUERY_STATUS_ERROR",
            "message": f"Failed to load query status: {str(err)}",
            "status_code": 500,
        }), 500

    return jsonify(result), 200

@api_v1_blueprint.route("/query", methods=["POST"])
@jwt_required()
def query_notes():

    current_user_id = get_jwt_identity()
    json_data = request.get_json()

    if not json_data:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Request body must be JSON",
            "status_code": 400,
        }), 400

    try:
        data = query_schema.load(json_data)
    except ValidationError as err:
        return jsonify({
            "error": "VALIDATION_ERROR",
            "message": err.messages,
            "status_code": 422,
        }), 422

    try:
        result = QueryService.query(
            user_id=current_user_id,
            question=data["question"],
            top_k=data["top_k"],
        )
    except Exception as err:
        return jsonify({
            "error": "QUERY_ERROR",
            "message": f"Failed to process query: {str(err)}",
            "status_code": 500,
        }), 500

    return jsonify(result), 200
