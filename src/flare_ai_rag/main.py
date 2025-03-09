"""
RAG Knowledge API Main Application Module

This module initializes and configures the FastAPI application for the RAG backend.
It sets up CORS middleware, loads configuration and data, and wires together the
Gemini-based Router, Retriever, and Responder components into a chat endpoint.
"""

import os
import pandas as pd
import structlog
import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient
import json

from flare_ai_rag.ai import GeminiEmbedding, GeminiProvider
from flare_ai_rag.api import ChatRouter
from flare_ai_rag.attestation import Vtpm
from flare_ai_rag.prompts import PromptService, SemanticRouterResponse
from flare_ai_rag.responder import GeminiResponder, ResponderConfig
from flare_ai_rag.retriever import QdrantRetriever, RetrieverConfig, generate_collection
from flare_ai_rag.router import GeminiRouter, RouterConfig
from flare_ai_rag.settings import settings
from flare_ai_rag.utils import load_json

logger = structlog.get_logger(__name__)

# Add these fallback responses as a dictionary
FALLBACK_RESPONSES = {
    "what is flare": "Flare is a blockchain for data, designed to provide decentralized access to high-integrity data from various sources. It's an EVM-compatible smart contract platform optimized for decentralized data acquisition, supporting price and time-series data, blockchain event and state data, and Web2 API data integration. For more information, visit https://dev.flare.network/intro/",
    
    "what is ftso": "FTSO (Flare Time Series Oracle) is Flare's native price oracle system that provides reliable, decentralized price data to the network. Key features include decentralized price feeds from multiple independent data providers, economic incentives for accurate data provision, resistance to manipulation through a robust voting system, and support for crypto assets, forex, commodities, and other assets. For more information, visit https://dev.flare.network/tech/ftso/",
    
    "tell me about flare": "Flare is the blockchain for data, offering secure, decentralized access to high-integrity data from various sources. As an EVM-compatible platform, it enables developers to build scalable applications with access to cross-chain data through the State Connector, price feeds via the Flare Time Series Oracle (FTSO), time-series data for various assets, and integration with Web2 API data. For more information, visit https://dev.flare.network/intro/",
    
    "python": "Flare Network supports Python development primarily through its API integrations and developer tools. While Flare's core smart contracts are written in Solidity (for EVM compatibility), Python is commonly used for building backend services that interact with Flare's blockchain, creating data analysis tools that work with FTSO data, developing scripts for automating interactions with Flare contracts, and implementing off-chain components of dApps that use Flare. For more information, visit https://dev.flare.network/",
    
    "setup flare python": "To set up a Python development environment for Flare Network: 1) Install Python 3.8 or higher and pip, 2) Install the web3.py library: `pip install web3`, 3) Configure your environment to connect to Flare's RPC endpoints (Flare mainnet: https://flare-api.flare.network/ext/bc/C/rpc), 4) Set up a wallet with the private keys for your Flare accounts, 5) Create a new Python script and import the necessary libraries. For more detailed setup instructions and examples, visit the official Flare documentation at https://dev.flare.network/"
}


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
    
    # Check if collection exists
    collections = qdrant_client.get_collections().collections
    collection_names = [collection.name for collection in collections]
    
    # Generate collection if it doesn't exist or if it has 0 points
    if retriever_config.collection_name not in collection_names:
        logger.info(f"Collection {retriever_config.collection_name} does not exist. Creating it.")
        generate_collection(
            df_docs,
            qdrant_client,
            retriever_config,
            embedding_client=embedding_client,
        )
    else:
        # Check if collection has points
        collection_info = qdrant_client.get_collection(retriever_config.collection_name)
        if collection_info.points_count == 0:
            logger.info(f"Collection {retriever_config.collection_name} exists but has 0 points. Populating it.")
            generate_collection(
                df_docs,
                qdrant_client,
                retriever_config,
                embedding_client=embedding_client,
            )
        else:
            logger.info(
                f"Using existing collection: {retriever_config.collection_name} with {collection_info.points_count} points."
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


def setup_direct_endpoints(app: FastAPI, chat_router: ChatRouter) -> None:
    """Set up direct endpoints with hardcoded responses for common queries.
    
    Args:
        app: The FastAPI application
        chat_router: The chat router instance
    """
    @app.post("/api/direct/chat/")
    async def direct_chat(message: dict) -> dict:
        """Direct chat endpoint with hardcoded responses for common queries."""
        try:
            user_message = message.get("message", "").lower().strip()
            
            # Check for fallback responses
            for key, response in FALLBACK_RESPONSES.items():
                if key in user_message:
                    return {"classification": "ANSWER", "response": response}
            
            # Special handling for questions not in fallbacks
            if "python" in user_message and ("flare" in user_message or "blockchain" in user_message or "setup" in user_message or "how to" in user_message):
                # Enhanced Python response with more detailed, code-rich content
                enhanced_python_response = """
# 🐍 Python + Flare Setup Guide for Developers

Ready to build on Flare with Python? Here's your comprehensive setup guide:

## 1️⃣ Environment Setup
```bash
# Create a virtual environment in your project
python -m venv flare-env
source flare-env/bin/activate  # On Windows: flare-env\\Scripts\\activate

# Install essential packages
pip install web3==6.15.1 requests pandas python-dotenv
```

## 2️⃣ Configure Connection
Create a `flare_config.py` file:

```python
from web3 import Web3
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Flare Mainnet connection
FLARE_RPC = "https://flare-api.flare.network/ext/bc/C/rpc"
w3 = Web3(Web3.HTTPProvider(FLARE_RPC))

# FTSO Registry contract - where all the price data lives
FTSO_REGISTRY = "0x6D222fb4544ba230d4b90BA1BfC0A01A94E254c9"  # Flare Mainnet

# Test connection
def check_connection():
    connected = w3.is_connected()
    if connected:
        print(f"✅ Connected to Flare! Current block: {w3.eth.block_number}")
    else:
        print("❌ Connection failed!")
    return connected
```

## 3️⃣ Fetch FTSO Price Data
Create `flare_ftso.py`:

```python
from flare_config import w3, FTSO_REGISTRY
import json

# ABI for the required functions only (minimal)
FTSO_REGISTRY_ABI = [
    {"inputs":[{"internalType":"string","name":"_symbol","type":"string"}],"name":"getPriceForSymbol","outputs":[{"internalType":"uint256","name":"_price","type":"uint256"},{"internalType":"uint256","name":"_timestamp","type":"uint256"},{"internalType":"uint256","name":"_decimals","type":"uint256"}],"stateMutability":"view","type":"function"}
]

registry = w3.eth.contract(address=FTSO_REGISTRY, abi=FTSO_REGISTRY_ABI)

def get_flr_price():
    try:
        # Get FLR/USD price
        price, timestamp, decimals = registry.functions.getPriceForSymbol("FLR").call()
        
        # Convert to human-readable format
        actual_price = price / (10 ** decimals)
        
        return {
            "price": actual_price,
            "timestamp": timestamp,
            "decimals": decimals
        }
    except Exception as e:
        print(f"Error fetching FTSO data: {e}")
        return None
```

## 4️⃣ Test Your Integration

```python
if __name__ == "__main__":
    from flare_config import check_connection
    
    if check_connection():
        price_data = get_flr_price()
        if price_data:
            print(f"🚀 Current FLR/USD: ${price_data['price']:.4f}")
        else:
            print("❌ Failed to get price data")
```

For more advanced examples and detailed documentation, visit https://dev.flare.network/apis/
"""
                return {"classification": "ANSWER", "response": enhanced_python_response}
                
            # If no fallback matches, use the router
            try:
                # Use the imported SemanticRouterResponse enum
                from flare_ai_rag.prompts import SemanticRouterResponse
                
                return await chat_router.route_message(
                    SemanticRouterResponse.RAG_ROUTER, 
                    message.get("message", "")
                )
            except Exception as e:
                logger.warning(f"Failed to route message: {str(e)}")
                return {"classification": "ANSWER", "response": "I'm trained specifically on Flare Network information. Your question seems to be outside my knowledge base. For questions about Flare's features, technology, or ecosystem, please feel free to ask!"}
                
        except Exception as e:
            logger.exception("Error in direct chat", error=str(e))
            return {"classification": "ERROR", "response": "Sorry, there was an error processing your request. Please try again."}


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    This function:
      1. Creates a new FastAPI instance with optional CORS middleware.
      2. Loads configuration.
      3. Sets up the Gemini Router, Qdrant Retriever, and Gemini Responder.
      4. Loads RAG data and (re)generates the Qdrant collection.
      5. Initializes a ChatRouter that wraps the RAG pipeline.
      6. Registers the chat endpoint under the /chat prefix.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    app = FastAPI(title="RAG Knowledge API", version="1.0", redirect_slashes=False)

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

    # 3. Set up the Responder.
    responder_component = setup_responder(input_config)

    # Create an APIRouter for chat endpoints and initialize ChatRouter.
    chat_router = ChatRouter(
        router=APIRouter(),
        ai=base_ai,
        query_router=router_component,
        retriever=retriever_component,
        responder=responder_component,
        attestation=Vtpm(simulate=settings.simulate_attestation),
        prompts=PromptService(),
    )
    app.include_router(chat_router.router, prefix="/api/routes/chat", tags=["chat"])

    # Add custom direct endpoints with fallback responses
    setup_direct_endpoints(app, chat_router)

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
