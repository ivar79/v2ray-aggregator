"""
Repository pattern for database operations.

Provides clean abstraction layer for database access with proper error handling.
"""
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func

from app.database.models import (
    Channel,
    Config,
    ConfigOccurrence,
    CollectionRun,
    ConfigLifecycleState,
)


class ChannelRepository:
    """Repository for Channel operations."""
    
    @staticmethod
    def create(
        session: Session,
        telegram_id: int,
        username: Optional[str] = None,
        title: Optional[str] = None,
        enabled: bool = True,
    ) -> Channel:
        """
        Create a new channel.
        
        Args:
            session: Database session
            telegram_id: Telegram channel ID
            username: Channel username (optional)
            title: Channel title (optional)
            enabled: Whether channel is enabled for collection
            
        Returns:
            Created Channel instance
        """
        channel = Channel(
            telegram_id=telegram_id,
            username=username,
            title=title,
            enabled=enabled,
        )
        session.add(channel)
        session.flush()
        return channel
    
    @staticmethod
    def get_by_id(session: Session, channel_id: int) -> Optional[Channel]:
        """
        Get channel by database ID.
        
        Args:
            session: Database session
            channel_id: Database ID
            
        Returns:
            Channel instance or None
        """
        return session.get(Channel, channel_id)
    
    @staticmethod
    def get_by_telegram_id(session: Session, telegram_id: int) -> Optional[Channel]:
        """
        Get channel by Telegram ID.
        
        Args:
            session: Database session
            telegram_id: Telegram channel ID
            
        Returns:
            Channel instance or None
        """
        stmt = select(Channel).where(Channel.telegram_id == telegram_id)
        return session.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_by_username(session: Session, username: str) -> Optional[Channel]:
        """
        Get channel by username.
        
        Args:
            session: Database session
            username: Channel username
            
        Returns:
            Channel instance or None
        """
        # Remove @ if present
        clean_username = username.lstrip('@')
        stmt = select(Channel).where(Channel.username == clean_username)
        return session.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_all_enabled(session: Session) -> List[Channel]:
        """
        Get all enabled channels.
        
        Args:
            session: Database session
            
        Returns:
            List of enabled Channel instances
        """
        stmt = select(Channel).where(Channel.enabled == True)
        return list(session.execute(stmt).scalars().all())
    
    @staticmethod
    def get_all(session: Session) -> List[Channel]:
        """
        Get all channels.
        
        Args:
            session: Database session
            
        Returns:
            List of all Channel instances
        """
        return list(session.execute(select(Channel)).scalars().all())
    
    @staticmethod
    def update(
        session: Session,
        channel: Channel,
        username: Optional[str] = None,
        title: Optional[str] = None,
        enabled: Optional[bool] = None,
        last_message_id: Optional[int] = None,
        last_error: Optional[str] = None,
    ) -> Channel:
        """
        Update channel fields.
        
        Args:
            session: Database session
            channel: Channel instance to update
            username: New username (optional)
            title: New title (optional)
            enabled: New enabled state (optional)
            last_message_id: New last message ID (optional)
            last_error: New error message (optional)
            
        Returns:
            Updated Channel instance
        """
        if username is not None:
            channel.username = username
        if title is not None:
            channel.title = title
        if enabled is not None:
            channel.enabled = enabled
        if last_message_id is not None:
            channel.last_message_id = last_message_id
        if last_error is not None:
            channel.last_error = last_error
        channel.updated_at = datetime.utcnow()
        session.flush()
        return channel
    
    @staticmethod
    def delete(session: Session, channel: Channel) -> None:
        """
        Delete a channel.
        
        Args:
            session: Database session
            channel: Channel instance to delete
        """
        session.delete(channel)
        session.flush()


