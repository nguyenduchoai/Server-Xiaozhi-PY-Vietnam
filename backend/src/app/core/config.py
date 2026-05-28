import os
from enum import Enum

from pydantic import SecretStr
from pydantic_settings import BaseSettings
from starlette.config import Config

current_file_dir = os.path.dirname(os.path.realpath(__file__))
env_path = os.path.join(current_file_dir, "..", "..", ".env")
config = Config(env_path)


class AppSettings(BaseSettings):
    APP_NAME: str = config("APP_NAME", default="FastAPI app")
    APP_DESCRIPTION: str | None = config("APP_DESCRIPTION", default=None)
    APP_VERSION: str | None = config("APP_VERSION", default=None)
    LICENSE_NAME: str | None = config("LICENSE", default=None)
    CONTACT_NAME: str | None = config("CONTACT_NAME", default=None)
    CONTACT_EMAIL: str | None = config("CONTACT_EMAIL", default=None)


class CryptSettings(BaseSettings):
    SECRET_KEY: SecretStr = config("SECRET_KEY", cast=SecretStr)
    ALGORITHM: str = config("ALGORITHM", default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = config("REFRESH_TOKEN_EXPIRE_DAYS", default=7)


class DatabaseSettings(BaseSettings):
    pass


class SQLiteSettings(DatabaseSettings):
    SQLITE_URI: str = config("SQLITE_URI", default="./sql_app.db")
    SQLITE_SYNC_PREFIX: str = config("SQLITE_SYNC_PREFIX", default="sqlite:///")
    SQLITE_ASYNC_PREFIX: str = config(
        "SQLITE_ASYNC_PREFIX", default="sqlite+aiosqlite:///"
    )


class MySQLSettings(DatabaseSettings):
    MYSQL_USER: str = config("MYSQL_USER", default="username")
    MYSQL_PASSWORD: str = config("MYSQL_PASSWORD", default="password")
    MYSQL_SERVER: str = config("MYSQL_SERVER", default="localhost")
    MYSQL_PORT: int = config("MYSQL_PORT", default=5432)
    MYSQL_DB: str = config("MYSQL_DB", default="dbname")
    MYSQL_URI: str = (
        f"{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_SERVER}:{MYSQL_PORT}/{MYSQL_DB}"
    )
    MYSQL_SYNC_PREFIX: str = config("MYSQL_SYNC_PREFIX", default="mysql://")
    MYSQL_ASYNC_PREFIX: str = config("MYSQL_ASYNC_PREFIX", default="mysql+aiomysql://")
    MYSQL_URL: str | None = config("MYSQL_URL", default=None)


class PostgresSettings(DatabaseSettings):
    POSTGRES_USER: str = config("POSTGRES_USER", default="postgres")
    POSTGRES_PASSWORD: str = config("POSTGRES_PASSWORD", default="postgres")
    POSTGRES_SERVER: str = config("POSTGRES_SERVER", default="localhost")
    POSTGRES_PORT: int = config("POSTGRES_PORT", default=5432)
    POSTGRES_DB: str = config("POSTGRES_DB", default="postgres")
    POSTGRES_SYNC_PREFIX: str = config("POSTGRES_SYNC_PREFIX", default="postgresql://")
    POSTGRES_ASYNC_PREFIX: str = config(
        "POSTGRES_ASYNC_PREFIX", default="postgresql+asyncpg://"
    )
    POSTGRES_URI: str = (
        f"{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    POSTGRES_URL: str | None = config("POSTGRES_URL", default=None)


def _require_admin_password() -> str:
    """Bắt buộc ADMIN_PASSWORD trong env. Fail-fast nếu thiếu/yếu.

    Trước đây dùng default '!Ch4ng3Th1sP4ssW0rd!' công khai trong source — dẫn tới
    deployment quên đặt env sẽ public password. Từ v2.1 trở đi REQUIRED.
    """
    pw = config("ADMIN_PASSWORD", default=None)
    if not pw:
        raise RuntimeError(
            "ADMIN_PASSWORD environment variable is REQUIRED. "
            "Set a strong password (≥12 chars, mixed case + digit + symbol) "
            "in .env or via secrets manager. See MANUAL_ACTIONS.md."
        )
    if len(pw) < 12:
        raise RuntimeError(
            f"ADMIN_PASSWORD too short ({len(pw)} chars). Minimum 12 chars required."
        )
    return pw


class FirstUserSettings(BaseSettings):
    ADMIN_NAME: str = config("ADMIN_NAME", default="admin")
    ADMIN_EMAIL: str = config("ADMIN_EMAIL", default="admin@admin.com")
    ADMIN_USERNAME: str = config("ADMIN_USERNAME", default="admin")
    ADMIN_PASSWORD: str = _require_admin_password()


class TestSettings(BaseSettings):
    pass


class RedisCacheSettings(BaseSettings):
    REDIS_CACHE_HOST: str = config("REDIS_CACHE_HOST", default="localhost")
    REDIS_CACHE_PORT: int = config("REDIS_CACHE_PORT", default=6379)
    REDIS_PASSWORD: str = config("REDIS_PASSWORD", default="")
    REDIS_CACHE_URL: str = config(
        "REDIS_CACHE_URL", default=""
    )

    @property
    def redis_cache_url_resolved(self) -> str:
        if self.REDIS_CACHE_URL:
            return self.REDIS_CACHE_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_CACHE_HOST}:{self.REDIS_CACHE_PORT}"
        return f"redis://{self.REDIS_CACHE_HOST}:{self.REDIS_CACHE_PORT}"


class ClientSideCacheSettings(BaseSettings):
    CLIENT_CACHE_MAX_AGE: int = config("CLIENT_CACHE_MAX_AGE", default=60)


class RedisQueueSettings(BaseSettings):
    REDIS_QUEUE_HOST: str = config("REDIS_QUEUE_HOST", default="localhost")
    REDIS_QUEUE_PORT: int = config("REDIS_QUEUE_PORT", default=6379)
    REDIS_QUEUE_URL: str = config(
        "REDIS_QUEUE_URL", default=""
    )

    @property
    def redis_queue_url_resolved(self) -> str:
        if self.REDIS_QUEUE_URL:
            return self.REDIS_QUEUE_URL
        password = config("REDIS_PASSWORD", default="")
        if password:
            return f"redis://:{password}@{self.REDIS_QUEUE_HOST}:{self.REDIS_QUEUE_PORT}"
        return f"redis://{self.REDIS_QUEUE_HOST}:{self.REDIS_QUEUE_PORT}"


class EmbeddingSettings(BaseSettings):
    EMBEDDING_API_KEY: str = config("EMBEDDING_API_KEY", default="")
    EMBEDDING_BASE_URL: str = config(
        "EMBEDDING_BASE_URL", default="http://localhost:8000"
    )
    EMBEDDING_MODEL: str = config("EMBEDDING_MODEL", default="text-embedding-model")


class EnvironmentOption(Enum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentSettings(BaseSettings):
    ENVIRONMENT: EnvironmentOption = config(
        "ENVIRONMENT", default=EnvironmentOption.LOCAL
    )


class UploadSettings(BaseSettings):
    """Configuration for file uploads"""

    UPLOAD_DIR: str = config("UPLOAD_DIR", default="static/uploads/profiles")
    MAX_UPLOAD_SIZE: int = config(
        "MAX_UPLOAD_SIZE", cast=int, default=5 * 1024 * 1024
    )  # 5MB
    ALLOWED_IMAGE_EXTENSIONS: list[str] = ["jpeg", "jpg", "png", "webp"]


class CORSSettings(BaseSettings):
    """Configuration for CORS middleware"""

    CORS_ALLOW_ORIGINS: str = config("CORS_ALLOW_ORIGINS", default="")  # REQUIRED: Set in .env for production


class OpenMemorySettings(BaseSettings):
    """Cấu hình OpenMemory service cho Knowledge Base"""

    base_url: str = config("OPENMEMORY_BASE_URL", default="http://localhost:8080")
    api_key: str = config("OPENMEMORY_API_KEY", default="")
    timeout: int = config("OPENMEMORY_TIMEOUT", cast=int, default=30)
    enabled: bool = config("OPENMEMORY_ENABLED", cast=bool, default=True)


class MCPEndpointSettings(BaseSettings):
    """Cấu hình MCP Endpoint Server"""

    MCP_ENDPOINT_KEY: str = config("MCP_ENDPOINT_KEY", default="")
    MCP_ENDPOINT_PUBLIC_URL: str = config(
        "MCP_ENDPOINT_PUBLIC_URL", default="ws://localhost:8004"
    )


class VoiceSettings(BaseSettings):
    """Cấu hình Voice Cloning"""
    MAX_VOICES_PER_USER: int = config("MAX_VOICES_PER_USER", cast=int, default=10)
    MAX_VOICE_FILE_SIZE: int = config(
        "MAX_VOICE_FILE_SIZE", cast=int, default=10 * 1024 * 1024
    )  # 10MB
    VOICES_STORAGE_PATH: str = config(
        "VOICES_STORAGE_PATH", default="/app/data/backend/voices"
    )
    MIN_VOICE_DURATION: float = config(
        "MIN_VOICE_DURATION", cast=float, default=3.0
    )  # seconds
    MAX_VOICE_DURATION: float = config(
        "MAX_VOICE_DURATION", cast=float, default=30.0
    )  # seconds




class Settings(
    AppSettings,
    SQLiteSettings,
    PostgresSettings,
    CryptSettings,
    FirstUserSettings,
    TestSettings,
    RedisCacheSettings,
    ClientSideCacheSettings,
    RedisQueueSettings,
    EmbeddingSettings,
    EnvironmentSettings,
    UploadSettings,
    CORSSettings,
    MCPEndpointSettings,
    VoiceSettings,
):
    openmemory: OpenMemorySettings = OpenMemorySettings()


settings = Settings()

