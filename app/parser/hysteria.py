"""
Hysteria protocol parser and canonicalizer.

Hysteria format: hysteria://server:port?key=value&key2=value2#fragment
"""
import re
import urllib.parse
from typing import Optional, Dict, Any

from app.parser.base import BaseParser, ParsedConfig


class HysteriaParser(BaseParser):
    """Parser for Hysteria protocol configurations."""
    
    # Hysteria protocol prefix
    PREFIX = "hysteria://"
    
    def __init__(self):
        """Initialize Hysteria parser."""
        super().__init__(protocol='hysteria')
        # Pattern to match hysteria:// URLs
        self.pattern = re.compile(r'hysteria://[^#\s]+(?:#[^\s]*)?')
    
    def extract(self, text: str) -> list[str]:
        """
        Extract Hysteria configurations from text.
        
        Args:
            text: Text to search for Hysteria configurations
            
        Returns:
            List of raw Hysteria configuration strings
        """
        matches = self.pattern.findall(text)
        return matches
    
    def parse(self, raw: str) -> Optional[ParsedConfig]:
        """
        Parse a raw Hysteria configuration string.
        
        Args:
            raw: Raw Hysteria configuration (hysteria://server:port?params#fragment)
            
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
            
            # Split server:port from params
            if '?' in url_part:
                server_port, params_str = url_part.split('?', 1)
                params = urllib.parse.parse_qs(params_str)
            else:
                server_port = url_part
                params = {}
            
            # Split server:port
            if ':' not in server_port:
                return None
            
            server, port_str = server_port.rsplit(':', 1)
            port = int(port_str)
            
            # Build fields dictionary
            fields = {
                'server': server,
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
        Canonicalize Hysteria configuration.
        
        Canonicalization steps:
        1. URL decode field values
        2. Sort query parameters alphabetically
        3. Normalize parameter values (single values instead of lists)
        4. Exclude fragment (metadata) from canonical representation
        
        Args:
            parsed: Parsed Hysteria configuration
            
        Returns:
            Canonicalized ParsedConfig
        """
        canonical_fields = {}
        fields = parsed.fields
        
        # Copy basic fields
        canonical_fields['server'] = urllib.parse.unquote(fields['server'])
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
        Validate Hysteria configuration structure.
        
        Args:
            parsed: Parsed Hysteria configuration
            
        Returns:
            True if structurally valid, False otherwise
        """
        fields = parsed.fields
        
        try:
            # Check required fields
            if 'server' not in fields or 'port' not in fields:
                return False
            
            # Validate server
            server = fields['server']
            if not isinstance(server, str) or not server:
                return False
            
            # Validate port
            port = int(fields['port'])
            if port < 1 or port > 65535:
                return False
            
            # Validate params if present
            if 'params' in fields:
                params = fields['params']
                if not isinstance(params, dict):
                    return False
            
            return True
            
        except (ValueError, TypeError, KeyError):
            return False
