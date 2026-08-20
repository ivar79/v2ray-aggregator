"""
Shadowsocks protocol parser and canonicalizer.

Shadowsocks format: ss://base64(method:password)@address:port#fragment
"""
import base64
import re
import urllib.parse
from typing import Optional, Dict, Any

from app.parser.base import BaseParser, ParsedConfig


class ShadowsocksParser(BaseParser):
    """Parser for Shadowsocks protocol configurations."""
    
    # Shadowsocks protocol prefix
    PREFIX = "ss://"
    
    def __init__(self):
        """Initialize Shadowsocks parser."""
        super().__init__(protocol='shadowsocks')
        # Pattern to match ss:// URLs
        self.pattern = re.compile(r'ss://[A-Za-z0-9+/=]+@[^#\s]+(?:#[^\s]*)?')
    
    def extract(self, text: str) -> list[str]:
        """
        Extract Shadowsocks configurations from text.
        
        Args:
            text: Text to search for Shadowsocks configurations
            
        Returns:
            List of raw Shadowsocks configuration strings
        """
        matches = self.pattern.findall(text)
        return matches
    
    def parse(self, raw: str) -> Optional[ParsedConfig]:
        """
        Parse a raw Shadowsocks configuration string.
        
        Args:
            raw: Raw Shadowsocks configuration (ss://base64@address:port#fragment)
            
        Returns:
            ParsedConfig object or None if parsing fails
        """
        if not raw.startswith(self.PREFIX):
            return None
        
        try:
            # Remove prefix
            url_part = raw[len(self.PREFIX):]
            
            # Split fragment
            if '#' in url_part:
                url_part, fragment = url_part.split('#', 1)
                fragment = urllib.parse.unquote(fragment)
            else:
                fragment = None
            
            # Parse URL: base64@address:port
            if '@' not in url_part:
                return None
            
            base64_part, address_port = url_part.split('@', 1)
            
            # Decode base64 to get method:password
            # Add padding if needed
            padding = len(base64_part) % 4
            if padding:
                base64_part += '=' * (4 - padding)
            
            decoded_bytes = base64.b64decode(base64_part)
            decoded_str = decoded_bytes.decode('utf-8')
            
            # Split method:password
            if ':' not in decoded_str:
                return None
            
            method, password = decoded_str.split(':', 1)
            
            # Split address:port
            if ':' not in address_port:
                return None
            
            address, port_str = address_port.rsplit(':', 1)
            port = int(port_str)
            
            # Build fields dictionary
            fields = {
                'method': method,
                'password': password,
                'address': address,
                'port': port,
                'fragment': fragment,
            }
            
            return ParsedConfig(
                protocol=self.protocol,
                raw=raw,
                fields=fields
            )
        except Exception:
            return None
    
    def canonicalize(self, parsed: ParsedConfig) -> ParsedConfig:
        """
        Canonicalize Shadowsocks configuration.
        
        Canonicalization steps:
        1. URL decode field values
        2. Normalize method to lowercase
        3. Exclude fragment (metadata) from canonical representation
        
        Args:
            parsed: Parsed Shadowsocks configuration
            
        Returns:
            Canonicalized ParsedConfig
        """
        canonical_fields = {}
        fields = parsed.fields
        
        # Copy and normalize basic fields
        canonical_fields['method'] = fields['method'].lower()
        canonical_fields['password'] = fields['password']
        canonical_fields['address'] = urllib.parse.unquote(fields['address'])
        canonical_fields['port'] = fields['port']
        
        # Note: We exclude 'fragment' from canonical representation as it's metadata
        
        return ParsedConfig(
            protocol=parsed.protocol,
            raw=parsed.raw,
            fields=canonical_fields
        )
    
    def validate(self, parsed: ParsedConfig) -> bool:
        """
        Validate Shadowsocks configuration structure.
        
        Args:
            parsed: Parsed Shadowsocks configuration
            
        Returns:
            True if structurally valid, False otherwise
        """
        fields = parsed.fields
        
        try:
            # Check required fields
            if 'method' not in fields or 'password' not in fields or 'address' not in fields or 'port' not in fields:
                return False
            
            # Validate method
            method = fields['method']
            if not isinstance(method, str) or not method:
                return False
            
            # Common Shadowsocks methods
            valid_methods = [
                'aes-128-gcm', 'aes-192-gcm', 'aes-256-gcm',
                'aes-128-cfb', 'aes-192-cfb', 'aes-256-cfb',
                'aes-128-ctr', 'aes-192-ctr', 'aes-256-ctr',
                'chacha20-ietf-poly1305', 'xchacha20-ietf-poly1305',
                'rc4-md5', 'bf-cfb', 'camellia-128-cfb',
                'camellia-192-cfb', 'camellia-256-cfb',
                'salsa20', 'chacha20'
            ]
            # Allow any method for flexibility, but check it's not empty
            if not method.strip():
                return False
            
            # Validate password
            password = fields['password']
            if not isinstance(password, str) or not password:
                return False
            
            # Validate address
            address = fields['address']
            if not isinstance(address, str) or not address:
                return False
            
            # Validate port
            port = int(fields['port'])
            if port < 1 or port > 65535:
                return False
            
            return True
            
        except (ValueError, TypeError, KeyError):
            return False
