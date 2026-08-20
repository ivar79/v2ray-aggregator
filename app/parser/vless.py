"""
VLESS protocol parser and canonicalizer.

VLESS format: vless://uuid@address:port?params#fragment
"""
import re
import urllib.parse
from typing import Optional, Dict, Any

from app.parser.base import BaseParser, ParsedConfig


class VLESSParser(BaseParser):
    """Parser for VLESS protocol configurations."""
    
    # VLESS protocol prefix
    PREFIX = "vless://"
    
    def __init__(self):
        """Initialize VLESS parser."""
        super().__init__(protocol='vless')
        # Pattern to match vless:// URLs
        self.pattern = re.compile(r'vless://[a-f0-9-]+@[^#\s]+(?:#[^\s]*)?')
    
    def extract(self, text: str) -> list[str]:
        """
        Extract VLESS configurations from text.
        
        Args:
            text: Text to search for VLESS configurations
            
        Returns:
            List of raw VLESS configuration strings
        """
        matches = self.pattern.findall(text)
        return matches
    
    def parse(self, raw: str) -> Optional[ParsedConfig]:
        """
        Parse a raw VLESS configuration string.
        
        Args:
            raw: Raw VLESS configuration (vless://uuid@address:port?params#fragment)
            
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
            
            # Parse URL: uuid@address:port?params
            if '@' not in url_part:
                return None
            
            uuid_part, rest = url_part.split('@', 1)
            
            # Split address:port from params
            if '?' in rest:
                address_port, params_str = rest.split('?', 1)
                params = urllib.parse.parse_qs(params_str)
            else:
                address_port = rest
                params = {}
            
            # Split address:port
            if ':' not in address_port:
                return None
            
            address, port_str = address_port.rsplit(':', 1)
            port = int(port_str)
            
            # Build fields dictionary
            fields = {
                'uuid': uuid_part,
                'address': address,
                'port': port,
                'params': dict(params),
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
        Canonicalize VLESS configuration.
        
        Canonicalization steps:
        1. URL decode field values
        2. Sort query parameters alphabetically
        3. Normalize parameter values (single values instead of lists)
        4. Exclude fragment (metadata) from canonical representation
        
        Args:
            parsed: Parsed VLESS configuration
            
        Returns:
            Canonicalized ParsedConfig
        """
        canonical_fields = {}
        fields = parsed.fields
        
        # Copy basic fields
        canonical_fields['uuid'] = fields['uuid']
        canonical_fields['address'] = urllib.parse.unquote(fields['address'])
        canonical_fields['port'] = fields['port']
        
        # Canonicalize parameters: sort keys, convert lists to single values
        if 'params' in fields:
            canonical_params = {}
            for key in sorted(fields['params'].keys()):
                values = fields['params'][key]
                if isinstance(values, list) and values:
                    # Take first value (most params are single-value)
                    canonical_params[key] = urllib.parse.unquote(values[0])
                elif values:
                    canonical_params[key] = urllib.parse.unquote(str(values))
            canonical_fields['params'] = canonical_params
        
        # Note: We exclude 'fragment' from canonical representation as it's metadata
        
        return ParsedConfig(
            protocol=parsed.protocol,
            raw=parsed.raw,
            fields=canonical_fields
        )
    
    def validate(self, parsed: ParsedConfig) -> bool:
        """
        Validate VLESS configuration structure.
        
        Args:
            parsed: Parsed VLESS configuration
            
        Returns:
            True if structurally valid, False otherwise
        """
        fields = parsed.fields
        
        try:
            # Check required fields
            if 'uuid' not in fields or 'address' not in fields or 'port' not in fields:
                return False
            
            # Validate UUID format (basic check)
            uuid = fields['uuid']
            if not isinstance(uuid, str) or len(uuid) < 32:
                return False
            
            # Validate address
            address = fields['address']
            if not isinstance(address, str) or not address:
                return False
            
            # Validate port
            port = int(fields['port'])
            if port < 1 or port > 65535:
                return False
            
            # Validate params if present (can be dict or empty)
            if 'params' in fields and fields['params']:
                params = fields['params']
                if not isinstance(params, dict):
                    return False
            
            return True
            
        except (ValueError, TypeError, KeyError):
            return False
