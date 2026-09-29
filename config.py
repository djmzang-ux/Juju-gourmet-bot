from pydantic_settings import BaseSettings, SettingsConfigDict
from decimal import Decimal

class Settings(BaseSettings):
    bot_token: str
    admin_telegram_id: int
    database_url: str = "sqlite+aiosqlite:///./juju.db"

    mercadopago_access_token: str | None = None
    mercadopago_webhook_secret: str | None = None
    public_base_url: str | None = None

    store_name: str = "Juju Gourmet"
    delivery_fee: Decimal = Decimal("5.00")
    currency: str = "BRL"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
