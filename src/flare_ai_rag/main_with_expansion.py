"""
RAG Knowledge API Main Application Module with Data Expansion

This module initializes and configures the FastAPI application for the RAG backend.
It sets up CORS middleware, loads configuration and data, and wires together the
Gemini-based Router, Retriever, and Responder components into a chat endpoint.
It also includes the data expansion feature to enhance the knowledge base.
"""

import os
from typing import Any

import pandas as pd
import structlog
import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient

from flare_ai_rag.ai import GeminiEmbedding, GeminiProvider
from flare_ai_rag.api import ChatRouter
from flare_ai_rag.attestation import Vtpm
from flare_ai_rag.prompts import PromptService
from flare_ai_rag.responder import GeminiResponder, ResponderConfig
from flare_ai_rag.retriever import QdrantRetriever, RetrieverConfig, generate_collection
from flare_ai_rag.router import GeminiRouter, RouterConfig
from flare_ai_rag.settings import settings
from flare_ai_rag.utils import load_json

# Import data expansion components
from flare_ai_rag.data_expansion import (
    CombinedRetriever,
    DataExpansionConfig,
    DataExpansionService,
    ProcessorConfig,
    ScraperConfig,
    StorageConfig,
)

logger = structlog.get_logger(__name__)


def setup_router(input_config: dict) -> tuple[GeminiProvider, GeminiRouter]:
    """Initialize a Gemini Provider for routing."""
    # Setup router config
    router_model_config = input_config["router_model"]
    router_config = RouterConfig.load(router_model_config)

    # Setup Gemini client based on Router config
    # Older version used a system_instruction
    gemini_provider = GeminiProvider(
        api_key=settings.gemini_api_key, model=router_config.model.model_id
    )
    gemini_router = GeminiRouter(client=gemini_provider, config=router_config)

    return gemini_provider, gemini_router


def setup_retriever(
    qdrant_client: QdrantClient,
    input_config: dict,
    df_docs: pd.DataFrame,
) -> QdrantRetriever:
    """Initialize the Qdrant retriever."""
    # Set up Qdrant config
    retriever_config = RetrieverConfig.load(input_config["retriever_config"])

    # Set up Gemini Embedding client
    embedding_client = GeminiEmbedding(settings.gemini_api_key)
    # (Re)generate qdrant collection
    generate_collection(
        df_docs,
        qdrant_client,
        retriever_config,
        embedding_client=embedding_client,
    )
    logger.info(
        "The Qdrant collection has been generated.",
        collection_name=retriever_config.collection_name,
    )
    # Return retriever
    return QdrantRetriever(
        client=qdrant_client,
        retriever_config=retriever_config,
        embedding_client=embedding_client,
    )


def setup_qdrant(input_config: dict) -> QdrantClient:
    """Initialize Qdrant client."""
    logger.info("Setting up Qdrant client...")
    retriever_config = RetrieverConfig.load(input_config["retriever_config"])
    qdrant_client = QdrantClient(host=retriever_config.host, port=retriever_config.port)
    logger.info("Qdrant client has been set up.")

    return qdrant_client


def setup_responder(input_config: dict) -> GeminiResponder:
    """Initialize the responder."""
    # Set up Responder Config.
    responder_config = input_config["responder_model"]
    responder_config = ResponderConfig.load(responder_config)

    # Set up a new Gemini Provider based on Responder Config.
    gemini_provider = GeminiProvider(
        api_key=settings.gemini_api_key,
        model=responder_config.model.model_id,
        system_instruction=responder_config.system_prompt,
    )
    return GeminiResponder(client=gemini_provider, responder_config=responder_config)


