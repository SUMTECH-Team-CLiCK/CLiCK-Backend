from pydantic_settings import BaseSettings, SettingsConfigDict
from datetime import timedelta
from pydantic import computed_field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # .env에서 읽힐 실제 필드들
    OPENAI_API_KEY: str
    DATABASE_URL: str
    # SECRET_KEY: str
    # REFRESH_SECRET_KEY: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    ALGORITHM: str= "HS256"

    # .env 로딩 이후의 파생값들 -> computed_field로 안전하게
    @computed_field(return_type=str)
    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return self.DATABASE_URL

    @computed_field(return_type=timedelta)
    @property
    def access_expires(self) -> timedelta:
        return timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)

    @computed_field(return_type=timedelta)
    @property
    def refresh_expires(self) -> timedelta:
        return timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)

settings = Settings()