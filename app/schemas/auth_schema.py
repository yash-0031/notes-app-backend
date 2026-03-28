from marshmallow import Schema, fields, validate, validates, ValidationError

class RegisterSchema(Schema):
    email = fields.Email(
        required=True,
        error_messages={"required": "Email is required"},
    )

    password = fields.String(
        required=True,
        validate=validate.Length(
            min=8,
            error="Password must be at least 8 characters",
        ),
        load_only=True,
    )

    full_name = fields.String(
        validate=validate.Length(max=100),
        load_only=True,
    )

    @validates("password")
    def validate_password_strength(self, value):

        if value.isdigit():
            raise ValidationError("Password cannot be all numbers")
        if value.isalpha():
            raise ValidationError("Password must contain at least one number")


class LoginSchema(Schema):

    email = fields.Email(
        required=True,
        error_messages={"required": "Email is required"},
    )

    password = fields.String(
        required=True,
        error_messages={"required": "Password is required"},
        load_only=True,
    )


class RefreshSchema(Schema):

    refresh_token = fields.String(
        required=True,
        error_messages={"required": "Refresh token is required"},
    )