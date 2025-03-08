"""
Web scrapers for the data expansion module.

This module contains web scrapers for collecting documentation from various sources.
"""

from .base import BaseScraper
from .web_scraper import WebScraper

__all__ = ["BaseScraper", "WebScraper"] 