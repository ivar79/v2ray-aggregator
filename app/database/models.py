"""
Database models for V2Ray Aggregator.

Defines the schema for channels, configurations, occurrences, and collection runs.
Uses SQLAlchemy ORM with proper relationships and indexes.
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class ConfigLifecycleState(str, Enum):
    """Configuration lifecycle states."""
    NEW = "new"
    VALID = "valid"
    INVALID = "invalid"
    ACTIVE = "active"
    INACTIVE = "inactive"


class Channel(Base):
    """
    Represents a Telegram source channel.
    
    Tracks channel information and collection state.
    """
    __tablename__ = "channels"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_message_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    config_occurrences: Mapped[list["ConfigOccurrence"]] = relationship(
        "ConfigOccurrence", 
        back_populates="channel",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Config(Base):
    """
    Represents a canonical V2Ray configuration.
    
    Stores the normalized configuration and its lifecycle state.
    One unique configuration per canonical hash.
    """
    __tablename__ = "configs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    protocol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    raw_config: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_config: Mapped[str] = mapped_column(Text, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # Lifecycle fields
    is_structurally_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(
        String(20), 
        default=ConfigLifecycleState.NEW.value, 
        nullable=False,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    occurrences: Mapped[list["ConfigOccurrence"]] = relationship(
        "ConfigOccurrence",
        back_populates="config",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_protocol_active', 'protocol', 'is_active'),
        Index('idx_lifecycle_state', 'lifecycle_state'),
    )
    
    def __repr__(self) -> str:
        return f"<Config(id={self.id}, protocol={self.protocol}, hash={self.config_hash[:8]}...)"


class ConfigOccurrence(Base):
    """
    Tracks where and when a configuration was found.
    
    This table allows multiple source occurrences for the same canonical configuration
    without duplicating the configuration data. Enables traceability and auditing.
    """
    __tablename__ = "config_occurrences"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("configs.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    channel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_message_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Store the raw occurrence for reference
    raw_occurrence: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Timestamps
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    config: Mapped["Config"] = relationship("Config", back_populates="occurrences")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="config_occurrences")
    
    # Unique constraint to prevent duplicate occurrences
    __table_args__ = (
        UniqueConstraint('config_id', 'channel_id', 'source_message_id', name='uq_config_channel_message'),
        Index('idx_channel_message', 'channel_id', 'source_message_id'),
    )
    
    def __repr__(self) -> str:
        return f"<ConfigOccurrence(id={self.id}, config_id={self.config_id}, channel_id={self.channel_id})>"


class CollectionRun(Base):
    """
    Tracks a collection run execution.
    
    Records statistics and status for each collection cycle.
    """
    __tablename__ = "collection_runs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False, index=True)
    
    # Statistics
    messages_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    configs_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    configs_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_removed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_configs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Error tracking
    errors: Mapped[str] = mapped_column(Text, nullable=True)
    
    # GitHub publishing status
    github_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    github_commit_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    github_error: Mapped[str] = mapped_column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<CollectionRun(id={self.id}, status={self.status}, started_at={self.started_at})>"
