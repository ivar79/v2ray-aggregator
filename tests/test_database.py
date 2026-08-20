"""
Unit tests for database models and repositories.
"""
import pytest
from datetime import datetime

from app.database.models import Channel, Config, ConfigOccurrence, CollectionRun, ConfigLifecycleState
from app.database.repository import ChannelRepository, ConfigRepository, ConfigOccurrenceRepository, CollectionRunRepository


class TestChannelRepository:
    """Test Channel repository operations."""
    
    def test_create_channel(self, test_database):
        """Test creating a new channel."""
        channel = ChannelRepository.create(
            test_database,
            telegram_id=123456789,
            username='testchannel',
            title='Test Channel',
            enabled=True,
        )
        
        assert channel.id is not None
        assert channel.telegram_id == 123456789
        assert channel.username == 'testchannel'
        assert channel.title == 'Test Channel'
        assert channel.enabled is True
        assert channel.last_message_id == 0
    
    def test_get_by_telegram_id(self, test_database, sample_channel):
        """Test retrieving channel by Telegram ID."""
        retrieved = ChannelRepository.get_by_telegram_id(test_database, 123456789)
        
        assert retrieved is not None
        assert retrieved.id == sample_channel.id
        assert retrieved.telegram_id == 123456789
    
    def test_get_by_username(self, test_database, sample_channel):
        """Test retrieving channel by username."""
        retrieved = ChannelRepository.get_by_username(test_database, 'testchannel')
        
        assert retrieved is not None
        assert retrieved.id == sample_channel.id
        assert retrieved.username == 'testchannel'
    
    def test_get_by_username_with_at(self, test_database, sample_channel):
        """Test retrieving channel by username with @ prefix."""
        retrieved = ChannelRepository.get_by_username(test_database, '@testchannel')
        
        assert retrieved is not None
        assert retrieved.id == sample_channel.id
    
    def test_update_channel(self, test_database, sample_channel):
        """Test updating channel fields."""
        updated = ChannelRepository.update(
            test_database,
            sample_channel,
            last_message_id=100,
            last_error="Test error",
        )
        
        assert updated.last_message_id == 100
        assert updated.last_error == "Test error"
    
    def test_get_all_enabled(self, test_database):
        """Test getting all enabled channels."""
        ChannelRepository.create(test_database, telegram_id=111, enabled=True)
        ChannelRepository.create(test_database, telegram_id=222, enabled=False)
        ChannelRepository.create(test_database, telegram_id=333, enabled=True)
        
        enabled = ChannelRepository.get_all_enabled(test_database)
        
        assert len(enabled) == 2
        assert all(c.enabled for c in enabled)


class TestConfigRepository:
    """Test Config repository operations."""
    
    def test_create_config(self, test_database):
        """Test creating a new configuration."""
        config = ConfigRepository.create(
            test_database,
            protocol='vmess',
            raw_config='vmess://test',
            normalized_config='vmess://normalized',
            config_hash='a' * 64,
            is_structurally_valid=True,
        )
        
        assert config.id is not None
        assert config.protocol == 'vmess'
        assert config.raw_config == 'vmess://test'
        assert config.normalized_config == 'vmess://normalized'
        assert config.config_hash == 'a' * 64
        assert config.is_structurally_valid is True
        assert config.lifecycle_state == ConfigLifecycleState.NEW.value
    
    def test_get_by_hash(self, test_database, sample_config):
        """Test retrieving config by hash."""
        retrieved = ConfigRepository.get_by_hash(test_database, sample_config.config_hash)
        
        assert retrieved is not None
        assert retrieved.id == sample_config.id
        assert retrieved.config_hash == sample_config.config_hash
    
    def test_update_lifecycle_state(self, test_database, sample_config):
        """Test updating lifecycle state."""
        updated = ConfigRepository.update_lifecycle_state(
            test_database,
            sample_config,
            ConfigLifecycleState.ACTIVE,
        )
        
        assert updated.lifecycle_state == ConfigLifecycleState.ACTIVE.value
    
    def test_update_validation(self, test_database, sample_config):
        """Test updating validation status."""
        updated = ConfigRepository.update_validation(
            test_database,
            sample_config,
            is_structurally_valid=False,
        )
        
        assert updated.is_structurally_valid is False
        assert updated.lifecycle_state == ConfigLifecycleState.INVALID.value
    
    def test_get_stats(self, test_database):
        """Test getting configuration statistics."""
        # Create sample configs
        ConfigRepository.create(
            test_database,
            protocol='vmess',
            raw_config='vmess://test1',
            normalized_config='vmess://norm1',
            config_hash='1' * 64,
            is_structurally_valid=True,
        )
        ConfigRepository.create(
            test_database,
            protocol='vless',
            raw_config='vless://test2',
            normalized_config='vless://norm2',
            config_hash='2' * 64,
            is_structurally_valid=True,
        )
        ConfigRepository.create(
            test_database,
            protocol='vmess',
            raw_config='vmess://test3',
            normalized_config='vmess://norm3',
            config_hash='3' * 64,
            is_structurally_valid=False,
        )
        
        stats = ConfigRepository.get_stats(test_database)
        
        assert stats['total_unique'] == 3
        assert stats['active_count'] == 2
        assert stats['invalid_count'] == 1
        assert stats['by_protocol']['vmess'] == 1
        assert stats['by_protocol']['vless'] == 1


