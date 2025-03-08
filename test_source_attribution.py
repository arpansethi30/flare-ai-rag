import os
import json
from dotenv import load_dotenv
from qdrant_client import QdrantClient

from flare_ai_rag.ai import GeminiProvider, GeminiEmbedding, EmbeddingTaskType, Model
from flare_ai_rag.responder import GeminiResponder, ResponderConfig
from flare_ai_rag.responder.prompts import RESPONDER_INSTRUCTION, RESPONDER_PROMPT
from flare_ai_rag.retriever import RetrieverConfig

# Load environment variables
load_dotenv()

def test_source_attribution():
    """Test source attribution in responses."""
    print("Starting source attribution test...")
    
    # Set up Gemini client
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    # Create model configurations
    model_id = "models/gemini-pro"
    
    gemini_provider = GeminiProvider(api_key=gemini_api_key, model=model_id)
    
    # Create test config for display purposes (not used in test)
    embedding_model = "models/text-embedding-004"
    retriever_config = RetrieverConfig(
        embedding_model=embedding_model,
        collection_name="flare_docs",
        vector_size=768,  # Typical size for text-embedding-004
        host="localhost",
        port=6333
    )
    
    model = Model(
        model_id=model_id,
        max_tokens=1024,
        temperature=0.2
    )
    
    responder_config = ResponderConfig(
        model=model,
        system_prompt=RESPONDER_INSTRUCTION,
        query_prompt=RESPONDER_PROMPT
    )
    
    responder = GeminiResponder(
        client=gemini_provider,
        responder_config=responder_config
    )
    
    # Create mock retrieved documents with metadata
    retrieved_docs = [
        {
            "text": "Flare Network is a blockchain designed to provide data to smart contracts safely and securely.",
            "metadata": {
                "filename": "introduction.md",
                "title": "Introduction to Flare",
                "author": "Flare Team",
                "date": "2023-01-15",
                "url": "https://dev.flare.network/intro/"
            },
            "score": 0.92
        },
        {
            "text": "The Flare Time Series Oracle (FTSO) provides decentralized price feeds for various cryptocurrencies.",
            "metadata": {
                "filename": "ftso.md",
                "title": "Flare Time Series Oracle",
                "author": "Flare Labs",
                "date": "2023-02-20",
                "url": "https://dev.flare.network/ftso/"
            },
            "score": 0.85
        }
    ]
    
    # Test query
    query = "What is Flare Network and what is FTSO?"
    
    # Generate response with source attribution
    response = responder.generate_response(query, retrieved_docs)
    
    print("\nQuery:", query)
    print("\nResponse with source attribution:")
    print(response)
    
    return response

if __name__ == "__main__":
    test_source_attribution() 