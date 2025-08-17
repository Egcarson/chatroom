import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


env = os.getenv("ENV", "local")

if env == "local":
    env_file = ".env.local"

else:
    env_file = ".env.docker"


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str

    model_config=SettingsConfigDict(
        env_file=env_file,
        extra="ignore"
    )


@lru_cache
def get_setttings():
    return Settings()

Config = get_setttings()