class TestConfigOccurrenceRepository:
    """Test ConfigOccurrence repository operations."""
    
    def test_create_occurrence(self, test_database, sample_config, sample_channel):
        """Test creating a config occurrence."""
        occurrence = ConfigOccurrenceRepository.create(
            test_database,
            config_id=sample_config.id,
            channel_id=sample_channel.id,
            source_message_id=100,
            raw_occurrence='vmess://raw',
        )
        
        assert occurrence.id is not None
        assert occurrence.config_id == sample_config.id
        assert occurrence.channel_id == sample_channel.id
        assert occurrence.source_message_id == 100
    
    def test_get_existing_occurrence(self, test_database, sample_config, sample_channel):
        """Test checking if occurrence exists."""
        ConfigOccurrenceRepository.create(
            test_database,
            config_id=sample_config.id,
            channel_id=sample_channel.id,
            source_message_id=100,
        )
        
        existing = ConfigOccurrenceRepository.get_existing(
            test_database,
            config_id=sample_config.id,
            channel_id=sample_channel.id,
            source_message_id=100,
        )
        
        assert existing is not None
    
    def test_duplicate_occurrence_prevented(self, test_database, sample_config, sample_channel):
        """Test that duplicate occurrences are prevented by unique constraint."""
        ConfigOccurrenceRepository.create(
            test_database,
            config_id=sample_config.id,
            channel_id=sample_channel.id,
            source_message_id=100,
        )
        test_database.commit()
        
        # Attempting to create duplicate should raise integrity error
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            ConfigOccurrenceRepository.create(
                test_database,
                config_id=sample_config.id,
                channel_id=sample_channel.id,
                source_message_id=100,
            )
            test_database.commit()
        
        # Rollback to clean up the failed transaction state
        test_database.rollback()


class TestCollectionRunRepository:
    """Test CollectionRun repository operations."""
    
    def test_create_run(self, test_database):
        """Test creating a collection run."""
        run = CollectionRunRepository.create(test_database)
        
        assert run.id is not None
        assert run.status == "running"
        assert run.started_at is not None
        assert run.finished_at is None
    
    def test_update_run(self, test_database, sample_collection_run):
        """Test updating collection run fields."""
        updated = CollectionRunRepository.update(
            test_database,
            sample_collection_run,
            messages_scanned=100,
            configs_found=50,
            configs_added=30,
        )
        
        assert updated.messages_scanned == 100
        assert updated.configs_found == 50
        assert updated.configs_added == 30
    
    def test_complete_run(self, test_database, sample_collection_run):
        """Test marking collection run as completed."""
        completed = CollectionRunRepository.complete(
            test_database,
            sample_collection_run,
            status="completed",
        )
        
        assert completed.status == "completed"
        assert completed.finished_at is not None
    
    def test_get_latest_runs(self, test_database):
        """Test getting latest collection runs."""
        CollectionRunRepository.create(test_database)
        CollectionRunRepository.create(test_database)
        CollectionRunRepository.create(test_database)
        
        latest = CollectionRunRepository.get_latest(test_database, limit=2)
        
        assert len(latest) == 2
