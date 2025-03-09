#!/usr/bin/env python3
"""
Flare Developer Hub Scraper and RAG Integration

This script scrapes data from the Flare Developer Hub, processes it,
and integrates it with the Flare AI RAG system using Qdrant for vector storage.

Usage:
    python flare_scraper.py

Dependencies:
    - requests
    - beautifulsoup4
    - qdrant_client
    - python-dotenv
"""

import os
import json
import time
import logging
import requests
import hashlib
from pathlib import Path
from typing import Any, cast
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

# Try to import from the flare_ai_rag package
try:
    from src.flare_ai_rag.ai import GeminiEmbedding, EmbeddingTaskType
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
except ImportError:
    print("Error: Required modules not found. Make sure you're in the correct environment.")
    print("Install dependencies with: pip install -e .")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scraper.log")
    ]
)

# URLs to scrape from Flare Developer Hub
FLARE_URLS = [
    "https://dev.flare.network/intro/",  # Introduction to Flare
    "https://dev.flare.network/ftso/overview/",  # FTSO Overview
    "https://dev.flare.network/hackathon/onboarding/",  # Hackathon Onboarding
    "https://dev.flare.network/hackathon/cookbook/"  # Hackathon Cookbook
]

# Base URL for the Flare Developer Hub
FLARE_DEV_HUB_URL = "https://dev.flare.network/"

# Headers to mimic a browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Storage directory for scraped data
STORAGE_DIR = "storage/enhanced_data"

# Qdrant collection name
COLLECTION_NAME = "flare_docs_extended"

# Document class for storing scraped data
class Document:
    def __init__(self, id: str, content: str, metadata: dict[str, Any]):
        self.id = id
        self.content = content
        self.metadata = metadata
    
    def model_dump(self) -> dict[str, Any]:
        """Convert document to dictionary (compatible with Pydantic v2)"""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata
        }