class ConfigRepository:
    """Repository for Config operations."""
    
    @staticmethod
    def create(
        session: Session,
        protocol: str,
        raw_config: str,
        normalized_config: str,
        config_hash: str,
        is_structurally_valid: bool = False,
    ) -> Config:
        """
        Create a new configuration.
        
        Args:
            session: Database session
            protocol: Protocol name (vmess, vless, etc.)
            raw_config: Raw configuration string
            normalized_config: Normalized configuration string
            config_hash: SHA-256 hash of normalized config
            is_structurally_valid: Whether config passes structural validation
            
        Returns:
            Created Config instance
        """
        config = Config(
            protocol=protocol,
            raw_config=raw_config,
            normalized_config=normalized_config,
            config_hash=config_hash,
            is_structurally_valid=is_structurally_valid,
            lifecycle_state=ConfigLifecycleState.NEW.value,
            is_active=True,
        )
        session.add(config)
        session.flush()
        return config
    
    @staticmethod
    def get_by_id(session: Session, config_id: int) -> Optional[Config]:
        """
        Get config by database ID.
        
        Args:
            session: Database session
            config_id: Database ID
            
        Returns:
            Config instance or None
        """
        return session.get(Config, config_id)
    
    @staticmethod
    def get_by_hash(session: Session, config_hash: str) -> Optional[Config]:
        """
        Get config by hash.
        
        Args:
            session: Database session
            config_hash: Configuration hash
            
        Returns:
            Config instance or None
        """
        stmt = select(Config).where(Config.config_hash == config_hash)
        return session.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_all_active(session: Session) -> List[Config]:
        """
        Get all active configurations.
        
        Args:
            session: Database session
            
        Returns:
            List of active Config instances
        """
        stmt = select(Config).where(
            and_(
                Config.is_active == True,
                Config.is_structurally_valid == True,
            )
        )
        return list(session.execute(stmt).scalars().all())
    
    @staticmethod
    def get_by_protocol(session: Session, protocol: str, active_only: bool = True) -> List[Config]:
        """
        Get configurations by protocol.
        
        Args:
            session: Database session
            protocol: Protocol name
            active_only: Only return active configs
            
        Returns:
            List of Config instances
        """
        stmt = select(Config).where(Config.protocol == protocol)
        if active_only:
            stmt = stmt.where(
                and_(
                    Config.is_active == True,
                    Config.is_structurally_valid == True,
                )
            )
        return list(session.execute(stmt).scalars().all())
    
    @staticmethod
    def update_lifecycle_state(
        session: Session,
        config: Config,
        lifecycle_state: ConfigLifecycleState,
    ) -> Config:
        """
        Update configuration lifecycle state.
        
        Args:
            session: Database session
            config: Config instance to update
            lifecycle_state: New lifecycle state
            
        Returns:
            Updated Config instance
        """
        config.lifecycle_state = lifecycle_state.value
        config.last_seen_at = datetime.utcnow()
        session.flush()
        return config
    
    @staticmethod
    def update_validation(
        session: Session,
        config: Config,
        is_structurally_valid: bool,
    ) -> Config:
        """
        Update configuration validation status.
        
        Args:
            session: Database session
            config: Config instance to update
            is_structurally_valid: Whether config is structurally valid
            
        Returns:
            Updated Config instance
        """
        config.is_structurally_valid = is_structurally_valid
        if is_structurally_valid:
            config.lifecycle_state = ConfigLifecycleState.VALID.value
        else:
            config.lifecycle_state = ConfigLifecycleState.INVALID.value
        config.last_seen_at = datetime.utcnow()
        session.flush()
        return config
    
    @staticmethod
    def set_active(session: Session, config: Config, is_active: bool) -> Config:
        """
        Set configuration active state.
        
        Args:
            session: Database session
            config: Config instance to update
            is_active: Whether config should be active
            
        Returns:
            Updated Config instance
        """
        config.is_active = is_active
        if is_active:
            config.lifecycle_state = ConfigLifecycleState.ACTIVE.value
        else:
            config.lifecycle_state = ConfigLifecycleState.INACTIVE.value
        config.last_seen_at = datetime.utcnow()
        session.flush()
        return config
    
    @staticmethod
    def get_stats(session: Session) -> dict:
        """
        Get configuration statistics.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary with statistics
        """
        total = session.execute(select(func.count()).select_from(Config)).scalar()
        active = session.execute(
            select(func.count()).select_from(Config).where(
                and_(
                    Config.is_active == True,
                    Config.is_structurally_valid == True,
                )
            )
        ).scalar()
        invalid = session.execute(
            select(func.count()).select_from(Config).where(Config.is_structurally_valid == False)
        ).scalar()
        
        # Count by protocol
        protocol_counts = {}
        for protocol in ['vmess', 'vless', 'trojan', 'shadowsocks', 'hysteria', 'hysteria2']:
            count = session.execute(
                select(func.count()).select_from(Config).where(
                    and_(
                        Config.protocol == protocol,
                        Config.is_active == True,
                        Config.is_structurally_valid == True,
                    )
                )
            ).scalar()
            if count > 0:
                protocol_counts[protocol] = count
        
        return {
            'total_unique': total,
            'active_count': active,
            'invalid_count': invalid,
            'by_protocol': protocol_counts,
        }


