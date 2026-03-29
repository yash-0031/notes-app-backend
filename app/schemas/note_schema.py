from marshmallow import Schema, fields, validate


class CreateNoteSchema(Schema):
    title = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
        error_messages={"required": "Title is required"},
    )
    content = fields.String(
        allow_none=True,
        load_default=None,
    )

class UpdateNoteSchema(Schema):
    title = fields.String(
        validate=validate.Length(min=1, max=500),
    )
    content = fields.String(
        allow_none=True,
    )
    is_archived = fields.Boolean()


class NoteResponseSchema(Schema):
    id = fields.String(dump_only=True)
    user_id = fields.String(dump_only=True)
    title = fields.String()
    content = fields.String()
    is_archived = fields.Boolean()
    updated_at = fields.DateTime()
    created_at = fields.DateTime()


class NoteListQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(
        load_default=20,
        validate=validate.Range(min=1, max=100),
    )
    search = fields.String(load_default=None)
    is_archived = fields.Boolean(load_default=False)