"""
Enhanced scraper for Flare Developer Hub.

This script provides improved scraping capabilities specifically optimized for
the Flare Developer Hub website, with better content extraction and link preservation.
"""

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from flare_ai_rag.data_expansion.config import DataExpansionConfig, ScraperConfig
from flare_ai_rag.data_expansion.schemas import Document, DocumentMetadata

logger = logging.getLogger(__name__)

# Constants
FLARE_DEV_HUB_URL = "https://dev.flare.network/"
STORAGE_DIR = "storage/enhanced_data"
METADATA_FILE = "metadata.json"
LINKS_FILE = "links.json"


class EnhancedScraper:
    """
    Enhanced scraper for Flare Developer Hub with better content extraction and link preservation.
    """
    
    def __init__(self, config: ScraperConfig | None = None):
        """
        Initialize the enhanced scraper.
        
        Args:
            config: Scraper configuration (optional)
        """
        self.config = config or ScraperConfig(
            follow_links=True,
            follow_external_links=False,
            max_depth=3,  # Increased depth for better coverage
            request_delay=1.5,  # Slightly increased delay to be respectful
        )
        
        # Set up session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.config.user_agent,
        })
        
        # Track visited URLs to avoid duplicates
        self.visited_urls: set[str] = set()
        
        # Track all discovered links for reference
        self.all_links: dict[str, dict] = {}
        
        # Ensure storage directory exists
        os.makedirs(STORAGE_DIR, exist_ok=True)
        
        # Load existing metadata if available
        self.metadata_path = os.path.join(STORAGE_DIR, METADATA_FILE)
        self.links_path = os.path.join(STORAGE_DIR, LINKS_FILE)
        
        self.metadata = self._load_json(self.metadata_path, {})
        self.link_data = self._load_json(self.links_path, {})
    
    def _load_json(self, path: str, default: dict) -> dict:
        """Load JSON data from file or return default."""
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Error loading JSON from {path}, using default")
        return default
    
    def _save_json(self, path: str, data: dict) -> None:
        """Save JSON data to file."""
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and trailing slashes."""
        parsed = urlparse(url)
        path = parsed.path
        if path.endswith('/'):
            path = path[:-1]
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    
    def _get_page(self, url: str) -> tuple[str | None, dict | None]:
        """
        Get page content and metadata.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple of (html_content, metadata) or (None, None) if failed
        """
        try:
            response = requests.get(url, headers={"User-Agent": self.config.user_agent}, timeout=self.config.timeout)
            response.raise_for_status()
            
            # Extract metadata
            soup = BeautifulSoup(response.text, "html.parser")
            
            metadata = {
                "url": url,
                "title": soup.title.text if soup.title else "",
                "last_fetched": datetime.now().isoformat(),
            }
            
            # Try to extract description
            description_tag = soup.find("meta", attrs={"name": "description"})
            if description_tag and "content" in description_tag.attrs:
                metadata["description"] = description_tag["content"]
            
            return response.text, metadata
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None, None
    
    def _extract_content(self, html: str, url: str) -> str | None:
        """
        Extract main content from HTML.
        
        Args:
            html: HTML content
            url: Source URL
            
        Returns:
            Extracted content or None if failed
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove navigation, header, footer, etc.
            for element in soup.select("nav, header, footer, script, style, [role='navigation']"):
                element.decompose()
            
            # Try to find main content
            main_content = soup.find("main") or soup.find("article") or soup.find("div", class_="content")
            
            if main_content:
                # Convert relative links to absolute
                for a_tag in main_content.find_all("a", href=True):
                    a_tag["href"] = urljoin(url, a_tag["href"])
                    # Add a marker to indicate this is a link
                    a_tag.string = f"{a_tag.get_text()} [Link: {a_tag['href']}]"
                
                # Extract text with preserved structure
                content = main_content.get_text(separator="\n", strip=True)
                
                # Clean up excessive whitespace
                content = re.sub(r'\n{3,}', '\n\n', content)
                
                return content
            else:
                # Fallback to body content
                body = soup.find("body")
                if body:
                    for a_tag in body.find_all("a", href=True):
                        a_tag["href"] = urljoin(url, a_tag["href"])
                        a_tag.string = f"{a_tag.get_text()} [Link: {a_tag['href']}]"
                    
                    content = body.get_text(separator="\n", strip=True)
                    content = re.sub(r'\n{3,}', '\n\n', content)
                    return content
            
            return None
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """
        Extract links from HTML.
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of normalized links
        """
        links = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                
                # Skip empty links, anchors, and javascript
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                
                # Normalize URL
                absolute_url = urljoin(base_url, href)
                normalized_url = self._normalize_url(absolute_url)
                
                # Skip external links if not allowed
                if not self.config.follow_external_links:
                    base_domain = urlparse(base_url).netloc
                    link_domain = urlparse(normalized_url).netloc
                    if link_domain != base_domain:
                        # Still track external links
                        self.all_links[normalized_url] = {
                            "url": normalized_url,
                            "source": base_url,
                            "text": a_tag.get_text(strip=True),
                            "external": True,
                            "visited": False
                        }
                        continue
                
                # Add link metadata
                self.all_links[normalized_url] = {
                    "url": normalized_url,
                    "source": base_url,
                    "text": a_tag.get_text(strip=True),
                    "external": False,
                    "visited": normalized_url in self.visited_urls
                }
                
                # Add to list if not already present
                if normalized_url not in links:
                    links.append(normalized_url)
            
        except Exception as e:
            logger.error(f"Error extracting links from {base_url}: {e}")
        
        return links
    
    def _create_document(self, url: str, content: str, metadata: dict) -> Document:
        """
        Create a document from scraped content.
        
        Args:
            url: Source URL
            content: Extracted content
            metadata: Page metadata
            
        Returns:
            Document object
        """
        # Generate a stable ID based on URL
        doc_id = hashlib.md5(url.encode()).hexdigest()
        
        # Create document metadata
        doc_metadata = DocumentMetadata(
            source_name="Flare Developer Hub",
            source_url=FLARE_DEV_HUB_URL,
            url=url,
            title=metadata.get("title", ""),
            description=metadata.get("description", ""),
            author="",
            date="",
            last_updated=metadata.get("last_fetched", ""),
            type="documentation",
            section="",
            subsection="",
            tags=[],
            language="en",
            version="",
            priority=1,
            extra={}
        )
        
        # Create document
        document = Document(
            id=doc_id,
            content=content,
            metadata=doc_metadata
        )
        
        return document
    
    def _save_document(self, document: Document) -> str:
        """
        Save document to file.
        
        Args:
            document: Document to save
            
        Returns:
            Path to saved file
        """
        # Create directory for source
        source_dir = os.path.join(STORAGE_DIR, "flare_developer_hub")
        os.makedirs(source_dir, exist_ok=True)
        
        # Save document
        file_path = os.path.join(source_dir, f"{document.id}.json")
        with open(file_path, "w") as f:
            # Use model_dump() instead of dict() for Pydantic v2 compatibility
            try:
                # Try Pydantic v2 method first
                json.dump(document.model_dump(), f, indent=2)
            except AttributeError:
                # Fall back to Pydantic v1 method
                json.dump(document.dict(), f, indent=2)
        
        # Update metadata
        self.metadata[document.id] = {
            "url": document.metadata.url,
            "title": document.metadata.title,
            "last_updated": document.metadata.last_updated,
            "file_path": file_path
        }
        
        # Save metadata
        self._save_json(self.metadata_path, self.metadata)
        
        return file_path
    
    def crawl(self, start_url: str = FLARE_DEV_HUB_URL, max_pages: int = 50) -> list[Document]:
        """
        Crawl Flare Developer Hub and extract content.
        
        Args:
            start_url: URL to start crawling from
            max_pages: Maximum number of pages to crawl
            
        Returns:
            List of extracted documents
        """
        logger.info(f"Starting enhanced crawl of {start_url} (max {max_pages} pages)")
        
        # Queue of URLs to visit
        queue = [(start_url, 0)]  # (url, depth)
        
        # List of extracted documents
        documents = []
        
        # Counter for pages visited
        pages_visited = 0
        
        while queue and pages_visited < max_pages:
            # Get next URL from queue
            url, depth = queue.pop(0)
            
            # Skip if already visited
            if url in self.visited_urls:
                continue
            
            # Skip if depth exceeds max_depth
            if depth > self.config.max_depth:
                continue
            
            # Mark as visited
            self.visited_urls.add(url)
            self.all_links.setdefault(url, {})["visited"] = True
            
            logger.info(f"Crawling {url} (depth {depth}, visited {pages_visited+1}/{max_pages})")
            
            # Get page content
            html, metadata = self._get_page(url)
            if not html or not metadata:
                continue
            
            # Extract content
            content = self._extract_content(html, url)
            if not content:
                continue
            
            # Create document
            document = self._create_document(url, content, metadata)
            
            # Save document
            file_path = self._save_document(document)
            logger.info(f"Saved document to {file_path}")
            
            # Add to list
            documents.append(document)
            
            # Increment counter
            pages_visited += 1
            
            # Extract links
            links = self._extract_links(html, url)
            
            # Add links to queue
            for link in links:
                if link not in self.visited_urls:
                    queue.append((link, depth + 1))
            
            # Save link data
            self._save_json(self.links_path, self.all_links)
            
            # Respect delay
            time.sleep(self.config.request_delay)
        
        logger.info(f"Crawl complete. Visited {pages_visited} pages, extracted {len(documents)} documents")
        
        return documents


def main():
    """Main entry point for enhanced scraper."""
    logging.basicConfig(level=logging.INFO)
    
    # Create scraper
    scraper = EnhancedScraper()
    
    # Crawl Flare Developer Hub
    documents = scraper.crawl()
    
    # Print summary
    print(f"Crawled {len(scraper.visited_urls)} pages")
    print(f"Extracted {len(documents)} documents")
    print(f"Discovered {len(scraper.all_links)} links")
    print(f"Data saved to {STORAGE_DIR}")


if __name__ == "__main__":
    main() 