"""
Web scraper for data expansion.

This module provides a web scraper for collecting data from websites.
"""

import hashlib
import logging
import re
import time
from datetime import datetime
from collections.abc import Generator
from typing import Any, override
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from flare_ai_rag.data_expansion.config import ScraperConfig
from flare_ai_rag.data_expansion.schemas import Document, DocumentMetadata
from flare_ai_rag.data_expansion.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class WebScraper(BaseScraper):
    """
    Scraper for web documentation.
    
    This class handles scraping web pages using BeautifulSoup and requests.
    """
    
    def __init__(self, config: ScraperConfig):
        """
        Initialize the web scraper.
        
        Args:
            config: Scraper configuration
        """
        super().__init__(config)
        
        # Set up session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.config.user_agent,
        })
        
        # Maximum number of consecutive failures before stopping
        self.max_fails = 5
    
    @override
    def scrape(self, url: str, source_name: str) -> Generator[Document, None, None]:
        """
        Scrape content from a URL.
        
        Args:
            url: URL to scrape
            source_name: Name of the source
            
        Yields:
            Document objects
        """
        # Track visited URLs to avoid duplicates
        visited = set()
        
        # Queue of URLs to visit
        queue = [url]
        
        # Track depth
        depth_map = {url: 0}
        
        # Track consecutive failures
        consecutive_fails = 0
        
        while queue and consecutive_fails < self.max_fails:
            # Get next URL
            current_url = queue.pop(0)
            
            # Skip if already visited
            if current_url in visited:
                continue
            
            # Mark as visited
            visited.add(current_url)
            
            # Get current depth
            current_depth = depth_map.get(current_url, 0)
            
            # Skip if exceeds max depth
            if current_depth > self.config.max_depth:
                continue
            
            try:
                # Get content
                response = self._get_with_retry(current_url)
                if not response:
                    consecutive_fails += 1
                    continue
                
                # Reset failure counter on success
                consecutive_fails = 0
                
                # Parse content
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Extract metadata
                title = self._extract_title(soup)
                description = self._extract_description(soup)
                author = self._extract_author(soup)
                date = self._extract_date(soup)
                last_updated = self._extract_last_updated(soup)
                content, raw_html = self._extract_sections(soup, current_url)
                tags = self._extract_tags(soup)
                language = self._extract_language(soup)
                version = self._extract_version(soup)
                
                # Skip if no content
                if not content:
                    logger.warning(f"No content found at {current_url}")
                    continue
                
                # Create document ID
                doc_id = hashlib.md5(current_url.encode()).hexdigest()
                
                # Create metadata
                metadata = DocumentMetadata(
                    source_name=source_name,
                    source_url=current_url,
                    url=current_url,
                    title=title,
                    description=description,
                    author=author,
                    date=date,
                    last_updated=last_updated,
                    tags=tags,
                    language=language,
                    version=version,
                )
                
                # Create document
                document = Document(
                    id=doc_id,
                    content=content,
                    metadata=metadata,
                    raw_html=raw_html,
                )
                
                # Yield document
                yield document
                
                # Get links if configured to follow
                if self.config.follow_links:
                    links = self.get_links(current_url, response.text)
                    for link in links:
                        # Skip if already visited
                        if link in visited:
                            continue
                        
                        # Add to queue with incremented depth
                        queue.append(link)
                        depth_map[link] = current_depth + 1
                
                # Respect delay between requests
                if self.config.request_delay > 0:
                    time.sleep(self.config.request_delay)
                
            except Exception as e:
                logger.error(f"Error scraping {current_url}: {e}")
                consecutive_fails += 1
                continue
        
        if consecutive_fails >= self.max_fails:
            logger.warning(f"Stopped after {consecutive_fails} consecutive failures")
    
    @override
    def get_links(self, url: str, html: str) -> list[str]:
        """
        Extract links from HTML.
        
        Args:
            url: Base URL
            html: HTML content
            
        Returns:
            List of links
        """
        links = []
        
        try:
            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # Find all links
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                
                # Skip empty links, anchors, and javascript
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                
                # Normalize URL
                absolute_url = urljoin(url, href)
                normalized_url = self._normalize_url(absolute_url)
                
                # Skip external links if not allowed
                if not self.config.follow_external_links:
                    base_domain = urlparse(url).netloc
                    link_domain = urlparse(normalized_url).netloc
                    if link_domain != base_domain:
                        continue
                
                # Add to list if not already present
                if normalized_url not in links:
                    links.append(normalized_url)
            
            logger.debug(f"Found {len(links)} links on {url}")
        except Exception as e:
            logger.error(f"Error extracting links from {url}: {e}")
        
        return links
    
    def _get_with_retry(self, url: str) -> requests.Response | None:
        """
        Get a URL with retry logic.
        
        Args:
            url: URL to get
            
        Returns:
            Response object or None
        """
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                if response.status_code == 200:
                    return response
                
                logger.warning(f"HTTP error {response.status_code} for {url}")
                if response.status_code == 429:  # Too many requests
                    # Exponential backoff
                    wait_time = (2 ** attempt) + 1
                    logger.info(f"Rate limited, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                    continue
                
                return None
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for {url}: {str(e)}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(1)
                    continue
                return None
        
        return None
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize a URL.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        # Add protocol if missing
        if not url.startswith("http"):
            url = "https://" + url
        
        # Remove trailing slash
        if url.endswith("/"):
            url = url[:-1]
        
        # Remove fragments
        url = url.split("#")[0]
        
        return url
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """
        Extract title from a page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Title string
        """
        # Try title tag first
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        
        # Try h1
        h1_tag = soup.find("h1")
        if h1_tag and h1_tag.string:
            return h1_tag.string.strip()
        
        return ""
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """
        Extract description from a page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Description string
        """
        # Try meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and "content" in meta_desc.attrs:
            return meta_desc["content"].strip()
        
        # Try open graph description
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and "content" in og_desc.attrs:
            return og_desc["content"].strip()
        
        return ""
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """
        Extract author from a page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Author string
        """
        # Try meta author
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and "content" in meta_author.attrs:
            return meta_author["content"].strip()
        
        # Try author link
        author_link = soup.find("a", attrs={"rel": "author"})
        if author_link and author_link.string:
            return author_link.string.strip()
        
        # Try byline
        byline = soup.find(class_=re.compile("author|byline", re.IGNORECASE))
        if byline and byline.string:
            return byline.string.strip()
        
        return ""
    
    def _extract_date(self, soup: BeautifulSoup) -> str:
        """
        Extract publication date from a page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Date string
        """
        # Try meta date
        meta_date = soup.find("meta", attrs={"name": re.compile("date|published", re.IGNORECASE)})
        if meta_date and "content" in meta_date.attrs:
            return meta_date["content"].strip()
        
        # Try time tag
        time_tag = soup.find("time")
        if time_tag and "datetime" in time_tag.attrs:
            return time_tag["datetime"].strip()
        elif time_tag and time_tag.string:
            return time_tag.string.strip()
        
        # Try date in text
        date_div = soup.find(class_=re.compile("date|published", re.IGNORECASE))
        if date_div and date_div.string:
            return date_div.string.strip()
        
        return ""
    
    def _extract_last_updated(self, soup: BeautifulSoup) -> str:
        """
        Extract last updated date from a page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Last updated string
        """
        # Try meta updated
        meta_updated = soup.find("meta", attrs={"name": re.compile("updated|modified", re.IGNORECASE)})
        if meta_updated and "content" in meta_updated.attrs:
            return meta_updated["content"].strip()
        
        # Try time tag with updated class
        updated_time = soup.find("time", class_=re.compile("updated|modified", re.IGNORECASE))
        if updated_time and "datetime" in updated_time.attrs:
            return updated_time["datetime"].strip()
        
        # Try updated div
        updated_div = soup.find(class_=re.compile("updated|modified|last-modified", re.IGNORECASE))
        if updated_div and updated_div.string:
            return updated_div.string.strip()
        
        return ""
    
    def _extract_sections(self, soup: BeautifulSoup, url: str) -> tuple[str, str]:
        """
        Extract content sections from HTML.
        
        Args:
            soup: BeautifulSoup object
            url: URL of the page
            
        Returns:
            Tuple of (content, raw_html)
        """
        # Get the raw HTML
        raw_html = str(soup)
        
        # Extract main content
        main_content = ""
        
        # Try to find the main content area
        main_selectors = [
            "main",
            "article",
            "#content",
            ".content",
            "#main",
            ".main",
            ".post-content",
            ".entry-content",
            ".article-content",
            ".markdown-body",  # GitHub style
        ]
        
        # Try each selector
        for selector in main_selectors:
            main_element = soup.select_one(selector)
            if main_element:
                main_content = main_element.get_text(separator="\n", strip=True)
                break
        
        # If no main content found, use the body
        if not main_content:
            body = soup.find("body")
            if body:
                main_content = body.get_text(separator="\n", strip=True)
        
        # If still no content, use the whole document
        if not main_content:
            main_content = soup.get_text(separator="\n", strip=True)
        
        # Try to extract document structure
        structured_content = ""
        
        # Extract headings and their content
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        
        if headings:
            # Get the path from the URL to use as a title prefix
            path_parts = urlparse(url).path.strip("/").split("/")
            
            # Add a title based on the URL path if no title found
            if not soup.title:
                if path_parts:
                    structured_content += f"# {path_parts[-1].replace('-', ' ').title()}\n\n"
            
            # Process each heading
            for heading in headings:
                # Get heading level
                level = int(heading.name[1])
                
                # Add heading to structured content
                structured_content += f"{'#' * level} {heading.get_text().strip()}\n\n"
                
                # Get content until next heading
                content = []
                for sibling in heading.find_next_siblings():
                    if sibling.name and sibling.name.startswith("h") and len(sibling.name) == 2:
                        break
                    if sibling.name in ["p", "ul", "ol", "pre", "blockquote", "table"]:
                        content.append(sibling.get_text(separator="\n", strip=True))
                
                # Add content
                if content:
                    structured_content += "\n".join(content) + "\n\n"
        
        # Use structured content if available, otherwise use main content
        final_content = structured_content if structured_content else main_content
        
        return final_content, raw_html
    
    def _extract_tags(self, soup: BeautifulSoup) -> list[str]:
        """
        Extract tags from a page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of tags
        """
        tags = []
        
        # Try meta keywords
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords and "content" in meta_keywords.attrs:
            keywords = meta_keywords["content"].split(",")
            tags.extend([k.strip() for k in keywords if k.strip()])
        
        # Try tag links
        tag_links = soup.find_all("a", class_=re.compile("tag", re.IGNORECASE))
        for tag in tag_links:
            if tag.string:
                tags.append(tag.string.strip())
        
        return tags
    
    def _extract_language(self, soup: BeautifulSoup) -> str:
        """
        Extract language from a page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Language code
        """
        # Try html lang attribute
        html = soup.find("html")
        if html and "lang" in html.attrs:
            return html["lang"].strip().split("-")[0]  # Just the language part, not region
        
        return "en"  # Default to English
    
    def _extract_version(self, soup: BeautifulSoup) -> str:
        """
        Extract version information from a page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Version string
        """
        # Try version in text
        version_div = soup.find(string=re.compile(r"version\s*[0-9]", re.IGNORECASE))
        if version_div:
            version_match = re.search(r"version\s*([0-9\.]+)", version_div, re.IGNORECASE)
            if version_match:
                return version_match.group(1)
        
        # Try document subtitle for version
        subtitle = soup.find("h2")
        if subtitle and subtitle.string:
            version_match = re.search(r"v[0-9\.]+", subtitle.string, re.IGNORECASE)
            if version_match:
                return version_match.group(0)[1:]  # Remove the 'v' prefix
        
        return "" 