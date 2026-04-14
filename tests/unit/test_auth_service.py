from uuid import uuid4

import bcrypt
import pytest

from app.services.auth_service import AuthService


def test_register_success():
    user = AuthService.register(
        email="  Test@Email.COM  ",
        password="Password123",
        full_name="Test User",
    )

    assert user.email == "test@email.com"
    assert user.password_hash != "Password123"
    assert bcrypt.checkpw(b"Password123", user.password_hash.encode("utf-8"))


def test_register_duplicate_email():
    AuthService.register(
        email="duplicate@example.com",
        password="Password123",
        full_name="First User",
    )

    with pytest.raises(ValueError, match="A user with this email already exists"):
        AuthService.register(
            email="duplicate@example.com",
            password="Password123",
            full_name="Second User",
        )


def test_register_email_case_insensitive():
    user = AuthService.register(
        email="Test@Email.COM",
        password="Password123",
        full_name="Case User",
    )

    assert user.email == "test@email.com"


def test_login_success():
    AuthService.register(
        email="login@example.com",
        password="Password123",
        full_name="Login User",
    )

    result = AuthService.login(email="login@example.com", password="Password123")

    assert set(result) == {"access_token", "refresh_token", "user"}
    assert result["access_token"]
    assert result["refresh_token"]
    assert result["user"]["email"] == "login@example.com"
    assert result["user"]["full_name"] == "Login User"
    assert result["user"]["id"]
    assert result["user"]["created_at"]


@pytest.mark.parametrize(
    "email,password",
    [
        ("login@example.com", "WrongPass123"),
        ("missing@example.com", "Password123"),
    ],
)
def test_login_invalid_credentials(email, password):
    if email == "login@example.com":
        AuthService.register(
            email=email,
            password="Password123",
            full_name="Login User",
        )

    with pytest.raises(ValueError, match="Invalid email or password"):
        AuthService.login(email=email, password=password)


def test_get_user_by_id_success():
    user = AuthService.register(
        email="lookup@example.com",
        password="Password123",
        full_name="Lookup User",
    )

    found = AuthService.get_user_by_id(str(user.id))

    assert found.id == user.id
    assert found.email == "lookup@example.com"


def test_get_user_by_id_not_found():
    with pytest.raises(ValueError, match="User not found"):
        AuthService.get_user_by_id(str(uuid4()))
