from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    DB_HOST: str = Field("localhost", alias="DB_HOST")
    DB_PORT: int = Field(5432, alias="DB_PORT")
    DB_USER: str = Field("postgres", alias="DB_USER")
    DB_PASSWORD: str = Field("postgres", alias="DB_PASSWORD")
    DB_NAME: str = Field("rozetka_db", alias="DB_NAME")
    PROFILE_PATH: str = Field("./profile", alias="PROFILE_PATH")

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


config = Config()  # pyright: ignore[reportCallIssue]
