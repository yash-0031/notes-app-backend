from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api.v1 import api_v1_blueprint
from app.services.notes_service import NotesService
from app.utils.pdf_parser import extract_text_from_pdf


@api_v1_blueprint.route("/upload", methods=["POST"])
@jwt_required()
def upload_pdf():

    current_user_id = get_jwt_identity()
    if "file" not in request.files:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "No file provided. Use 'file' as the form field name.",
            "status_code": 400,
        }), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "No file selected",
            "status_code": 400,
        }), 400
    
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Only PDF files are supported",
            "status_code": 400,
        }), 400
    
    try:
        text_content = extract_text_from_pdf(file)

        if not text_content.strip():
            return jsonify({
                "error": "BAD_REQUEST",
                "message": "Could not extract text from PDF. It may be scanned/image-based.",
                "status_code": 400,
            }), 400

        title = file.filename.rsplit(".", 1)[0]  # Remove .pdf extension
        note = NotesService.create_note(
            user_id=current_user_id,
            title=f"PDF: {title}",
            content=text_content,
        )

    except Exception as err:
        return jsonify({
            "error": "PROCESSING_ERROR",
            "message": f"Failed to process PDF: {str(err)}",
            "status_code": 500,
        }), 500

    return jsonify({
        "message": "PDF processed successfully",
        "note": note.to_dict(),
    }), 201