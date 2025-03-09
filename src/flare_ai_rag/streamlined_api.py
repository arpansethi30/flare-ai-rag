"""
Streamlined API for Flare AI RAG

This module provides a simplified FastAPI setup for the Flare AI RAG system.
It uses the streamlined RAG pipeline to process queries and return responses.
"""

import structlog
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from flare_ai_rag.settings import settings
from flare_ai_rag.streamlined_rag import StreamlinedRAG, create_streamlined_rag

# Configure logging
logger = structlog.get_logger(__name__)

# Global RAG pipeline instance (singleton)
# This is created only once when the module is loaded
RAG_PIPELINE = create_streamlined_rag()

# Define request models
class ChatMessage(BaseModel):
    """Chat message model."""
    message: str = Field(..., min_length=1, description="User query message")

class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str = Field(..., description="Response to the user query")

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.
    
    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    # Create FastAPI app
    app = FastAPI(title="Flare AI RAG API", version="2.0")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Create API router
    api_router = APIRouter()
    
    # Define chat endpoint
    @api_router.post("/")
    async def chat_endpoint(message: ChatMessage):
        """Process a chat message and return a response."""
        try:
            logger.info(f"Received chat message: {message.message}")
            
            # Process the message using the global RAG pipeline
            response = RAG_PIPELINE.get_response(message.message)
            
            logger.info(f"Generated response: {response[:100]}...")
            return ChatResponse(answer=response)
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="An error occurred while processing your request"
            )

    # Define health check endpoint
    @api_router.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}
    
    # Include router with prefix
    app.include_router(api_router, prefix="/api/chat", tags=["chat"])
    
    return app

# Create app instance
app = create_app()

def start() -> None:
    """Start the FastAPI application server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

# For manual testing
if __name__ == "__main__":
    start() 