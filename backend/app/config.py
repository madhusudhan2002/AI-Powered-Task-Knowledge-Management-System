import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
load_dotenv()
class Settings:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "task_knowledge_db")
    _encoded_user = quote_plus(DB_USER)
    _encoded_password = quote_plus(DB_PASSWORD)
    SQLALCHEMY_DATABASE_URL = (
        f"mysql+pymysql://{_encoded_user}:{_encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "insecure_dev_secret")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    VECTOR_STORE_DIR = os.getenv("VECTOR_STORE_DIR", "vector_store")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")
settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_STORE_DIR, exist_ok=True)