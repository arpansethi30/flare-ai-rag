"""
RAG Knowledge API Main Application Module

This module initializes and configures the FastAPI application for the RAG backend.
It sets up CORS middleware, loads configuration and data, and wires together the
components for the RAG system.
"""

import structlog
import uvicorn
from fastapi import FastAPI

logger = structlog.get_logger(__name__)

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    This function:
      1. Creates a new FastAPI instance with CORS middleware
      2. Loads configuration
      3. Loads data and initializes components
      4. Sets up API routes

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    # Import here to avoid circular imports
    from flare_ai_rag.streamlined_api import create_app as create_api_app
    
    return create_api_app()


app = create_app()


def start() -> None:
    """
    Start the FastAPI application server.
    """
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    start()
