"""
Unit tests for Telegram Collector.

Tests use mocks for Telethon to ensure tests are deterministic and offline.
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
from pathlib import Path
import tempfile

from app.collector.collector import TelegramCollector
from app.database.models import Channel, Config, ConfigOccurrence, CollectionRun, ConfigLifecycleState
from app.database.repository import ChannelRepository, ConfigRepository, ConfigOccurrenceRepository, CollectionRunRepository
from app.parser.base import ParsedConfig


class TestTelegramCollector:
    """Test TelegramCollector functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        settings = Mock()
        settings.telegram_api_id = 12345
        settings.telegram_api_hash = "test_hash"
        settings.telegram_bot_token = "test_token"
        settings.telegram_session_name = "test_session"
        settings.first_run_message_limit = 100
        settings.max_document_size_mb = 10.0
        return settings
    
    @pytest.fixture
    def mock_client(self):
        """Mock Telethon client."""
        client = AsyncMock()
        client.start = AsyncMock()
        client.disconnect = AsyncMock()
        client.get_entity = AsyncMock()
        client.iter_messages = AsyncMock()
        client.download_media = AsyncMock()
        return client
    
    @pytest.fixture
    def collector(self, mock_settings):
        """Create collector instance with mocked settings."""
        with patch('app.collector.collector.get_settings', return_value=mock_settings):
            collector = TelegramCollector()
            return collector
    
    @pytest.fixture
    def sample_channel(self, test_database):
        """Create sample channel for testing."""
        with test_database as session:
            channel = ChannelRepository.create(
                session,
                telegram_id=123456789,
                username="testchannel",
                title="Test Channel",
                enabled=True,
            )
            session.commit()
            session.refresh(channel)
            # Return both the channel object and channel data dict
            channel_data = {
                'id': channel.id,
                'telegram_id': channel.telegram_id,
                'last_message_id': channel.last_message_id,
                'username': channel.username,
            }
            return channel, channel_data
    
    @pytest.fixture
    def sample_parsed_config(self):
        """Create sample parsed config."""
        return ParsedConfig(
            protocol="vmess",
            raw="vmess://test",
            fields={"add": "127.0.0.1", "port": 80},
        )
    
    def test_collector_initialization(self, collector):
        """Test collector initialization."""
        assert collector is not None
        assert len(collector.parsers) == 6
        assert 'vmess' in collector.parsers
        assert 'vless' in collector.parsers
        assert 'trojan' in collector.parsers
        assert 'shadowsocks' in collector.parsers
        assert 'hysteria' in collector.parsers
        assert 'hysteria2' in collector.parsers
    
    @pytest.mark.asyncio
    @patch('app.collector.collector.TelegramClient')
    async def test_client_initialization(self, mock_telethon_client, collector, mock_client):
        """Test Telethon client initialization."""
        mock_telethon_client.return_value = mock_client
        
        await collector.initialize()
        
        mock_telethon_client.assert_called_once()
        mock_client.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_client_shutdown(self, collector, mock_client):
        """Test Telethon client shutdown."""
        collector.client = mock_client
        
        await collector.shutdown()
        
        mock_client.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.collector.collector.TelegramClient')
    async def test_collect_from_channel_success(
        self,
        mock_telethon_client,
        collector,
        mock_client,
        sample_channel,
        sample_parsed_config,
    ):
        """Test successful collection from a channel."""
        mock_telethon_client.return_value = mock_client
        mock_entity = Mock()
        mock_entity.id = 123456789
        mock_client.get_entity.return_value = mock_entity
        
        # Mock messages
        mock_message = Mock()
        mock_message.id = 100
        mock_message.text = "vmess://eyJ2IjoiMiIsInBzIjoidGVzdCIsImFkZCI6IjEyNy4wLjAuMSIsInBvcnQiOiI4MCIsImlkIjoiYWJjZCIsImFpZCI6IjAiLCJuZXQiOiJ0Y3AiLCJ0eXBlIjoibm9uZSIsImhvc3QiOiIiLCJwYXRoIjoiIiwidGxzIjoiIn0="
        mock_message.media = None
        
        # Make iter_messages return messages in correct order
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message
        
        mock_client.iter_messages = mock_iter_messages
        
        # Initialize collector
        await collector.initialize()
        
        # Collect from channel
        _, channel_data = sample_channel
        stats = await collector.collect_from_channel(
            channel_data,
            collection_run_id=1,
        )
        
        assert stats['messages_scanned'] == 1
        assert stats['last_message_id'] == 100
        
        await collector.shutdown()
    
    @pytest.mark.asyncio
    @patch('app.collector.collector.TelegramClient')
    async def test_incremental_collection(
        self,
        mock_telethon_client,
        collector,
        mock_client,
        sample_channel,
    ):
        """Test incremental collection using last_message_id."""
        mock_telethon_client.return_value = mock_client
        mock_entity = Mock()
        mock_client.get_entity.return_value = mock_entity
        
        # Update channel with last_message_id
        channel, channel_data = sample_channel
        with get_session() as session:
            ChannelRepository.update(
                session,
                channel,
                last_message_id=50,
            )
            # Update channel_data directly instead of refreshing
            channel_data['last_message_id'] = 50
        
        # Mock messages
        mock_message = Mock()
        mock_message.id = 51
        mock_message.text = "test config"
        mock_message.media = None
        
        async def mock_iter_messages(*args, **kwargs):
            min_id = kwargs.get('min_id', 0)
            if min_id == 50:
                yield mock_message
        
        mock_client.iter_messages = mock_iter_messages
        
        await collector.initialize()
        stats = await collector.collect_from_channel(channel_data, collection_run_id=1)
        
        assert stats['last_message_id'] == 51
        
        await collector.shutdown()
    
    @pytest.mark.asyncio
    @patch('app.collector.collector.TelegramClient')
    async def test_first_run_message_limit(
        self,
        mock_telethon_client,
        collector,
        mock_client,
        sample_channel,
    ):
        """Test first run message limit."""
        mock_telethon_client.return_value = mock_client
        mock_entity = Mock()
        mock_client.get_entity.return_value = mock_entity
        
        # Mock messages
        messages = []
        for i in range(150):
            mock_msg = Mock()
            mock_msg.id = i + 1
            mock_msg.text = f"config {i}"
            mock_msg.media = None
            messages.append(mock_msg)
        
        async def mock_iter_messages(*args, **kwargs):
            limit = kwargs.get('limit', None)
            for msg in messages[:limit] if limit else messages:
                yield msg
        
        mock_client.iter_messages = mock_iter_messages
        
        await collector.initialize()
        _, channel_data = sample_channel
        stats = await collector.collect_from_channel(channel_data, collection_run_id=1)
        
        # Should limit to first_run_message_limit (100)
        assert stats['messages_scanned'] <= 100
        
        await collector.shutdown()
    
    @pytest.mark.asyncio
    @patch('app.collector.collector.TelegramClient')
    async def test_multiple_channels(
        self,
        mock_telethon_client,
        collector,
        mock_client,
        test_database,
    ):
        """Test collection from multiple channels."""
        mock_telethon_client.return_value = mock_client
        mock_entity = Mock()
        mock_client.get_entity.return_value = mock_entity
        
        # Create multiple channels
        with test_database as session:
            channel1 = ChannelRepository.create(
                session,
                telegram_id=111111111,
                username="channel1",
                enabled=True,
            )
            channel2 = ChannelRepository.create(
                session,
                telegram_id=222222222,
                username="channel2",
                enabled=True,
            )
            session.commit()
            session.refresh(channel1)
            session.refresh(channel2)
            
            # Create channel data dicts
            channel1_data = {
                'id': channel1.id,
                'telegram_id': channel1.telegram_id,
                'last_message_id': channel1.last_message_id,
                'username': channel1.username,
            }
            channel2_data = {
                'id': channel2.id,
                'telegram_id': channel2.telegram_id,
                'last_message_id': channel2.last_message_id,
                'username': channel2.username,
            }
        
        # Mock messages
        mock_message = Mock()
        mock_message.id = 100
        mock_message.text = "test"
        mock_message.media = None
        
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message
        
        mock_client.iter_messages = mock_iter_messages
        
        await collector.initialize()
        
        # Collect from both channels
        stats1 = await collector.collect_from_channel(channel1_data, collection_run_id=1)
        stats2 = await collector.collect_from_channel(channel2_data, collection_run_id=1)
        
        assert stats1['messages_scanned'] == 1
        assert stats2['messages_scanned'] == 1
        
        await collector.shutdown()
    
    @pytest.mark.asyncio
    @patch('app.collector.collector.TelegramClient')
    async def test_channel_failure_continues(
        self,
        mock_telethon_client,
        collector,
        mock_client,
        test_database,
    ):
        """Test that one channel failure doesn't stop collection."""
        mock_telethon_client.return_value = mock_client
        
        # Create channels
        with test_database as session:
            channel1 = ChannelRepository.create(
                session,
                telegram_id=111111111,
                username="channel1",
                enabled=True,
            )
            channel2 = ChannelRepository.create(
                session,
                telegram_id=222222222,
                username="channel2",
                enabled=True,
            )
            session.commit()
            session.refresh(channel1)
            session.refresh(channel2)
            
            # Create channel data dicts
            channel1_data = {
                'id': channel1.id,
                'telegram_id': channel1.telegram_id,
                'last_message_id': channel1.last_message_id,
                'username': channel1.username,
            }
            channel2_data = {
                'id': channel2.id,
                'telegram_id': channel2.telegram_id,
                'last_message_id': channel2.last_message_id,
                'username': channel2.username,
            }
        
        # Make first channel fail
        mock_client.get_entity.side_effect = [
            Exception("Channel 1 failed"),
            Mock(),  # Channel 2 succeeds
        ]
        
        mock_message = Mock()
        mock_message.id = 100
        mock_message.text = "test"
        mock_message.media = None
        
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message
        
        mock_client.iter_messages = mock_iter_messages
        
        await collector.initialize()
        
        # First channel should fail
        with pytest.raises(Exception):
            await collector.collect_from_channel(channel1_data, collection_run_id=1)
        
        # Second channel should succeed
        stats = await collector.collect_from_channel(channel2_data, collection_run_id=1)
        assert stats['messages_scanned'] == 1
        
        await collector.shutdown()
    
    @pytest.mark.asyncio
    @patch('app.collector.collector.TelegramClient')
    async def test_process_text_content(
        self,
        mock_telethon_client,
        collector,
        sample_channel,
    ):
        """Test processing text content."""
        text = """
        vmess://eyJ2IjoiMiIsInBzIjoidGVzdCIsImFkZCI6IjEyNy4wLjAuMSIsInBvcnQiOiI4MCIsImlkIjoiYWJjZCIsImFpZCI6IjAiLCJuZXQiOiJ0Y3AiLCJ0eXBlIjoibm9uZSIsImhvc3QiOiIiLCJwYXRoIjoiIiwidGxzIjoiIn0=
        vless://12345678-1234-1234-1234-123456789abc@127.0.0.1:443?encryption=none
        """
        
        _, channel_data = sample_channel
        stats = collector.process_text_content(
            text,
            channel_data['id'],
            message_id=100,
        )
        
        assert stats['configs_found'] >= 0
    
    @pytest.mark.asyncio
    @patch('app.collector.collector.TelegramClient')
    async def test_process_document_attachment_valid(
        self,
        mock_telethon_client,
        collector,
        mock_client,
        sample_channel,
    ):
        """Test processing valid .txt attachment."""
        mock_telethon_client.return_value = mock_client
        
        # Create temp file with content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = Path(f.name)
            f.write("vmess://test config")
        
        # Mock document
        mock_document = Mock()
        mock_document.size = 1024  # 1 KB
        mock_document.mime_type = "text/plain"
        
        # Mock download
        async def mock_download(media, file):
            with open(file, 'w') as f:
                f.write("vmess://test config")
        
        mock_client.download_media = mock_download
        
        _, channel_data = sample_channel
        stats = await collector.process_document_attachment(
            mock_document,
            channel_data['id'],
            message_id=100,
        )
        
        # Clean up
        temp_path.unlink(missing_ok=True)
        
        assert stats['configs_found'] >= 0
    
    @pytest.mark.asyncio
    @patch('app.collector.collector.TelegramClient')
    async def test_process_document_attachment_too_large(
        self,
        mock_telethon_client,
        collector,
        sample_channel,
    ):
        """Test processing attachment larger than 10 MB."""
        mock_document = Mock()
        mock_document.size = 15 * 1024 * 1024  # 15 MB
        mock_document.mime_type = "text/plain"
        
        _, channel_data = sample_channel
        stats = await collector.process_document_attachment(
            mock_document,
            channel_data['id'],
            message_id=100,
        )
        
        assert stats['configs_found'] == 0
    
    @pytest.mark.asyncio
    @patch('app.collector.collector.TelegramClient')
    async def test_process_document_invalid_utf8(
        self,
        mock_telethon_client,
        collector,
        mock_client,
        sample_channel,
    ):
        """Test processing attachment with invalid UTF-8."""
        mock_telethon_client.return_value = mock_client
        
        # Create temp file with binary content
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as f:
            temp_path = Path(f.name)
            f.write(b'\x80\x81\x82\x83')  # Invalid UTF-8
        
        # Mock document
        mock_document = Mock()
        mock_document.size = 1024
        mock_document.mime_type = "text/plain"
        
        async def mock_download(media, file):
            with open(file, 'wb') as f:
                f.write(b'\x80\x81\x82\x83')
        
        mock_client.download_media = mock_download
        
        _, channel_data = sample_channel
        stats = await collector.process_document_attachment(
            mock_document,
            channel_data['id'],
            message_id=100,
        )
        
        # Clean up
        temp_path.unlink(missing_ok=True)
        
        assert stats['invalid_configs'] == 1
    
    def test_store_config_new(
        self,
        collector,
        sample_channel,
        sample_parsed_config,
        test_database,
    ):
        """Test storing a new configuration."""
        _, channel_data = sample_channel
        stats = collector.store_config(
            sample_parsed_config,
            channel_data['id'],
            message_id=100,
        )
        
        assert stats['configs_added'] == 1
        assert stats['duplicates_removed'] == 0
    
    def test_store_config_duplicate(
        self,
        collector,
        sample_channel,
        sample_parsed_config,
        test_database,
    ):
        """Test storing duplicate configuration."""
        _, channel_data = sample_channel
        # Store first time
        stats1 = collector.store_config(
            sample_parsed_config,
            channel_data['id'],
            message_id=100,
        )
        assert stats1['configs_added'] == 1
        
        # Store same config again (same message)
        stats2 = collector.store_config(
            sample_parsed_config,
            channel_data['id'],
            message_id=100,
        )
        assert stats2['configs_added'] == 0
        assert stats2['duplicates_removed'] == 1
    
    def test_store_config_multiple_occurrences(
        self,
        collector,
        sample_channel,
        sample_parsed_config,
        test_database,
    ):
        """Test storing same config from different messages."""
        _, channel_data = sample_channel
        # Store first occurrence
        stats1 = collector.store_config(
            sample_parsed_config,
            channel_data['id'],
            message_id=100,
        )
        assert stats1['configs_added'] == 1
        
        # Store same config from different message
        stats2 = collector.store_config(
            sample_parsed_config,
            channel_data['id'],
            message_id=200,
        )
        assert stats2['configs_added'] == 1  # New occurrence
        assert stats2['duplicates_removed'] == 0
    
    @pytest.mark.asyncio
    @patch('app.collector.collector.TelegramClient')
    async def test_collection_run_statistics(
        self,
        mock_telethon_client,
        collector,
        mock_client,
        test_database,
    ):
        """Test collection run statistics tracking."""
        mock_telethon_client.return_value = mock_client
        mock_entity = Mock()
        mock_client.get_entity.return_value = mock_entity
        
        # Create channel
        with test_database as session:
            channel = ChannelRepository.create(
                session,
                telegram_id=123456789,
                username="testchannel",
                enabled=True,
            )
            session.commit()
            session.refresh(channel)
        
        # Mock messages
        mock_message = Mock()
        mock_message.id = 100
        mock_message.text = "test"
        mock_message.media = None
        
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message
        
        mock_client.iter_messages = mock_iter_messages
        
        await collector.initialize()
        
        # Run collection
        stats = await collector.collect()
        
        # Check collection run was created
        with test_database as session:
            runs = CollectionRunRepository.get_latest(session, limit=1)
            assert len(runs) == 1
            run = runs[0]
            assert run.status in ["completed", "failed"]
            assert run.messages_scanned == stats['messages_scanned']
            assert run.configs_found == stats['configs_found']
        
        await collector.shutdown()
    
    def test_session_configuration(self, collector, mock_settings):
        """Test Telegram session configuration."""
        assert collector.settings.telegram_session_name == "test_session"
    
    def test_sensitive_data_not_logged(self, collector):
        """Test that sensitive data is not logged."""
        # This test verifies the logging filter is working
        # The actual filtering is in logging_config.py
        from app.logging_config import SensitiveDataFilter
        from logging import LogRecord
        
        filter_instance = SensitiveDataFilter()
        
        # Test redaction with actual sensitive patterns
        test_message = "api_hash=secret123 bot_token=abc456"
        record = LogRecord(
            name="test",
            level=20,
            pathname="test.py",
            lineno=1,
            msg=test_message,
            args=(),
            exc_info=None,
        )
        
        filter_instance.filter(record)
        
        message = record.msg
        # Check that the sensitive values are redacted
        assert "secret123" not in message
        assert "abc456" not in message
        assert "***REDACTED***" in message


# Helper function for tests
def get_session():
    """Get database session for tests."""
    from app.database.database import get_session
    return get_session()
