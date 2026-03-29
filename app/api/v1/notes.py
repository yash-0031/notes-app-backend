from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.api.v1 import api_v1_blueprint
from app.schemas.note_schema import (
    CreateNoteSchema,
    UpdateNoteSchema,
    NoteListQuerySchema,
)
from app.services.notes_service import NotesService

create_note_schema = CreateNoteSchema()
update_note_schema = UpdateNoteSchema()
list_query_schema = NoteListQuerySchema()

@api_v1_blueprint.route("/notes", methods=["GET"])
@jwt_required()
def list_notes():

    current_user_id = get_jwt_identity()
    try:
        params = list_query_schema.load(request.args)
    except ValidationError as err:
        return jsonify({
            "error": "VALIDATION_ERROR",
            "message": err.messages,
            "status_code": 422,
        }), 422

    result = NotesService.list_notes(
        user_id=current_user_id,
        page=params["page"],
        per_page=params["per_page"],
        search=params.get("search"),
        is_archived=params["is_archived"],
    )

    return jsonify(result), 200

@api_v1_blueprint.route("/notes", methods=["POST"])
@jwt_required()
def create_note():

    current_user_id = get_jwt_identity()
    json_data = request.get_json()

    if not json_data:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Request body must be JSON",
            "status_code": 400,
        }), 400

    try:
        data = create_note_schema.load(json_data)
    except ValidationError as err:
        return jsonify({
            "error": "VALIDATION_ERROR",
            "message": err.messages,
            "status_code": 422,
        }), 422

    note = NotesService.create_note(
        user_id=current_user_id,
        title=data["title"],
        content=data.get("content"),
    )

    return jsonify({
        "message": "Note created successfully",
        "note": note.to_dict(),
    }), 201

@api_v1_blueprint.route("/notes/<note_id>", methods=["GET"])
@jwt_required()
def get_note(note_id):

    current_user_id = get_jwt_identity()

    try:
        note = NotesService.get_note(
            note_id=note_id,
            user_id=current_user_id,
        )
    except PermissionError:
        return jsonify({
            "error": "FORBIDDEN",
            "message": "You do not have access to this note",
            "status_code": 403,
        }), 403
    except ValueError as err:
        return jsonify({
            "error": "NOT_FOUND",
            "message": str(err),
            "status_code": 404,
        }), 404

    return jsonify({"note": note.to_dict()}), 200

@api_v1_blueprint.route("/notes/<note_id>", methods=["PUT"])
@jwt_required()
def update_note(note_id):

    current_user_id = get_jwt_identity()
    json_data = request.get_json()

    if not json_data:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Request body must be JSON",
            "status_code": 400,
        }), 400

    try:
        data = update_note_schema.load(json_data)
    except ValidationError as err:
        return jsonify({
            "error": "VALIDATION_ERROR",
            "message": err.messages,
            "status_code": 422,
        }), 422

    try:
        note = NotesService.update_note(
            note_id=note_id,
            user_id=current_user_id,
            **data,
        )
    except PermissionError:
        return jsonify({
            "error": "FORBIDDEN",
            "message": "You do not have permission to edit this note",
            "status_code": 403,
        }), 403
    except ValueError as err:
        return jsonify({
            "error": "NOT_FOUND",
            "message": str(err),
            "status_code": 404,
        }), 404

    return jsonify({
        "message": "Note updated successfully",
        "note": note.to_dict(),
    }), 200

@api_v1_blueprint.route("/notes/<note_id>", methods=["DELETE"])
@jwt_required()
def delete_note(note_id):

    current_user_id = get_jwt_identity()

    try:
        NotesService.archive_note(
            note_id=note_id,
            user_id=current_user_id,
        )
    except PermissionError:
        return jsonify({
            "error": "FORBIDDEN",
            "message": "Only the note owner can delete it",
            "status_code": 403,
        }), 403
    except ValueError as err:
        return jsonify({
            "error": "NOT_FOUND",
            "message": str(err),
            "status_code": 404,
        }), 404

    return jsonify({
        "message": "Note archived successfully",
    }), 200