def setup_data_expansion(
    qdrant_client: QdrantClient, 
    embedding_client: GeminiEmbedding, 
    config_path: str | None = None
) -> tuple[DataExpansionService, DataExpansionConfig]:
    """Initialize the data expansion service."""
    logger.info("Setting up data expansion service...")
    
    # Configure data expansion
    # Create default scraper config
    scraper_config = ScraperConfig(
        follow_links=False,  # Disable link following for test
        max_depth=1,
        request_delay=1.0,
    )
    
    # Create default processor config
    processor_config = ProcessorConfig(
        chunk_size=500,  # Smaller chunks for faster processing
        chunk_overlap=100,
        max_documents_per_run=3,
    )
    
    # Create default storage config
    storage_config = StorageConfig(
        collection_name="flare_docs_expanded",
        vector_size=768,
        create_if_missing=True,
    )
    
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
        scraper=scraper_config,
        processor=processor_config,
        storage=storage_config,
        enabled=True,
        data_dir="storage/expanded_data",
    )
    
    # Create data expansion service
    expansion_service = DataExpansionService(
        config=expansion_config,
        qdrant_client=qdrant_client,
        embedding_client=embedding_client,
    )
    
    logger.info("Data expansion service setup complete")
    return expansion_service, expansion_config


def setup_combined_retriever(
    original_retriever: QdrantRetriever, 
    expansion_service: DataExpansionService
) -> CombinedRetriever:
    """Set up the combined retriever."""
    logger.info("Setting up combined retriever...")
    
    # Create combined retriever
    combined_retriever = CombinedRetriever(
        original_retriever=original_retriever,
        expansion_service=expansion_service,
        max_results=10,
        ratio=0.6,  # Slightly favor expanded results
    )
    
    logger.info("Combined retriever setup complete")
    return combined_retriever


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance with data expansion.

    This function:
      1. Creates a new FastAPI instance with optional CORS middleware.
      2. Loads configuration.
      3. Sets up the Gemini Router, Qdrant Retriever, and Gemini Responder.
      4. Loads RAG data and (re)generates the Qdrant collection.
      5. Sets up the data expansion service and combined retriever.
      6. Initializes a ChatRouter that wraps the RAG pipeline.
      7. Registers the chat endpoint under the /chat prefix.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    app = FastAPI(title="RAG Knowledge API with Data Expansion", version="1.0", redirect_slashes=False)

    # Optional: configure CORS middleware using settings.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load input configuration.
    input_config = load_json(settings.input_path / "input_parameters.json")

    # Load RAG data.
    df_docs = pd.read_csv(settings.data_path / "docs.csv", delimiter=",")
    logger.info("Loaded CSV Data.", num_rows=len(df_docs))

    # Set up the RAG components: 1. Gemini Provider
    base_ai, router_component = setup_router(input_config)

    # 2a. Set up Qdrant client.
    qdrant_client = setup_qdrant(input_config)

    # 2b. Set up the Retriever.
    retriever_component = setup_retriever(qdrant_client, input_config, df_docs)
    
    # 2c. Set up data expansion service
    expansion_service, _ = setup_data_expansion(
        qdrant_client, 
        retriever_component.embedding_client
    )
    
    # 2d. Run data expansion (can be done periodically or on startup)
    try:
        expansion_results = expansion_service.expand_dataset()
        logger.info(f"Data expansion completed: {expansion_results['chunks_stored']} chunks stored")
    except Exception as e:
        logger.error(f"Data expansion failed: {e}")
    
    # 2e. Set up combined retriever
    combined_retriever = setup_combined_retriever(retriever_component, expansion_service)

    # 3. Set up the Responder.
    responder_component = setup_responder(input_config)

    # Create an APIRouter for chat endpoints and initialize ChatRouter.
    chat_router = ChatRouter(
        router=APIRouter(),
        ai=base_ai,
        query_router=router_component,
        retriever=combined_retriever,  # Use combined retriever instead of original
        responder=responder_component,
        attestation=Vtpm(simulate=settings.simulate_attestation),
        prompts=PromptService(),
    )
    app.include_router(chat_router.router, prefix="/api/routes/chat", tags=["chat"])

    return app


app = create_app()


def start():
    """
    Start the FastAPI application server.
    """
    # Get port from environment variable with fallback to 8080
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)  # noqa: S104


if __name__ == "__main__":
    start() 