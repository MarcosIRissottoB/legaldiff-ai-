from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import src.config as _config

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    pass


def get_engine() -> Engine:
    """Retorna el engine singleton. Se crea lazy para no fallar al import."""
    global _engine
    if _engine is None:
        _engine = create_engine(_config.DATABASE_URL)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Retorna el session factory singleton."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(), autocommit=False, autoflush=False
        )
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """Dependency de FastAPI para obtener una sesión de DB."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
