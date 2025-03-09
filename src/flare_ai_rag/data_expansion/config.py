"""
Configuration classes for data expansion.

This module contains configuration classes for scrapers and processors.
"""

from dataclasses import dataclass

@dataclass
class ScraperConfig:
    """Configuration for web scrapers."""
    
    user_agent: str
    """User agent string to use for requests."""
    
    follow_links: bool = False
    """Whether to follow links found in scraped pages."""
    
    follow_external_links: bool = False
    """Whether to follow links to external domains."""
    
    request_delay: float = 0.0
    """Delay between requests in seconds."""
    
    max_depth: int = 1
    """Maximum depth to follow links."""
    
    timeout: int = 30
    """Request timeout in seconds."""
    
    max_retries: int = 3
    """Maximum number of retries for failed requests."""
    
    headers: dict | None = None
    """Additional headers to send with requests."""

@dataclass
class ProcessorConfig:
    """Configuration for document processors."""
    
    chunk_size: int = 1000
    """Maximum size of document chunks in characters."""
    
    overlap: int = 100
    """Number of characters to overlap between chunks."""
    
    min_chunk_size: int = 100
    """Minimum size of document chunks in characters."""
    
    preserve_sections: bool = True
    """Whether to preserve document sections when chunking.""" 