import bcrypt
from flask_jwt_extended import create_access_token, create_refresh_token

from app import db
from app.models import User


class AuthService:

    @staticmethod
    def register(email: str, password: str, full_name: str = None) -> User:

        existing_user = User.query.filter_by(email=email.lower().strip()).first()
        if existing_user:
            raise ValueError("A user with this email already exists")
        
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)  # 12 rounds = good security/speed balance
        password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

        # Create the user
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash,
            full_name=full_name,
        )

        db.session.add(user)
        db.session.commit()

        return user

    @staticmethod
    def login(email: str, password: str) -> dict:

        user = User.query.filter_by(email=email.lower().strip()).first()

        if not user:
            raise ValueError("Invalid email or password")
        password_bytes = password.encode("utf-8")
        stored_hash = user.password_hash.encode("utf-8")

        if not bcrypt.checkpw(password_bytes, stored_hash):
            raise ValueError("Invalid email or password")
        
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict(),
        }

    @staticmethod
    def get_user_by_id(user_id: str) -> User:
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        return user