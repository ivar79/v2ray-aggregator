"""
Base parser interface for V2Ray configuration protocols.

All protocol-specific parsers must implement this interface to ensure
consistent behavior across different protocols.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
import hashlib
import json


@dataclass
class ParsedConfig:
    """
    Represents a parsed V2Ray configuration.
    
    Contains the normalized fields that are critical for connection.
    """
    protocol: str
    raw: str
    fields: Dict[str, Any]
    
    def __hash__(self):
        """Make ParsedConfig hashable based on canonical representation."""
        return hash(self.canonical_representation)
    
    @property
    def canonical_representation(self) -> str:
        """
        Generate canonical string representation for hashing.
        
        This should be overridden by protocol-specific parsers to provide
        a deterministic representation that connection-critical fields only.
        """
        # Default implementation: JSON with sorted keys
        return json.dumps(self.fields, sort_keys=True)
    
    def get_hash(self) -> str:
        """
        Generate SHA-256 hash of canonical representation.
        
        Returns:
            SHA-256 hash as hexadecimal string
        """
        canonical = self.canonical_representation.encode('utf-8')
        return hashlib.sha256(canonical).hexdigest()


class BaseParser(ABC):
    """
    Base class for protocol-specific parsers.
    
    Each protocol parser must implement:
    - extract: Find configurations in text
    - parse: Parse raw configuration into structured data
    - canonicalize: Convert parsed data to canonical form
    - validate: Check structural validity
    """
    
    def __init__(self, protocol: str):
        """
        Initialize parser.
        
        Args:
            protocol: Protocol name (e.g., 'vmess', 'vless')
        """
        self.protocol = protocol
    
    @abstractmethod
    def extract(self, text: str) -> list[str]:
        """
        Extract raw configuration strings from text.
        
        Args:
            text: Text to search for configurations
            
        Returns:
            List of raw configuration strings found
        """
        pass
    
    @abstractmethod
    def parse(self, raw: str) -> Optional[ParsedConfig]:
        """
        Parse a raw configuration string into structured data.
        
        Args:
            raw: Raw configuration string
            
        Returns:
            ParsedConfig object or None if parsing fails
        """
        pass
    
    @abstractmethod
    def canonicalize(self, parsed: ParsedConfig) -> ParsedConfig:
        """
        Convert parsed configuration to canonical form.
        
        This should:
        - Normalize field values (e.g., URL decoding)
        - Sort parameters consistently
        - Exclude non-critical metadata (e.g., display names)
        - Ensure deterministic output
        
        Args:
            parsed: Parsed configuration
            
        Returns:
            ParsedConfig with canonicalized fields
        """
        pass
    
    @abstractmethod
    def validate(self, parsed: ParsedConfig) -> bool:
        """
        Validate structural correctness of parsed configuration.
        
        This should check:
        - Required fields are present
        - Field values are valid
        - Data types are correct
        
        Args:
            parsed: Parsed configuration
            
        Returns:
            True if structurally valid, False otherwise
        """
        pass
    
    def process(self, raw: str) -> Optional[ParsedConfig]:
        """
        Complete processing pipeline: parse → canonicalize → validate.
        
        Args:
            raw: Raw configuration string
            
        Returns:
            Validated and canonicalized ParsedConfig, or None if invalid
        """
        # Parse
        parsed = self.parse(raw)
        if parsed is None:
            return None
        
        # Canonicalize
        canonicalized = self.canonicalize(parsed)
        
        # Validate
        if not self.validate(canonicalized):
            return None
        
        return canonicalized
    
    def extract_and_process(self, text: str) -> list[ParsedConfig]:
        """
        Extract and process all configurations from text.
        
        Args:
            text: Text to search for configurations
            
        Returns:
            List of valid, canonicalized ParsedConfig objects
        """
        raw_configs = self.extract(text)
        processed = []
        
        for raw in raw_configs:
            result = self.process(raw)
            if result is not None:
                processed.append(result)
        
        return processed