class ConfigOccurrenceRepository:
    """Repository for ConfigOccurrence operations."""
    
    @staticmethod
    def create(
        session: Session,
        config_id: int,
        channel_id: int,
        source_message_id: int,
        raw_occurrence: Optional[str] = None,
    ) -> ConfigOccurrence:
        """
        Create a new config occurrence.
        
        Args:
            session: Database session
            config_id: Config database ID
            channel_id: Channel database ID
            source_message_id: Telegram message ID
            raw_occurrence: Raw occurrence string (optional)
            
        Returns:
            Created ConfigOccurrence instance
        """
        occurrence = ConfigOccurrence(
            config_id=config_id,
            channel_id=channel_id,
            source_message_id=source_message_id,
            raw_occurrence=raw_occurrence,
        )
        session.add(occurrence)
        session.flush()
        return occurrence
    
    @staticmethod
    def get_existing(
        session: Session,
        config_id: int,
        channel_id: int,
        source_message_id: int,
    ) -> Optional[ConfigOccurrence]:
        """
        Check if occurrence already exists.
        
        Args:
            session: Database session
            config_id: Config database ID
            channel_id: Channel database ID
            source_message_id: Telegram message ID
            
        Returns:
            ConfigOccurrence instance or None
        """
        stmt = select(ConfigOccurrence).where(
            and_(
                ConfigOccurrence.config_id == config_id,
                ConfigOccurrence.channel_id == channel_id,
                ConfigOccurrence.source_message_id == source_message_id,
            )
        )
        return session.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def update_last_seen(session: Session, occurrence: ConfigOccurrence) -> ConfigOccurrence:
        """
        Update occurrence last seen timestamp.
        
        Args:
            session: Database session
            occurrence: ConfigOccurrence instance to update
            
        Returns:
            Updated ConfigOccurrence instance
        """
        occurrence.last_seen_at = datetime.utcnow()
        session.flush()
        return occurrence


class CollectionRunRepository:
    """Repository for CollectionRun operations."""
    
    @staticmethod
    def create(session: Session) -> CollectionRun:
        """
        Create a new collection run.
        
        Args:
            session: Database session
            
        Returns:
            Created CollectionRun instance
        """
        run = CollectionRun(
            status="running",
        )
        session.add(run)
        session.flush()
        return run
    
    @staticmethod
    def get_by_id(session: Session, run_id: int) -> Optional[CollectionRun]:
        """
        Get collection run by ID.
        
        Args:
            session: Database session
            run_id: Database ID
            
        Returns:
            CollectionRun instance or None
        """
        return session.get(CollectionRun, run_id)
    
    @staticmethod
    def get_latest(session: Session, limit: int = 10) -> List[CollectionRun]:
        """
        Get latest collection runs.
        
        Args:
            session: Database session
            limit: Maximum number of runs to return
            
        Returns:
            List of CollectionRun instances
        """
        stmt = (
            select(CollectionRun)
            .order_by(CollectionRun.started_at.desc())
            .limit(limit)
        )
        return list(session.execute(stmt).scalars().all())
    
    @staticmethod
    def update(
        session: Session,
        run: CollectionRun,
        status: Optional[str] = None,
        finished_at: Optional[datetime] = None,
        messages_scanned: Optional[int] = None,
        configs_found: Optional[int] = None,
        configs_added: Optional[int] = None,
        duplicates_removed: Optional[int] = None,
        invalid_configs: Optional[int] = None,
        errors: Optional[str] = None,
        github_published: Optional[bool] = None,
        github_commit_hash: Optional[str] = None,
        github_error: Optional[str] = None,
    ) -> CollectionRun:
        """
        Update collection run fields.
        
        Args:
            session: Database session
            run: CollectionRun instance to update
            status: New status (optional)
            finished_at: Finish timestamp (optional)
            messages_scanned: Messages scanned count (optional)
            configs_found: Configs found count (optional)
            configs_added: Configs added count (optional)
            duplicates_removed: Duplicates removed count (optional)
            invalid_configs: Invalid configs count (optional)
            errors: Error messages (optional)
            github_published: GitHub publish status (optional)
            github_commit_hash: GitHub commit hash (optional)
            github_error: GitHub error message (optional)
            
        Returns:
            Updated CollectionRun instance
        """
        if status is not None:
            run.status = status
        if finished_at is not None:
            run.finished_at = finished_at
        if messages_scanned is not None:
            run.messages_scanned = messages_scanned
        if configs_found is not None:
            run.configs_found = configs_found
        if configs_added is not None:
            run.configs_added = configs_added
        if duplicates_removed is not None:
            run.duplicates_removed = duplicates_removed
        if invalid_configs is not None:
            run.invalid_configs = invalid_configs
        if errors is not None:
            run.errors = errors
        if github_published is not None:
            run.github_published = github_published
        if github_commit_hash is not None:
            run.github_commit_hash = github_commit_hash
        if github_error is not None:
            run.github_error = github_error
        session.flush()
        return run
    
    @staticmethod
    def complete(
        session: Session,
        run: CollectionRun,
        status: str = "completed",
    ) -> CollectionRun:
        """
        Mark collection run as completed.
        
        Args:
            session: Database session
            run: CollectionRun instance to update
            status: Final status (default: completed)
            
        Returns:
            Updated CollectionRun instance
        """
        run.status = status
        run.finished_at = datetime.utcnow()
        session.flush()
        return run
