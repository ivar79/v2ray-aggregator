"""
Pytest configuration and fixtures for V2Ray Aggregator tests.
"""
import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.database import init_database, create_tables, drop_tables, get_session
from app.database.models import Base


@pytest.fixture(scope="session")
def temp_database_path():
    """
    Create a temporary database file for testing.
    
    Yields:
        Path to temporary database file
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    yield db_path
    
    # Cleanup - attempt to remove but don't fail if locked
    try:
        if db_path.exists():
            db_path.unlink()
    except PermissionError:
        # File may be locked by WAL mode, this is acceptable for tests
        pass


@pytest.fixture(scope="session")
def test_settings(temp_database_path):
    """
    Create test settings with temporary database.
    
    Args:
        temp_database_path: Temporary database path fixture
        
    Returns:
        Settings instance for testing
    """
    # Override environment variables for testing
    os.environ['TELEGRAM_API_ID'] = '123456'
    os.environ['TELEGRAM_API_HASH'] = 'test_hash'
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test_bot_token'
    os.environ['GITHUB_TOKEN'] = 'test_github_token'
    os.environ['GITHUB_OWNER'] = 'test_owner'
    os.environ['GITHUB_REPO'] = 'test_repo'
    os.environ['CHANNEL_NAME'] = 'Test Channel'
    os.environ['CHANNEL_USERNAME'] = '@testchannel'
    os.environ['CHANNEL_ID'] = '123456789'
    os.environ['ADMIN_USER_IDS'] = '123456789,987654321'
    os.environ['DATABASE_PATH'] = str(temp_database_path)
    os.environ['DRY_RUN'] = 'true'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    
    from app.config import load_settings
    settings = load_settings()
    
    yield settings
    
    # Cleanup environment
    for key in [
        'TELEGRAM_API_ID', 'TELEGRAM_API_HASH', 'TELEGRAM_BOT_TOKEN',
        'GITHUB_TOKEN', 'GITHUB_OWNER', 'GITHUB_REPO',
        'CHANNEL_NAME', 'CHANNEL_USERNAME', 'CHANNEL_ID',
        'ADMIN_USER_IDS', 'DATABASE_PATH', 'DRY_RUN', 'LOG_LEVEL'
    ]:
        os.environ.pop(key, None)


@pytest.fixture(scope="function")
def test_database(test_settings):
    """
    Create and initialize test database for each test.
    
    Args:
        test_settings: Test settings fixture
        
    Yields:
        Database session
    """
    # Initialize database with test settings
    init_database()
    
    # Create tables
    create_tables()
    
    # Provide session
    with get_session() as session:
        yield session
    
    # Close connections before dropping
    from app.database.database import get_engine
    engine = get_engine()
    engine.dispose()
    
    # Drop tables after test
    drop_tables()


@pytest.fixture(scope="function")
def sample_channel(test_database):
    """
    Create a sample channel for testing.
    
    Args:
        test_database: Database session fixture
        
    Returns:
        Channel instance
    """
    from app.database.models import Channel
    from app.database.repository import ChannelRepository
    
    channel = ChannelRepository.create(
        test_database,
        telegram_id=123456789,
        username='testchannel',
        title='Test Channel',
        enabled=True,
    )
    return channel


@pytest.fixture(scope="function")
def sample_config(test_database):
    """
    Create a sample config for testing.
    
    Args:
        test_database: Database session fixture
        
    Returns:
        Config instance
    """
    import uuid
    from app.database.models import Config
    from app.database.repository import ConfigRepository
    
    # Use unique hash for each test to avoid conflicts
    unique_hash = uuid.uuid4().hex + 'a' * (64 - 32)  # 64 character hash
    
    config = ConfigRepository.create(
        test_database,
        protocol='vmess',
        raw_config='vmess://test',
        normalized_config='vmess://normalized_test',
        config_hash=unique_hash,
        is_structurally_valid=True,
    )
    return config


@pytest.fixture(scope="function")
def sample_collection_run(test_database):
    """
    Create a sample collection run for testing.
    
    Args:
        test_database: Database session fixture
        
    Returns:
        CollectionRun instance
    """
    from app.database.models import CollectionRun
    from app.database.repository import CollectionRunRepository
    
    run = CollectionRunRepository.create(test_database)
    return run
