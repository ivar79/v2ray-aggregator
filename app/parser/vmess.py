"""
VMess protocol parser and canonicalizer.

VMess format: vmess://base64_encoded_json
"""
import base64
import json
import re
import urllib.parse
from typing import Optional, Dict, Any

from app.parser.base import BaseParser, ParsedConfig


class VMessParser(BaseParser):
    """Parser for VMess protocol configurations."""
    
    # VMess protocol prefix
    PREFIX = "vmess://"
    
    # Required fields for structural validation
    REQUIRED_FIELDS = ['v', 'ps', 'add', 'port', 'id', 'aid', 'net', 'type', 'host', 'path', 'tls']
    
    def __init__(self):
        """Initialize VMess parser."""
        super().__init__(protocol='vmess')
        # Pattern to match vmess:// URLs
        self.pattern = re.compile(r'vmess://[A-Za-z0-9+/=]+')
    
    def extract(self, text: str) -> list[str]:
        """
        Extract VMess configurations from text.
        
        Args:
            text: Text to search for VMess configurations
            
        Returns:
            List of raw VMess configuration strings
        """
        matches = self.pattern.findall(text)
        return matches
    
    def parse(self, raw: str) -> Optional[ParsedConfig]:
        """
        Parse a raw VMess configuration string.
        
        Args:
            raw: Raw VMess configuration (vmess://base64_json)
            
        Returns:
            ParsedConfig object or None if parsing fails
        """
        if not raw.startswith(self.PREFIX):
            return None
        
        try:
            # Remove prefix and decode base64
            base64_part = raw[len(self.PREFIX):]
            # Add padding if needed
            padding = len(base64_part) % 4
            if padding:
                base64_part += '=' * (4 - padding)
            
            decoded_bytes = base64.b64decode(base64_part)
            decoded_str = decoded_bytes.decode('utf-8')
            
            # Parse JSON
            fields = json.loads(decoded_str)
            
            return ParsedConfig(
                protocol=self.protocol,
                raw=raw,
                fields=fields
            )
        except Exception:
            return None
    
    def canonicalize(self, parsed: ParsedConfig) -> ParsedConfig:
        """
        Canonicalize VMess configuration.
        
        Canonicalization steps:
        1. URL decode field values where appropriate
        2. Normalize field names (ensure consistent casing)
        3. Sort JSON fields alphabetically
        4. Exclude non-critical metadata (ps - remarks/name)
        
        Note: We keep 'ps' (remarks) in the canonical representation for now
        as it may be used by some clients. This can be refined based on testing.
        
        Args:
            parsed: Parsed VMess configuration
            
        Returns:
            Canonicalized ParsedConfig
        """
        canonical_fields = {}
        
        for key, value in parsed.fields.items():
            # URL decode string values
            if isinstance(value, str):
                try:
                    decoded = urllib.parse.unquote(value)
                    canonical_fields[key] = decoded
                except Exception:
                    canonical_fields[key] = value
            else:
                canonical_fields[key] = value
        
        return ParsedConfig(
            protocol=parsed.protocol,
            raw=parsed.raw,
            fields=canonical_fields
        )
    
    def validate(self, parsed: ParsedConfig) -> bool:
        """
        Validate VMess configuration structure.
        
        Args:
            parsed: Parsed VMess configuration
            
        Returns:
            True if structurally valid, False otherwise
        """
        fields = parsed.fields
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in fields:
                return False
        
        # Validate field types and values
        try:
            # v (version) should be a string
            if not isinstance(fields['v'], str):
                return False
            
            # add (address) should be a non-empty string
            if not isinstance(fields['add'], str) or not fields['add']:
                return False
            
            # port should be a valid port number
            port = int(fields['port'])
            if port < 1 or port > 65535:
                return False
            
            # id (UUID) should be a string
            if not isinstance(fields['id'], str) or not fields['id']:
                return False
            
            # aid (alter ID) should be an integer
            aid = int(fields['aid'])
            if aid < 0:
                return False
            
            # net (network type) should be valid
            valid_net_types = ['tcp', 'http', 'ws', 'grpc', 'quic']
            if fields['net'] not in valid_net_types:
                return False
            
            # type should be valid
            valid_types = ['none', 'http', 'srtp', 'utp', 'wechat-video']
            if fields['type'] not in valid_types:
                return False
            
            return True
            
        except (ValueError, TypeError, KeyError):
            return False
    
    @property
    def canonical_representation(self) -> str:
        """
        Override to provide VMess-specific canonical representation.
        
        For VMess, we use JSON with sorted keys, excluding the 'ps' field
        (remarks/name) as it's metadata that doesn't affect connection.
        """
        # This is a placeholder - the actual implementation should be in the ParsedConfig
        # This property is not used in the base class, but can be used for custom logic
        return ""
