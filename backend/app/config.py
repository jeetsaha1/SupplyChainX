from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="sqlite:///./supplychainx.db")
    DB_URL: str | None = Field(default=None)
    SECRET_KEY: str = Field(default="change-me-in-environment")
    RPC_URL: str = Field(default="https://rpc-amoy.polygon.technology")
    WALLET_PRIVATE_KEY: str = Field(default="change-me-in-environment")
    CONTRACT_ADDRESS: str = Field(default="")
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

if settings.DB_URL is None:
    settings.DB_URL = settings.DATABASE_URL