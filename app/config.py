import os
from pydantic_settings import BaseSettings
from typing import Optional, Union


class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://user:password@localhost/freya_db"
    )

    # JWT
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Environment
    environment: str = os.getenv("NODE_ENV", "development")
    port: int = int(os.getenv("PORT", 8000))

    # External Services
    eskiz_email: Optional[str] = os.getenv("ESKIZ_EMAIL")
    eskiz_password: Optional[str] = os.getenv("ESKIZ_PASSWORD")
    eskiz_token: Optional[str] = os.getenv("ESKIZ_TOKEN")

    deepl_api_key: Optional[str] = os.getenv("DEEPL_API_KEY")

    click_service_id: Optional[str] = os.getenv("CLICK_SERVICE_ID")
    click_merchant_id: Optional[str] = os.getenv("CLICK_MERCHANT_ID")
    click_secret_key: Optional[str] = os.getenv("CLICK_SECRET_KEY")
    click_merchant_user_id: Optional[str] = os.getenv("CLICK_MERCHANT_USER_ID")
    click_api_url: Optional[str] = os.getenv("CLICK_API_URL", "https://api.click.uz/v2")

    # Frontend URL
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Eskiz SMS
    eskiz_base_url: str = os.getenv("ESKIZ_BASE_URL", "https://notify.eskiz.uz/api")

    # File upload
    upload_path: str = os.getenv("UPLOAD_PATH", "uploads/")
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    SUPERADMIN_EMAIL: Optional[Union[str, int, bool, None]] = (
        os.getenv("SUPERADMIN_EMAIL", "") or None
    )
    SUPERADMIN_PASSWORD: Optional[Union[str, int, bool, None]] = (
        os.getenv("SUPERADMIN_PASSWORD", "") or None
    )
    SUPERADMIN_USERNAME: Optional[Union[str, int, bool, None]] = (
        os.getenv("SUPERADMIN_USERNAME", "") or None
    )
    SUPERADMIN_FIRST_NAME: Optional[Union[str, int, bool, None]] = (
        os.getenv("SUPERADMIN_FIRST_NAME", "") or None
    )
    SUPERADMIN_LAST_NAME: Optional[Union[str, int, bool, None]] = (
        os.getenv("SUPERADMIN_LAST_NAME", "") or None
    )
    SUPERADMIN_PHONE: Optional[Union[str, int, bool, None]] = (
        os.getenv("SUPERADMIN_PHONE", "") or None
    )
    SUPERADMIN_IS_ACTIVE: Optional[Union[str, int, bool, None]] = (
        os.getenv("SUPERADMIN_IS_ACTIVE", "") or None
    )
    SUPERADMIN_IS_SUPERUSER: Optional[Union[str, int, bool, None]] = (
        os.getenv("SUPERADMIN_IS_SUPERUSER", "") or None
    )
    SUPERADMIN_IS_VERIFIED: Optional[Union[str, int, bool, None]] = (
        os.getenv("SUPERADMIN_IS_VERIFIED", "") or None
    )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
