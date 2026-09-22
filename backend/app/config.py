import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


# --------------------------------------------------
# Backend Base Directory
# --------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

# BASE_DIR = backend/app
BACKEND_DIR = os.path.dirname(BASE_DIR)

# --------------------------------------------------
# Settings
# --------------------------------------------------

class Settings:

    # ----------------------------------------------
    # Database
    # ----------------------------------------------

    DB_HOST = os.getenv(
        "DB_HOST",
        "localhost"
    )

    DB_PORT = os.getenv(
        "DB_PORT",
        "3306"
    )

    DB_USER = os.getenv(
        "DB_USER",
        "root"
    )

    DB_PASSWORD = os.getenv(
        "DB_PASSWORD",
        ""
    )

    DB_NAME = os.getenv(
        "DB_NAME",
        "task_knowledge_db"
    )

    # ----------------------------------------------
    # SQLAlchemy Database URL
    # ----------------------------------------------

    _encoded_user = quote_plus(
        DB_USER
    )

    _encoded_password = quote_plus(
        DB_PASSWORD
    )

    SQLALCHEMY_DATABASE_URL = (
        f"mysql+pymysql://"
        f"{_encoded_user}:"
        f"{_encoded_password}@"
        f"{DB_HOST}:"
        f"{DB_PORT}/"
        f"{DB_NAME}"
    )

    # ----------------------------------------------
    # JWT
    # ----------------------------------------------

    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY",
        "insecure_dev_secret"
    )

    JWT_ALGORITHM = os.getenv(
        "JWT_ALGORITHM",
        "HS256"
    )

    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "120"
        )
    )

    # ----------------------------------------------
    # File Storage
    # ----------------------------------------------

    UPLOAD_DIR = os.path.join(
        BACKEND_DIR,
        os.getenv(
            "UPLOAD_DIR",
            "uploads"
        )
    )

    VECTOR_STORE_DIR = os.path.join(
        BACKEND_DIR,
        os.getenv(
            "VECTOR_STORE_DIR",
            "vector_store"
        )
    )

    # ----------------------------------------------
    # Admin
    # ----------------------------------------------

    ADMIN_EMAIL = os.getenv(
        "ADMIN_EMAIL",
        "admin@example.com"
    )

    ADMIN_PASSWORD = os.getenv(
        "ADMIN_PASSWORD",
        "Admin@123"
    )


settings = Settings()


# --------------------------------------------------
# Create Required Directories
# --------------------------------------------------

os.makedirs(
    settings.UPLOAD_DIR,
    exist_ok=True
)

os.makedirs(
    settings.VECTOR_STORE_DIR,
    exist_ok=True
)