class FlareHubScraper:
    """Scraper for the Flare Developer Hub"""
    
    def __init__(self):
        """Initialize the scraper"""
        self.visited_urls = set()
        self.all_links = set()
        self.metadata = {}
        self.documents = []
        
        # Create storage directory
        os.makedirs(STORAGE_DIR, exist_ok=True)
        
        # Load metadata if exists
        metadata_path = os.path.join(STORAGE_DIR, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                self.metadata = json.load(f)
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and trailing slashes"""
        parsed = urlparse(url)
        path = parsed.path
        if not path.endswith("/"):
            path += "/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    
    def _get_page(self, url: str) -> tuple[str | None, dict[str, Any] | None]:
        """
        Get page content and metadata
        
        Args:
            url: URL to get
            
        Returns:
            Tuple of (HTML content, metadata)
        """
        try:
            logging.info(f"Fetching {url}")
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            
            # Extract metadata
            metadata = {
                "url": url,
                "title": "",
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "content_type": response.headers.get("Content-Type", ""),
                "status_code": response.status_code
            }
            
            return response.text, metadata
        except Exception as e:
            logging.error(f"Error fetching {url}: {e}")
            return None, None
    
    def _extract_content(self, html: str, url: str) -> str | None:
        """
        Extract content from HTML
        
        Args:
            html: HTML content
            url: Source URL
            
        Returns:
            Extracted text content
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove navigation, footer, and other non-content elements
            for element in soup.select("nav, footer, .sidebar, .navbar, script, style"):
                element.decompose()
            
            # Extract title
            title_element = soup.find("title")
            title = title_element.get_text() if title_element else "Untitled"
            
            # Extract main content
            main_content = soup.select_one("main, article, .content, .main-content, #content")
            
            if not main_content:
                # Fallback to body if no main content found
                main_content = soup.select_one("body")
            
            if main_content:
                # Extract text with proper spacing
                paragraphs = []
                for p in main_content.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
                    text = p.get_text(strip=True)
                    if text:
                        paragraphs.append(text)
                
                content = "\n\n".join(paragraphs)
                
                # Add title at the beginning
                content = f"{title}\n\n{content}"
                
                return content
            
            return None
        except Exception as e:
            logging.error(f"Error extracting content from {url}: {e}")
            return None
    
    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """
        Extract links from HTML
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of extracted links
        """
        links = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Find all links
            for a in soup.find_all("a", href=True):
                href = a["href"]
                
                # Skip empty links, anchors, and non-HTTP links
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                
                # Resolve relative URLs
                full_url = urljoin(base_url, href)
                
                # Skip external links
                if not full_url.startswith(FLARE_DEV_HUB_URL):
                    continue
                
                # Normalize URL
                normalized_url = self._normalize_url(full_url)
                
                # Add to links
                links.append(normalized_url)
                self.all_links.add(normalized_url)
        except Exception as e:
            logging.error(f"Error extracting links from {base_url}: {e}")
        
        return links
    
    def _create_document(self, url: str, content: str, metadata: dict[str, Any]) -> Document:
        """
        Create document from content
        
        Args:
            url: Source URL
            content: Text content
            metadata: Metadata dictionary
            
        Returns:
            Document object
        """
        # Generate document ID from URL
        doc_id = hashlib.md5(url.encode()).hexdigest()
        
        # Create metadata
        doc_metadata = {
            "url": url,
            "title": metadata.get("title", "Untitled"),
            "last_updated": metadata.get("last_updated", ""),
            "source": "flare_developer_hub",
            "content_type": metadata.get("content_type", ""),
            "status_code": metadata.get("status_code", 0)
        }
        
        # Create document
        document = Document(
            id=doc_id,
            content=content,
            metadata=doc_metadata
        )
        
        return document
    
    def _save_document(self, document: Document) -> str:
        """
        Save document to file
        
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
            json.dump(document.model_dump(), f, indent=2)
        
        # Update metadata
        self.metadata[document.id] = {
            "url": document.metadata["url"],
            "title": document.metadata["title"],
            "last_updated": document.metadata["last_updated"],
        }
        
        # Save metadata
        metadata_path = os.path.join(STORAGE_DIR, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)
        
        return file_path
    
    def crawl(self, start_urls: list[str] | None = None, max_pages: int = 50) -> list[Document]:
        """
        Crawl the Flare Developer Hub
        
        Args:
            start_urls: List of URLs to start crawling from
            max_pages: Maximum number of pages to crawl
            
        Returns:
            List of documents
        """
        if start_urls is None:
            start_urls = FLARE_URLS
        
        logging.info(f"Starting crawl of Flare Developer Hub (max {max_pages} pages)")
        
        # Initialize queue with start URLs
        queue = list(start_urls)
        
        # Crawl until queue is empty or max_pages is reached
        while queue and len(self.visited_urls) < max_pages:
            # Get next URL
            url = queue.pop(0)
            
            # Skip if already visited
            if url in self.visited_urls:
                continue
            
            # Mark as visited
            self.visited_urls.add(url)
            
            # Get page
            html, metadata = self._get_page(url)
            if not html:
                continue
            
            # Extract content
            content = self._extract_content(html, url)
            if not content:
                logging.warning(f"No content extracted from {url}")
                continue
            
            # Create document
            document = self._create_document(url, content, metadata)
            
            # Save document
            file_path = self._save_document(document)
            logging.info(f"Saved document to {file_path}")
            
            # Add to documents
            self.documents.append(document)
            
            # Extract links
            links = self._extract_links(html, url)
            
            # Add new links to queue
            for link in links:
                if link not in self.visited_urls and link not in queue:
                    queue.append(link)
            
            # Sleep to avoid overloading the server
            time.sleep(1)
        
        logging.info(f"Crawl complete! Visited {len(self.visited_urls)} pages, extracted {len(self.documents)} documents")
        
        return self.documents

def setup_qdrant_collection():
    """Set up Qdrant collection for storing embeddings"""
    try:
        # Connect to Qdrant
        client = QdrantClient(host="localhost", port=6333)
        
        # Check if collection exists
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if COLLECTION_NAME in collection_names:
            logging.info(f"Collection {COLLECTION_NAME} already exists")
            # Optionally recreate the collection
            client.delete_collection(COLLECTION_NAME)
            logging.info(f"Deleted existing collection {COLLECTION_NAME}")
        
        # Create collection
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=768,  # Gemini embedding size
                distance=models.Distance.COSINE
            )
        )
        logging.info(f"Created collection {COLLECTION_NAME}")
        
        return client
    except Exception as e:
        logging.error(f"Error setting up Qdrant collection: {e}")
        return None

def index_documents(client: QdrantClient, documents: list[Document]) -> bool:
    """Index documents in Qdrant"""
    try:
        # Load API key from .env
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logging.error("GEMINI_API_KEY not found in .env file")
            return False
        
        # Initialize embedding client
        embedding_client = GeminiEmbedding(api_key=api_key)
        
        # Process documents in batches
        batch_size = 10
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            
            # Extract content and IDs
            contents = [doc.content for doc in batch]
            ids = [doc.id for doc in batch]
            metadatas = [doc.metadata for doc in batch]
            
            # Generate embeddings
            logging.info(f"Generating embeddings for batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
            embeddings = []
            for content in contents:
                # Truncate content if too long (Gemini has a limit of 8000 bytes)
                # Use a smaller limit to be safe
                if len(content.encode('utf-8')) > 7500:
                    content = content[:7000]  # Truncate to be well under the limit
                
                try:
                    # Generate embedding
                    embedding = embedding_client.embed_content(
                        embedding_model="models/embedding-001",
                        contents=content,
                        task_type=EmbeddingTaskType.RETRIEVAL_DOCUMENT
                    )
                    embeddings.append(embedding)
                except Exception as e:
                    logging.error(f"Error generating embedding: {e}")
                    # Skip this document
                    continue
            
            # Index in Qdrant
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=models.Batch(
                    ids=ids,
                    vectors=embeddings,
                    payloads=[{
                        "content": doc.content,
                        "url": doc.metadata["url"],
                        "title": doc.metadata["title"],
                        "source": doc.metadata["source"]
                    } for doc in batch]
                )
            )
            
            logging.info(f"Indexed batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
            
            # Sleep to avoid rate limits
            time.sleep(2)
        
        logging.info(f"Indexed {len(documents)} documents in Qdrant")
        return True
    except Exception as e:
        logging.error(f"Error indexing documents: {e}")
        return False

def load_documents_from_storage():
    """Load documents from storage"""
    documents = []
    source_dir = os.path.join(STORAGE_DIR, "flare_developer_hub")
    
    if not os.path.exists(source_dir):
        logging.warning(f"Storage directory {source_dir} does not exist")
        return documents
    
    # Load all JSON files
    for file_path in Path(source_dir).glob("*.json"):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                document = Document(
                    id=data["id"],
                    content=data["content"],
                    metadata=data["metadata"]
                )
                documents.append(document)
        except Exception as e:
            logging.error(f"Error loading document {file_path}: {e}")
    
    logging.info(f"Loaded {len(documents)} documents from storage")
    return documents

def test_search(client: QdrantClient) -> None:
    """Test search functionality"""
    try:
        # Load API key from .env
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logging.error("GEMINI_API_KEY not found in .env file")
            return
        
        # Initialize embedding client
        embedding_client = GeminiEmbedding(api_key=api_key)
        
        # Test queries
        test_queries = [
            "What is Flare?",
            "How does FTSO work?",
            "What is the Flare Time Series Oracle?",
            "How can I participate in the Flare hackathon?"
        ]
        
        for query in test_queries:
            try:
                # Generate query embedding
                query_embedding = embedding_client.embed_content(
                    embedding_model="models/embedding-001",
                    contents=query,
                    task_type=EmbeddingTaskType.RETRIEVAL_QUERY
                )
                
                # Search in Qdrant
                results = client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=query_embedding,
                    limit=3
                )
                
                logging.info(f"Query: {query}")
                logging.info(f"Found {len(results)} results")
                
                # Print results
                for i, result in enumerate(results):
                    logging.info(f"Result {i+1}: {result.payload.get('title', 'Untitled')} (Score: {result.score:.4f})")
                    logging.info(f"URL: {result.payload.get('url', 'No URL')}")
                    content = result.payload.get("content", "No content")
                    logging.info(f"Content preview: {content[:100]}...")
                    logging.info("---")
            except Exception as e:
                logging.error(f"Error testing query '{query}': {e}")
    except Exception as e:
        logging.error(f"Error testing search: {e}")

def main():
    """Main function"""
    logging.info("Starting Flare Developer Hub scraper and RAG integration")
    
    # Check if data already exists
    documents = load_documents_from_storage()
    
    # Scrape if no documents found
    if not documents:
        logging.info("No documents found in storage, starting scraper")
        scraper = FlareHubScraper()
        documents = scraper.crawl(max_pages=50)
    
    # Set up Qdrant collection
    client = setup_qdrant_collection()
    if not client:
        logging.error("Failed to set up Qdrant collection")
        return
    
    # Index documents
    success = index_documents(client, documents)
    if not success:
        logging.error("Failed to index documents")
        return
    
    # Test search
    test_search(client)
    
    logging.info("Flare Developer Hub scraper and RAG integration complete!")
    logging.info(f"Indexed {len(documents)} documents in Qdrant collection '{COLLECTION_NAME}'")
    logging.info("You can now use the Flare AI RAG system to query the data")
    logging.info("Run './run_enhanced_app.sh' to start the application")

if __name__ == "__main__":
    main() 