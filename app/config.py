import os
from pydantic_settings import BaseSettings
from typing import ClassVar, Optional, Union

from app.services.Click import ClickPaymentProvider


class Settings(BaseSettings):
    # Database
    # Fallback to local SQLite for fresh setups; override with DATABASE_URL in .env
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    # Fix for Heroku: translate legacy scheme to SQLAlchemy-compatible
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # JWT
    secret_key: str = "gj589tujfj39if094fkvmi3jtju359im3u8hf1qsiodacr89rf3rijwcm3uwi"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # EnvironmentJWT_EXPIRES_IN
    environment: str = os.getenv("NODE_ENV", "development")
    port: int = int(os.getenv("PORT", 8000))

    # External Services
    eskiz_email: Optional[str] = "fayzullindmr@gmail.com"
    eskiz_password: Optional[str] = "rlPJjmkaqRvZshRoNpcIiCFtC5GiNzI7k7YNe8fs"
    eskiz_token: Optional[str] = ""

    deepl_api_key: Optional[str] = os.getenv("DEEPL_API_KEY")

    click_service_id: Optional[str] = os.getenv("CLICK_SERVICE_ID")
    click_merchant_id: Optional[str] = os.getenv("CLICK_MERCHANT_ID")
    click_secret_key: Optional[str] = os.getenv("CLICK_SECRET_KEY")
    click_merchant_user_id: Optional[str] = os.getenv("CLICK_MERCHANT_USER_ID")
    click_api_url: Optional[str] = os.getenv("CLICK_API_URL", "https://api.click.uz/v2")

    # Frontend URL
    frontend_url: str = "https://freya-admin.vercel.app"

    # Eskiz SMS
    eskiz_base_url: str = "https://notify.eskiz.uz/api"

    # File upload
    upload_path: str = "uploads/"
    max_file_size: int = 5242880  # 5 MB

    # Telegram Bot
    bot_secret_key: Optional[str] = os.getenv("BOT_SECRET_KEY")

    SUPERADMIN_EMAIL: Optional[Union[str, int, bool, None]] = "superadmin@localhost"
    SUPERADMIN_PASSWORD: Optional[Union[str, int, bool, None]] = "superadminpassword"
    SUPERADMIN_USERNAME: Optional[Union[str, int, bool, None]] = "superadmin"
    SUPERADMIN_FIRST_NAME: Optional[Union[str, int, bool, None]] = "Super"
    SUPERADMIN_LAST_NAME: Optional[Union[str, int, bool, None]] = "Admin"
    SUPERADMIN_PHONE: Optional[Union[str, int, bool, None]] = "+1234567890"
    SUPERADMIN_IS_ACTIVE: Optional[Union[str, int, bool, None]] = "true"
    SUPERADMIN_IS_SUPERUSER: Optional[Union[str, int, bool, None]] = "true"
    SUPERADMIN_IS_VERIFIED: Optional[Union[str, int, bool, None]] = "true"

    AMOUNT_FOR_PREMIUM: Optional[Union[str, int, bool, None]] = 1000 # so'm
    AMOUNT_FOR_PER_POST: Optional[Union[str, int, bool, None]] = 1500 # so'm
    click_provider: ClassVar[ClickPaymentProvider]  = ClickPaymentProvider(
        merchant_id="44558",
        merchant_service_id="80178",
        merchant_user_id="61876",
        secret_key="j4qMFKcdBIYS",
    )


    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
