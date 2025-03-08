"""
Test script for the combined retriever.

This script demonstrates how to use the combined retriever with both
the original and expanded datasets.
"""

import logging
import os
import uuid
from dotenv import load_dotenv

from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

from src.flare_ai_rag.ai import GeminiEmbedding, GeminiProvider, EmbeddingTaskType
from src.flare_ai_rag.data_expansion import (
    CombinedRetriever,
    DataExpansionConfig,
    DataExpansionService,
    ProcessorConfig,
    ScraperConfig,
    StorageConfig,
)
from src.flare_ai_rag.retriever import QdrantRetriever, RetrieverConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def test_combined_retriever():
    """Test the combined retriever."""
    logger.info("Starting combined retriever test...")
    
    # Get Gemini API key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY environment variable not set")
        return
    
    # Set up embedding client
    embedding_client = GeminiEmbedding(api_key=gemini_api_key)
    
    # Set up Qdrant client (local in-memory for testing both collections)
    qdrant_client = QdrantClient(":memory:")
    
    # Set up the original retriever
    retriever_config = RetrieverConfig(
        embedding_model="models/text-embedding-004",
        collection_name="flare_docs_original",
        vector_size=768,
        host="localhost",
        port=6333,
    )
    
    original_retriever = QdrantRetriever(
        client=qdrant_client,
        retriever_config=retriever_config,
        embedding_client=embedding_client,
    )
    
    # Create a mock document in the original collection
    original_doc = {
        "text": "Flare is a blockchain platform that provides data to smart contracts.",
        "metadata": {
            "filename": "original_doc.md",
            "title": "Original Flare Documentation",
        }
    }
    
    # Insert the original document (normally this would come from a CSV or other source)
    # Here we're just adding one directly for demonstration
    try:
        # Create the collection
        qdrant_client.create_collection(
            collection_name=retriever_config.collection_name,
            vectors_config={
                "size": retriever_config.vector_size,
                "distance": "Cosine",
            },
        )
        
        # Generate embedding
        vector = embedding_client.embed_content(
            embedding_model="models/text-embedding-004",
            contents=original_doc["text"],
            task_type=EmbeddingTaskType.RETRIEVAL_DOCUMENT,
        )
        
        # Create a UUID for the point ID
        point_id = str(uuid.uuid4())
        
        # Insert the document using PointStruct
        qdrant_client.upsert(
            collection_name=retriever_config.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=original_doc
                )
            ],
        )
        
        logger.info("Inserted test document into original collection")
    except Exception as e:
        logger.error(f"Error setting up original collection: {e}")
        return
    
    # Set up data expansion service
    expansion_config = DataExpansionConfig(
        sources=[
            {
                "name": "Flare Developer Hub",
                "url": "https://dev.flare.network/intro/",  # Just the intro page for testing
                "type": "documentation",
                "priority": 1,
                "enabled": True,
            }
        ],
        scraper=ScraperConfig(
            follow_links=False,  # Disable link following for test
            max_depth=1,
        ),
        processor=ProcessorConfig(
            chunk_size=500,  # Smaller chunks for faster processing
            max_documents_per_run=1,  # Only process one document
        ),
        storage=StorageConfig(
            collection_name="flare_docs_expanded",
            vector_size=768,
            create_if_missing=True,
        ),
        enabled=True,
        data_dir="storage/test_expanded_data",
    )
    
    expansion_service = DataExpansionService(
        config=expansion_config,
        qdrant_client=qdrant_client,
        embedding_client=embedding_client,
    )
    
    # Initialize the combined retriever
    combined_retriever = CombinedRetriever(
        original_retriever=original_retriever,
        expansion_service=expansion_service,
        max_results=5,
        ratio=0.6,  # Slightly favor expanded results
    )
    
    try:
        # First, run the data expansion to populate the expanded collection
        logger.info("Running data expansion...")
        expansion_service.expand_dataset()
        
        # Test the combined retriever
        logger.info("Testing combined retriever...")
        query = "What is Flare Network?"
        
        # Get results from original retriever only
        logger.info("Testing original retriever...")
        original_results = original_retriever.semantic_search(query, top_k=2)
        logger.info(f"Original retriever found {len(original_results)} results")
        
        # Get results from combined retriever
        logger.info("Testing combined retriever...")
        combined_results = combined_retriever.semantic_search(query, top_k=3)
        logger.info(f"Combined retriever found {len(combined_results)} results")
        
        # Log combined results
        logger.info("Combined results:")
        for i, result in enumerate(combined_results, start=1):
            logger.info(f"Result {i}:")
            logger.info(f"Source: {result.get('source', 'unknown')}")
            logger.info(f"Score: {result.get('score', 0.0):.4f}")
            if "metadata" in result:
                metadata = result["metadata"]
                logger.info(f"Title: {metadata.get('title', 'No title')}")
                if "source_name" in metadata:
                    logger.info(f"Source name: {metadata['source_name']}")
                if "url" in metadata:
                    logger.info(f"URL: {metadata['url']}")
            logger.info(f"Text: {result.get('text', '')[:100]}...")
            logger.info("---")
        
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
    
    finally:
        # Clean up
        logger.info("Cleaning up...")
        try:
            # Delete collections
            qdrant_client.delete_collection(retriever_config.collection_name)
            qdrant_client.delete_collection(expansion_config.storage.collection_name)
            logger.info("Collections deleted")
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")


if __name__ == "__main__":
    test_combined_retriever() 