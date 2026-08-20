"""
Database connection and session management for V2Ray Aggregator.

Uses SQLAlchemy with SQLite backend and WAL mode for better concurrency.
"""
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


def get_database_path() -> Path:
    """
    Get the path to the SQLite database file.
    
    Returns:
        Path: Database file path
    """
    settings = get_settings()
    return Path(settings.database_path)


def create_engine_with_wal(database_path: Path) -> object:
    """
    Create SQLAlchemy engine with WAL mode enabled for better concurrency.
    
    Args:
        database_path: Path to SQLite database file
        
    Returns:
        SQLAlchemy engine
    """
    # Ensure parent directory exists
    database_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create connection string with WAL mode
    connection_string = f"sqlite:///{database_path}"
    
    engine = create_engine(
        connection_string,
        connect_args={
            "check_same_thread": False,  # Allow multi-threaded access
        },
        poolclass=StaticPool,  # SQLite doesn't need connection pooling
        echo=False,  # Set to True for SQL query logging
    )
    
    # Enable WAL mode for better concurrency
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.commit()
    
    return engine


# Global engine instance
_engine = None
_session_factory = None


def init_database() -> None:
    """Initialize database engine and session factory."""
    global _engine, _session_factory
    
    if _engine is None:
        database_path = get_database_path()
        _engine = create_engine_with_wal(database_path)
        _session_factory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_engine() -> object:
    """
    Get the database engine, initializing if necessary.
    
    Returns:
        SQLAlchemy engine
    """
    if _engine is None:
        init_database()
    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get the session factory, initializing if necessary.
    
    Returns:
        SQLAlchemy session factory
    """
    if _session_factory is None:
        init_database()
    return _session_factory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Yields:
        Session: SQLAlchemy session
        
    Example:
        with get_session() as session:
            session.add(model)
            session.commit()
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables() -> None:
    """Create all database tables from models."""
    from app.database.models import Base
    
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """Drop all database tables. Use with caution!"""
    from app.database.models import Base
    
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
