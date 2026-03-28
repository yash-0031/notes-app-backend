import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/noteshare"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    RATELIMIT_STORAGE_URI = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB max upload size

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/noteshare_test"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=5)  # Short-lived for fast tests

class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_ECHO = False

config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}