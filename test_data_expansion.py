"""
Test script for the data expansion feature.

This script demonstrates how to use the data expansion feature.
"""

import logging
import os
from dotenv import load_dotenv

from qdrant_client import QdrantClient

from src.flare_ai_rag.ai import GeminiEmbedding
from src.flare_ai_rag.data_expansion.config import (
    DataExpansionConfig, 
    ScraperConfig,
    ProcessorConfig,
    StorageConfig
)
from src.flare_ai_rag.data_expansion.service import DataExpansionService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def test_data_expansion():
    """Test the data expansion feature."""
    logger.info("Starting data expansion test...")
    
    # Get Gemini API key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY environment variable not set")
        return
    
    # Configure for testing - use a smaller scope
    test_sources = [
        {
            "name": "Flare Developer Hub",
            "url": "https://dev.flare.network/intro/",  # Just the intro page for testing
            "type": "documentation",
            "priority": 1,
            "enabled": True,
        }
    ]
    
    # Create configuration with limited scope
    scraper_config = ScraperConfig(
        user_agent="Flare AI RAG Data Collector (Testing)",
        request_delay=1.0,
        timeout=30,
        max_retries=2,
        respect_robots_txt=True,
        follow_links=False,  # Disable link following for test
        max_depth=1,
    )
    
    processor_config = ProcessorConfig(
        chunk_size=500,  # Smaller chunks for faster processing
        chunk_overlap=100,
        min_chunk_size=50,
        preserve_sections=True,
        max_documents_per_run=2,  # Only process a few documents
    )
    
    storage_config = StorageConfig(
        collection_name="flare_docs_test",
        vector_size=768,
        create_if_missing=True,
    )
    
    config = DataExpansionConfig(
        sources=test_sources,
        scraper=scraper_config,
        processor=processor_config,
        storage=storage_config,
        enabled=True,
        data_dir="storage/test_expanded_data",
    )
    
    # Set up Qdrant client (local)
    qdrant_client = QdrantClient(":memory:")  # Use in-memory storage for testing
    
    # Set up embedding client
    embedding_client = GeminiEmbedding(api_key=gemini_api_key)
    
    # Create the data expansion service
    service = DataExpansionService(
        config=config,
        qdrant_client=qdrant_client,
        embedding_client=embedding_client,
    )
    
    try:
        # Run the data expansion
        logger.info("Running data expansion...")
        results = service.expand_dataset()
        
        # Log the results
        logger.info(f"Data expansion results: {results}")
        
        # Test querying the expanded dataset
        logger.info("Testing search...")
        query = "What is Flare Network?"
        search_results = service.search_expanded_dataset(query, top_k=2)
        
        # Log search results
        logger.info(f"Search results for '{query}':")
        for i, result in enumerate(search_results, start=1):
            logger.info(f"Result {i}:")
            logger.info(f"Score: {result['score']:.4f}")
            logger.info(f"Source: {result['metadata']['source_name']}")
            logger.info(f"Title: {result['metadata']['title']}")
            logger.info(f"URL: {result['metadata']['url']}")
            logger.info(f"Text snippet: {result['text'][:100]}...")
            logger.info("---")
            
        # Get collection info
        collection_info = service.get_collection_info()
        logger.info(f"Collection info: {collection_info}")
        
    except Exception as e:
        logger.error(f"Error during data expansion test: {e}", exc_info=True)
    
    finally:
        # Clean up
        logger.info("Cleaning up...")
        try:
            service.clear_collection()
            logger.info("Collection cleared")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")


if __name__ == "__main__":
    test_data_expansion() 