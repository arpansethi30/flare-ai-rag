"""
Base scraper interface for data expansion.

This module provides the base interface for scrapers used in data expansion.
"""

from collections.abc import Generator

from flare_ai_rag.data_expansion.config import ScraperConfig
from flare_ai_rag.data_expansion.schemas import Document

class BaseScraper:
    """Base class for scrapers."""
    
    def __init__(self, config: ScraperConfig):
        """
        Initialize the scraper.
        
        Args:
            config: Scraper configuration
        """
        self.config = config
    
    def scrape(self, url: str, source_name: str) -> Generator[Document, None, None]:
        """
        Scrape a URL for documents.
        
        Args:
            url: URL to scrape
            source_name: Name of the source
            
        Returns:
            Generator yielding documents
        """
        raise NotImplementedError("Subclasses must implement scrape()")
    
    def get_links(self, url: str, html: str) -> list[str]:
        """
        Extract links from HTML.
        
        Args:
            url: Base URL
            html: HTML content
            
        Returns:
            List of links
        """
        raise NotImplementedError("Subclasses must implement get_links()") 