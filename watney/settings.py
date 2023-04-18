from pydantic import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://watney:watney@postgres/watney"
    database_echo: bool = False


settings = Settings()
