import functools

from sqlalchemy.future import Engine
from sqlmodel import Session, create_engine

from watney.settings import settings


@functools.cache
def get_engine(uri: str, echo: bool = False) -> Engine:
    return create_engine(uri, echo=echo)


def get_engine_from_settings() -> Engine:
    return get_engine(settings.database_url, settings.database_echo)


@functools.cache
def get_session() -> Session:
    return Session(get_engine_from_settings())


__all__ = ["get_session"]
