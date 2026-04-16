from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.api.v1 import api_v1_blueprint
from app.schemas.share_schema import CreateShareSchema
from app.services.share_service import ShareService

create_share_schema = CreateShareSchema()


@api_v1_blueprint.route("/notes/<note_id>/share", methods=["POST"])
@jwt_required()
def share_note(note_id):

    current_user_id = get_jwt_identity()
    json_data = request.get_json()

    if not json_data:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Request body must be JSON",
            "status_code": 400,
        }), 400

    try:
        data = create_share_schema.load(json_data)
    except ValidationError as err:
        return jsonify({
            "error": "VALIDATION_ERROR",
            "message": err.messages,
            "status_code": 422,
        }), 422

    try:
        share = ShareService.share_note(
            note_id=note_id,
            owner_id=current_user_id,
            recipient_email=data["email"],
            permission=data["permission"],
        )
    except PermissionError as err:
        return jsonify({
            "error": "FORBIDDEN",
            "message": str(err),
            "status_code": 403,
        }), 403
    except ValueError as err:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": str(err),
            "status_code": 400,
        }), 400

    return jsonify({
        "message": "Note shared successfully",
        "share": share.to_dict(),
        "note": share.note.to_dict(),
    }), 201

@api_v1_blueprint.route("/notes/<note_id>/share/<share_id>", methods=["DELETE"])
@jwt_required()
def revoke_share(note_id, share_id):

    current_user_id = get_jwt_identity()

    try:
        ShareService.revoke_share(
            share_id=share_id,
            note_id=note_id,
            owner_id=current_user_id,
        )
    except PermissionError as err:
        return jsonify({
            "error": "FORBIDDEN",
            "message": str(err),
            "status_code": 403,
        }), 403
    except ValueError as err:
        return jsonify({
            "error": "NOT_FOUND",
            "message": str(err),
            "status_code": 404,
        }), 404

    return jsonify({"message": "Share revoked successfully"}), 200

@api_v1_blueprint.route("/shared", methods=["GET"])
@jwt_required()
def list_shared_notes():

    current_user_id = get_jwt_identity()
    shared_notes = ShareService.get_shared_with_me(user_id=current_user_id)

    return jsonify({
        "notes": [
            {
                **note.to_dict(include_content=True),
                "share_permission": permission.value,
            }
            for note, permission in shared_notes
        ],
    }), 200
