from pydantic import BaseSettings


class Settings(BaseSettings):
    database_url: str = 'sqlite:///database.db'
    database_echo: bool = False


settings = Settings()
