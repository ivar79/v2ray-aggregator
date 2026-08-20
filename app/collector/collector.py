"""
Telegram Collector for V2Ray Aggregator.

Collects V2Ray configurations from Telegram channels using Telethon.
Handles message processing, document attachments, and database integration.
"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import tempfile

from telethon import TelegramClient, types
from telethon.errors import (
    ChatAdminRequiredError,
    ChannelPrivateError,
    FloodWaitError,
    UserBannedInChannelError,
)

from app.config import get_settings
from app.logging_config import get_logger
from app.database.database import get_session
from app.database.repository import (
    ChannelRepository,
    ConfigRepository,
    ConfigOccurrenceRepository,
    CollectionRunRepository,
)
from app.database.models import ConfigLifecycleState
from app.parser.vmess import VMessParser
from app.parser.vless import VLESSParser
from app.parser.trojan import TrojanParser
from app.parser.shadowsocks import ShadowsocksParser
from app.parser.hysteria import HysteriaParser
from app.parser.hysteria2 import Hysteria2Parser


class TelegramCollector:
    """
    Collector for Telegram channels.
    
    Fetches messages from enabled channels, extracts configurations,
    and stores them in the database with proper deduplication.
    """
    
    def __init__(self):
        """Initialize the collector."""
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.client: Optional[TelegramClient] = None
        
        # Initialize parsers
        self.parsers = {
            'vmess': VMessParser(),
            'vless': VLESSParser(),
            'trojan': TrojanParser(),
            'shadowsocks': ShadowsocksParser(),
            'hysteria': HysteriaParser(),
            'hysteria2': Hysteria2Parser(),
        }
    
    async def initialize(self):
        """Initialize Telethon client."""
        session_path = Path(self.settings.telegram_session_name)
        
        self.client = TelegramClient(
            str(session_path),
            self.settings.telegram_api_id,
            self.settings.telegram_api_hash,
        )
        
        await self.client.start()
        self.logger.info("Telegram client initialized")
    
    async def shutdown(self):
        """Shutdown Telethon client."""
        if self.client:
            await self.client.disconnect()
            self.logger.info("Telegram client disconnected")
    
    async def collect(self) -> Dict[str, Any]:
        """
        Run a full collection cycle.
        
        Returns:
            Dictionary with collection statistics
        """
        self.logger.info("Starting collection cycle")
        
        # Create collection run
        with get_session() as session:
            collection_run = CollectionRunRepository.create(session)
            collection_run_id = collection_run.id
        
        stats = {
            'messages_scanned': 0,
            'configs_found': 0,
            'configs_added': 0,
            'duplicates_removed': 0,
            'invalid_configs': 0,
            'errors': [],
        }
        
        try:
            # Initialize Telegram client
            await self.initialize()
            
            # Get enabled channels
            with get_session() as session:
                channels = ChannelRepository.get_all_enabled(session)
                # Extract channel data before session closes
                channel_data = []
                for ch in channels:
                    channel_data.append({
                        'id': ch.id,
                        'telegram_id': ch.telegram_id,
                        'last_message_id': ch.last_message_id,
                        'username': ch.username,
                    })
            
            self.logger.info(f"Found {len(channel_data)} enabled channels")
            
            # Collect from each channel
            for ch_data in channel_data:
                channel_id = ch_data['id']
                channel_telegram_id = ch_data['telegram_id']
                last_message_id = ch_data['last_message_id']
                
                try:
                    channel_stats = await self.collect_from_channel(
                        ch_data,
                        collection_run_id,
                    )
                    stats['messages_scanned'] += channel_stats['messages_scanned']
                    stats['configs_found'] += channel_stats['configs_found']
                    stats['configs_added'] += channel_stats['configs_added']
                    stats['duplicates_removed'] += channel_stats['duplicates_removed']
                    stats['invalid_configs'] += channel_stats['invalid_configs']
                    
                    # Update channel last_message_id
                    with get_session() as session:
                        db_channel = ChannelRepository.get_by_id(session, channel_id)
                        if db_channel:
                            ChannelRepository.update(
                                session,
                                db_channel,
                                last_message_id=channel_stats['last_message_id'],
                                last_error=None,
                            )
                    
                except Exception as e:
                    error_msg = f"Channel {channel_telegram_id} failed: {str(e)}"
                    self.logger.error(error_msg)
                    stats['errors'].append(error_msg)
                    
                    # Update channel error state
                    with get_session() as session:
                        db_channel = ChannelRepository.get_by_id(session, channel_id)
                        if db_channel:
                            ChannelRepository.update(
                                session,
                                db_channel,
                                last_error=str(e),
                            )
            
            # Update collection run as completed
            with get_session() as session:
                collection_run = CollectionRunRepository.get_by_id(session, collection_run_id)
                if collection_run:
                    CollectionRunRepository.update(
                        session,
                        collection_run,
                        status="completed",
                        finished_at=datetime.utcnow(),
                        messages_scanned=stats['messages_scanned'],
                        configs_found=stats['configs_found'],
                        configs_added=stats['configs_added'],
                        duplicates_removed=stats['duplicates_removed'],
                        invalid_configs=stats['invalid_configs'],
                        errors='\n'.join(stats['errors']) if stats['errors'] else None,
                    )
            
            self.logger.info(f"Collection cycle completed: {stats}")
            return stats
            
        except Exception as e:
            error_msg = f"Collection cycle failed: {str(e)}"
            self.logger.error(error_msg)
            stats['errors'].append(error_msg)
            
            # Update collection run as failed
            with get_session() as session:
                collection_run = CollectionRunRepository.get_by_id(session, collection_run_id)
                if collection_run:
                    CollectionRunRepository.update(
                        session,
                        collection_run,
                        status="failed",
                        finished_at=datetime.utcnow(),
                        errors='\n'.join(stats['errors']),
                    )
            
            raise
        finally:
            await self.shutdown()
    
    async def collect_from_channel(
        self,
        channel_data: Dict[str, Any],
        collection_run_id: int,
    ) -> Dict[str, Any]:
        """
        Collect configurations from a single channel.
        
        Args:
            channel_data: Dictionary with channel data (id, telegram_id, last_message_id, username)
            collection_run_id: Collection run database ID
            
        Returns:
            Dictionary with channel statistics
        """
        # Extract channel data
        channel_id = channel_data['id']
        channel_telegram_id = channel_data['telegram_id']
        last_message_id = channel_data['last_message_id']
        
        stats = {
            'messages_scanned': 0,
            'configs_found': 0,
            'configs_added': 0,
            'duplicates_removed': 0,
            'invalid_configs': 0,
            'last_message_id': last_message_id,
        }
        
        self.logger.info(f"Collecting from channel {channel_telegram_id}")
        
        try:
            # Determine message limit
            if last_message_id == 0:
                # First run: use limit
                limit = self.settings.first_run_message_limit
                self.logger.info(f"First run for channel, limiting to {limit} messages")
            else:
                # Incremental: no limit, start from last_message_id
                limit = None
            
            # Fetch messages
            entity = await self.client.get_entity(channel_telegram_id)
            messages = []
            
            async for message in self.client.iter_messages(
                entity,
                min_id=last_message_id,
                limit=limit,
            ):
                messages.append(message)
            
            # Process in reverse order (oldest first)
            messages.reverse()
            
            self.logger.info(f"Fetched {len(messages)} messages from channel")
            
            # Process each message
            for message in messages:
                try:
                    message_stats = await self.process_message(
                        message,
                        channel_id,
                        channel_telegram_id,
                    )
                    stats['messages_scanned'] += 1
                    stats['configs_found'] += message_stats['configs_found']
                    stats['configs_added'] += message_stats['configs_added']
                    stats['duplicates_removed'] += message_stats['duplicates_removed']
                    stats['invalid_configs'] += message_stats['invalid_configs']
                    
                    # Update last_message_id
                    if message.id > stats['last_message_id']:
                        stats['last_message_id'] = message.id
                    
                except Exception as e:
                    self.logger.error(f"Failed to process message {message.id}: {e}")
                    stats['invalid_configs'] += 1
            
            self.logger.info(f"Channel {channel_telegram_id} collection completed: {stats}")
            return stats
            
        except ChatAdminRequiredError:
            raise Exception("Not authorized to access this channel")
        except ChannelPrivateError:
            raise Exception("Channel is private or inaccessible")
        except UserBannedInChannelError:
            raise Exception("User is banned from this channel")
        except FloodWaitError as e:
            raise Exception(f"Flood wait required: {e.seconds} seconds")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")
    
    async def process_message(
        self,
        message,
        channel_db_id: int,
        channel_telegram_id: int,
    ) -> Dict[str, Any]:
        """
        Process a single Telegram message.
        
        Args:
            message: Telethon message object
            channel_db_id: Channel database ID
            channel_telegram_id: Channel Telegram ID
            
        Returns:
            Dictionary with message statistics
        """
        stats = {
            'configs_found': 0,
            'configs_added': 0,
            'duplicates_removed': 0,
            'invalid_configs': 0,
        }
        
        # Extract text content
        text_content = ""
        if message.text:
            text_content += message.text
        if message.media and hasattr(message.media, 'caption') and message.media.caption:
            text_content += "\n" + message.media.caption
        
        # Process text content
        if text_content.strip():
            text_stats = self.process_text_content(
                text_content,
                channel_db_id,
                message.id,
            )
            stats['configs_found'] += text_stats['configs_found']
            stats['configs_added'] += text_stats['configs_added']
            stats['duplicates_removed'] += text_stats['duplicates_removed']
            stats['invalid_configs'] += text_stats['invalid_configs']
        
        # Process document attachments
        if message.media and isinstance(message.media, types.MessageMediaDocument):
            doc_stats = await self.process_document_attachment(
                message.media.document,
                channel_db_id,
                message.id,
            )
            stats['configs_found'] += doc_stats['configs_found']
            stats['configs_added'] += doc_stats['configs_added']
            stats['duplicates_removed'] += doc_stats['duplicates_removed']
            stats['invalid_configs'] += doc_stats['invalid_configs']
        
        return stats
    
    def process_text_content(
        self,
        text: str,
        channel_db_id: int,
        message_id: int,
    ) -> Dict[str, Any]:
        """
        Process text content for configurations.
        
        Args:
            text: Text content
            channel_db_id: Channel database ID
            message_id: Telegram message ID
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            'configs_found': 0,
            'configs_added': 0,
            'duplicates_removed': 0,
            'invalid_configs': 0,
        }
        
        # Extract configs using all parsers
        for protocol, parser in self.parsers.items():
            try:
                parsed_configs = parser.extract_and_process(text)
                
                for parsed_config in parsed_configs:
                    stats['configs_found'] += 1
                    config_stats = self.store_config(
                        parsed_config,
                        channel_db_id,
                        message_id,
                    )
                    stats['configs_added'] += config_stats['configs_added']
                    stats['duplicates_removed'] += config_stats['duplicates_removed']
                    stats['invalid_configs'] += config_stats['invalid_configs']
                    
            except Exception as e:
                self.logger.error(f"Failed to parse {protocol} configs: {e}")
        
        return stats
    
    async def process_document_attachment(
        self,
        document,
        channel_db_id: int,
        message_id: int,
    ) -> Dict[str, Any]:
        """
        Process document attachment for configurations.
        
        Args:
            document: Telethon document object
            channel_db_id: Channel database ID
            message_id: Telegram message ID
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            'configs_found': 0,
            'configs_added': 0,
            'duplicates_removed': 0,
            'invalid_configs': 0,
        }
        
        # Check file size
        max_size_bytes = self.settings.max_document_size_mb * 1024 * 1024
        if document.size > max_size_bytes:
            self.logger.warning(
                f"Document too large: {document.size} bytes (max {max_size_bytes})"
            )
            return stats
        
        # Check if text file
        mime_type = document.mime_type or ""
        if not mime_type.startswith('text/') and not document.attributes:
            self.logger.warning(f"Skipping non-text document: {mime_type}")
            return stats
        
        try:
            # Download document to temp file
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as f:
                temp_path = Path(f.name)
                await self.client.download_media(document, file=temp_path)
            
            # Read file content
            try:
                content = temp_path.read_text(encoding='utf-8')
                
                # Process content
                text_stats = self.process_text_content(
                    content,
                    channel_db_id,
                    message_id,
                )
                stats['configs_found'] += text_stats['configs_found']
                stats['configs_added'] += text_stats['configs_added']
                stats['duplicates_removed'] += text_stats['duplicates_removed']
                stats['invalid_configs'] += text_stats['invalid_configs']
                
            except UnicodeDecodeError:
                self.logger.warning("Document is not valid UTF-8")
                stats['invalid_configs'] += 1
            finally:
                # Clean up temp file
                temp_path.unlink(missing_ok=True)
                
        except Exception as e:
            self.logger.error(f"Failed to process document: {e}")
            stats['invalid_configs'] += 1
        
        return stats
    
    def store_config(
        self,
        parsed_config,
        channel_db_id: int,
        message_id: int,
    ) -> Dict[str, Any]:
        """
        Store a configuration in the database.
        
        Args:
            parsed_config: ParsedConfig object
            channel_db_id: Channel database ID
            message_id: Telegram message ID
            
        Returns:
            Dictionary with storage statistics
        """
        stats = {
            'configs_added': 0,
            'duplicates_removed': 0,
            'invalid_configs': 0,
        }
        
        config_hash = parsed_config.get_hash()
        
        with get_session() as session:
            # Check if config already exists
            existing_config = ConfigRepository.get_by_hash(session, config_hash)
            
            if existing_config:
                # Config exists, check for new occurrence
                existing_occurrence = ConfigOccurrenceRepository.get_existing(
                    session,
                    existing_config.id,
                    channel_db_id,
                    message_id,
                )
                
                if existing_occurrence:
                    # Duplicate occurrence
                    stats['duplicates_removed'] += 1
                else:
                    # New occurrence of existing config
                    ConfigOccurrenceRepository.create(
                        session,
                        config_id=existing_config.id,
                        channel_id=channel_db_id,
                        source_message_id=message_id,
                        raw_occurrence=parsed_config.raw,
                    )
                    # Update config last_seen_at
                    existing_config.last_seen_at = datetime.utcnow()
                    session.flush()
                    stats['configs_added'] += 1
            else:
                # New config
                config = ConfigRepository.create(
                    session,
                    protocol=parsed_config.protocol,
                    raw_config=parsed_config.raw,
                    normalized_config=parsed_config.canonical_representation,
                    config_hash=config_hash,
                    is_structurally_valid=True,
                )
                
                # Create occurrence
                ConfigOccurrenceRepository.create(
                    session,
                    config_id=config.id,
                    channel_id=channel_db_id,
                    source_message_id=message_id,
                    raw_occurrence=parsed_config.raw,
                )
                
                # Update lifecycle state
                ConfigRepository.update_lifecycle_state(
                    session,
                    config,
                    ConfigLifecycleState.VALID,
                )
                
                stats['configs_added'] += 1
        
        return stats


async def collect_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for async collect.
    
    Returns:
        Dictionary with collection statistics
    """
    collector = TelegramCollector()
    return await collector.collect()
