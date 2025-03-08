"""
Real-world scenario test for the Flare AI RAG system with data expansion.

This script demonstrates how to use the data expansion feature in a real-world scenario,
including setting up the environment, configuring the data expansion service, and using
the combined retriever to answer user queries.
"""

import logging
import os
import time
import uuid
from datetime import datetime
from dotenv import load_dotenv

from qdrant_client import QdrantClient

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


def setup_environment():
    """Set up the environment for testing."""
    logger.info("Setting up environment...")
    
    # Get Gemini API key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY environment variable not set")
        return None, None, None
    
    # Set up embedding client
    embedding_client = GeminiEmbedding(api_key=gemini_api_key)
    
    # Set up Gemini provider for chat
    gemini_provider = GeminiProvider(
        api_key=gemini_api_key,
        model="models/gemini-1.5-pro"  # Specify the model
    )
    
    # Set up Qdrant client (local in-memory for testing)
    qdrant_client = QdrantClient(":memory:")
    
    logger.info("Environment setup complete")
    return embedding_client, gemini_provider, qdrant_client


def setup_original_retriever(qdrant_client, embedding_client):
    """Set up the original retriever with sample data."""
    logger.info("Setting up original retriever...")
    
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
    
    # Create the collection
    qdrant_client.create_collection(
        collection_name=retriever_config.collection_name,
        vectors_config={
            "size": retriever_config.vector_size,
            "distance": "Cosine",
        },
    )
    
    # Sample documents for the original collection
    sample_docs = [
        {
            "text": "Flare is a blockchain platform that provides data to smart contracts.",
            "metadata": {
                "filename": "flare_intro.md",
                "title": "Introduction to Flare",
            }
        },
        {
            "text": "The Flare Time Series Oracle (FTSO) provides decentralized price data to the Flare network.",
            "metadata": {
                "filename": "ftso.md",
                "title": "Flare Time Series Oracle",
            }
        },
        {
            "text": "The State Connector allows Flare to securely use data from other blockchains.",
            "metadata": {
                "filename": "state_connector.md",
                "title": "State Connector",
            }
        }
    ]
    
    # Insert sample documents
    for i, doc in enumerate(sample_docs):
        # Generate embedding
        vector = embedding_client.embed_content(
            embedding_model="models/text-embedding-004",
            contents=doc["text"],
            task_type=EmbeddingTaskType.RETRIEVAL_DOCUMENT,
        )
        
        # Insert the document
        from qdrant_client.http.models import PointStruct
        qdrant_client.upsert(
            collection_name=retriever_config.collection_name,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),  # Generate a proper UUID
                    vector=vector,
                    payload=doc
                )
            ],
        )
    
    logger.info(f"Inserted {len(sample_docs)} documents into original collection")
    return original_retriever, retriever_config


def setup_data_expansion(qdrant_client, embedding_client):
    """Set up the data expansion service."""
    logger.info("Setting up data expansion service...")
    
    # Configure data expansion
    expansion_config = DataExpansionConfig(
        sources=[
            {
                "name": "Flare Developer Hub",
                "url": "https://dev.flare.network/intro/",
                "type": "documentation",
                "priority": 1,
                "enabled": True,
            },
            {
                "name": "Flare Blog",
                "url": "https://flare.network/blog/",
                "type": "blog",
                "priority": 2,
                "enabled": False,  # Disabled for testing
            }
        ],
        scraper=ScraperConfig(
            follow_links=False,  # Disable link following for test
            max_depth=1,
            request_delay=1.0,
        ),
        processor=ProcessorConfig(
            chunk_size=500,  # Smaller chunks for faster processing
            chunk_overlap=100,
            max_documents_per_run=3,
        ),
        storage=StorageConfig(
            collection_name="flare_docs_expanded",
            vector_size=768,
            create_if_missing=True,
        ),
        enabled=True,
        data_dir="storage/test_expanded_data",
    )
    
    # Create data expansion service
    expansion_service = DataExpansionService(
        config=expansion_config,
        qdrant_client=qdrant_client,
        embedding_client=embedding_client,
    )
    
    logger.info("Data expansion service setup complete")
    return expansion_service, expansion_config


def run_data_expansion(expansion_service):
    """Run the data expansion process."""
    logger.info("Running data expansion...")
    start_time = time.time()
    
    # Run data expansion
    results = expansion_service.expand_dataset()
    
    end_time = time.time()
    duration = end_time - start_time
    
    logger.info(f"Data expansion completed in {duration:.2f} seconds")
    logger.info(f"Processed {results['sources_processed']} sources")
    logger.info(f"Collected {results['documents_collected']} documents")
    logger.info(f"Stored {results['chunks_stored']} chunks")
    
    if results['errors']:
        logger.warning(f"Encountered {len(results['errors'])} errors during expansion")
        for error in results['errors']:
            logger.warning(f"Error: {error}")
    
    return results


def setup_combined_retriever(original_retriever, expansion_service):
    """Set up the combined retriever."""
    logger.info("Setting up combined retriever...")
    
    # Create combined retriever
    combined_retriever = CombinedRetriever(
        original_retriever=original_retriever,
        expansion_service=expansion_service,
        max_results=5,
        ratio=0.6,  # Slightly favor expanded results
    )
    
    logger.info("Combined retriever setup complete")
    return combined_retriever


