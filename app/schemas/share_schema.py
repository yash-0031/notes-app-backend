from marshmallow import Schema, fields, validate


class CreateShareSchema(Schema):
    email = fields.Email(
        required=True,
        error_messages={"required": "Email of the recipient is required"},
    )
    permission = fields.String(
        load_default="VIEWER",
        validate=validate.OneOf(["VIEWER", "EDITOR"]),
    )


class ShareResponseSchema(Schema):
    id = fields.String(dump_only=True)
    note_id = fields.String(dump_only=True)
    shared_with_user_id = fields.String(dump_only=True)
    shared_with_email = fields.String(dump_only=True)
    permission = fields.String()
    created_at = fields.DateTime()