def test_queries(original_retriever, combined_retriever):
    """Test various queries against both retrievers."""
    logger.info("Testing queries...")
    
    test_queries = [
        "What is Flare Network?",
        "How does the State Connector work?",
        "What is FTSO?",
        "How can developers use Flare?",
        "What blockchain data can Flare access?",
    ]
    
    for query in test_queries:
        logger.info(f"\n--- Query: '{query}' ---")
        
        # Test original retriever
        logger.info("Results from original retriever:")
        original_results = original_retriever.semantic_search(query, top_k=2)
        for i, result in enumerate(original_results, start=1):
            logger.info(f"  Result {i}:")
            logger.info(f"  Score: {result.get('score', 0.0):.4f}")
            if "metadata" in result:
                metadata = result["metadata"]
                logger.info(f"  Title: {metadata.get('title', 'No title')}")
            logger.info(f"  Text: {result.get('text', '')[:100]}...")
        
        # Test combined retriever
        logger.info("\nResults from combined retriever:")
        combined_results = combined_retriever.semantic_search(query, top_k=3)
        for i, result in enumerate(combined_results, start=1):
            logger.info(f"  Result {i}:")
            logger.info(f"  Source: {result.get('source', 'unknown')}")
            logger.info(f"  Score: {result.get('score', 0.0):.4f}")
            if "metadata" in result:
                metadata = result["metadata"]
                logger.info(f"  Title: {metadata.get('title', 'No title')}")
                if "source_name" in metadata:
                    logger.info(f"  Source name: {metadata['source_name']}")
                if "url" in metadata:
                    logger.info(f"  URL: {metadata['url']}")
            logger.info(f"  Text: {result.get('text', '')[:100]}...")
        
        logger.info("\n")


def generate_ai_response(gemini_provider, query, context):
    """Generate an AI response using the retrieved context."""
    logger.info(f"Generating AI response for query: '{query}'")
    
    # Create a system prompt
    system_prompt = """
    You are an AI assistant for Flare Network. 
    Answer questions based on the provided context.
    If you don't know the answer, say so - don't make up information.
    Keep your answers concise and informative.
    """
    
    # Format the context
    formatted_context = "\n\n".join([
        f"Source: {item.get('source', 'unknown')}\n"
        f"Title: {item.get('metadata', {}).get('title', 'No title')}\n"
        f"Text: {item.get('text', '')}"
        for item in context
    ])
    
    # Generate response using the correct method
    prompt = f"{system_prompt}\n\nContext:\n{formatted_context}\n\nQuestion: {query}"
    response = gemini_provider.generate(
        prompt=prompt,
        response_mime_type=None,
        response_schema=None,
    )
    
    return response.text


def main():
    """Main function to run the real-world scenario test."""
    logger.info("Starting real-world scenario test...")
    
    # Setup environment
    embedding_client, gemini_provider, qdrant_client = setup_environment()
    if not embedding_client or not gemini_provider or not qdrant_client:
        logger.error("Failed to set up environment")
        return
    
    # Initialize variables for cleanup
    retriever_config = None
    expansion_config = None
    
    try:
        # Setup original retriever
        original_retriever, retriever_config = setup_original_retriever(qdrant_client, embedding_client)
        
        # Setup data expansion
        expansion_service, expansion_config = setup_data_expansion(qdrant_client, embedding_client)
        
        # Run data expansion
        expansion_results = run_data_expansion(expansion_service)
        
        # Setup combined retriever
        combined_retriever = setup_combined_retriever(original_retriever, expansion_service)
        
        # Test queries
        test_queries(original_retriever, combined_retriever)
        
        # Demonstrate end-to-end RAG with a specific query
        demo_query = "What are the main features of Flare Network?"
        logger.info(f"\n=== End-to-End RAG Demo for Query: '{demo_query}' ===")
        
        # Get context from combined retriever
        context = combined_retriever.semantic_search(demo_query, top_k=3)
        
        # Generate AI response
        if gemini_provider:
            ai_response = generate_ai_response(gemini_provider, demo_query, context)
            logger.info("\nAI Response:")
            logger.info(ai_response)
        
        # Get collection info
        original_collection_info = qdrant_client.get_collection(retriever_config.collection_name)
        expanded_collection_info = qdrant_client.get_collection(expansion_config.storage.collection_name)
        
        logger.info("\nCollection Statistics:")
        logger.info(f"Original collection: {original_collection_info.points_count} points")
        logger.info(f"Expanded collection: {expanded_collection_info.points_count} points")
        
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
    
    finally:
        # Clean up
        logger.info("\nCleaning up...")
        try:
            # Delete collections if they were created
            if retriever_config:
                try:
                    qdrant_client.delete_collection(retriever_config.collection_name)
                    logger.info(f"Deleted collection {retriever_config.collection_name}")
                except Exception as e:
                    logger.error(f"Error deleting collection {retriever_config.collection_name}: {e}")
                    
            if expansion_config:
                try:
                    qdrant_client.delete_collection(expansion_config.storage.collection_name)
                    logger.info(f"Deleted collection {expansion_config.storage.collection_name}")
                except Exception as e:
                    logger.error(f"Error deleting collection {expansion_config.storage.collection_name}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
    
    logger.info("Real-world scenario test completed")


if __name__ == "__main__":
    main() 