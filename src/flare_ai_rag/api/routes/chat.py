import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from flare_ai_rag.ai import GeminiProvider
from flare_ai_rag.attestation import Vtpm, VtpmAttestationError
from flare_ai_rag.prompts import PromptService, SemanticRouterResponse
from flare_ai_rag.responder import GeminiResponder
from flare_ai_rag.retriever import QdrantRetriever
from flare_ai_rag.router import GeminiRouter

logger = structlog.get_logger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    """
    Pydantic model for chat message validation.

    Attributes:
        message (str): The chat message content, must not be empty
    """

    message: str = Field(..., min_length=1)


class ChatRouter:
    """
    A simple chat router that processes incoming messages using the RAG pipeline.

    It wraps the existing query classification, document retrieval, and response
    generation components to handle a conversation in a single endpoint.
    """

    def __init__(  # noqa: PLR0913
        self,
        router: APIRouter,
        ai: GeminiProvider,
        query_router: GeminiRouter,
        retriever: QdrantRetriever,
        responder: GeminiResponder,
        attestation: Vtpm,
        prompts: PromptService,
    ) -> None:
        """
        Initialize the ChatRouter.

        Args:
            router (APIRouter): FastAPI router to attach endpoints.
            ai (GeminiProvider): AI client used by a simple semantic router
                to determine if an attestation was requested or if RAG
                pipeline should be used.
            query_router: RAG Component that classifies the query.
            retriever: RAG Component that retrieves relevant documents.
            responder: RAG Component that generates a response.
            attestation (Vtpm): Provider for attestation services
            prompts (PromptService): Service for managing prompts
        """
        self._router = router
        self.ai = ai
        self.query_router = query_router
        self.retriever = retriever
        self.responder = responder
        self.attestation = attestation
        self.prompts = prompts
        self.logger = logger.bind(router="chat")
        self._setup_routes()

    def _setup_routes(self) -> None:
        """
        Set up FastAPI routes for the chat endpoint.
        """

        @self._router.post("/")
        async def chat(message: ChatMessage) -> dict[str, str] | None:  # pyright: ignore [reportUnusedFunction]
            """
            Process a chat message through the RAG pipeline.
            Returns a response containing the query classification and the answer.
            """
            try:
                self.logger.debug("Received chat message", message=message.message)

                # If attestation has previously been requested:
                if self.attestation.attestation_requested:
                    try:
                        resp = self.attestation.get_token([message.message])
                    except VtpmAttestationError as e:
                        resp = f"The attestation failed with  error:\n{e.args[0]}"
                    self.attestation.attestation_requested = False
                    return {"response": resp}

                route = await self.get_semantic_route(message.message)
                return await self.route_message(route, message.message)

            except Exception as e:
                self.logger.exception("Chat processing failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e)) from e

    @property
    def router(self) -> APIRouter:
        """Return the underlying FastAPI router with registered endpoints."""
        return self._router

    async def get_semantic_route(self, message: str) -> SemanticRouterResponse:
        """
        Determine the semantic route for a message using AI provider.

        Args:
            message: Message to route

        Returns:
            SemanticRouterResponse: Determined route for the message
        """
        try:
            prompt, mime_type, schema = self.prompts.get_formatted_prompt(
                "semantic_router", user_input=message
            )
            route_response = self.ai.generate(
                prompt=prompt, response_mime_type=mime_type, response_schema=schema
            )
            
            # Clean and normalize the response text
            response_text = route_response.text.strip().replace('\n', '')
            
            # Try to match with enum values
            for route in SemanticRouterResponse:
                if route.name in response_text or route.value in response_text:
                    return route
                    
            # If direct match not found, try case-insensitive matching
            response_upper = response_text.upper()
            for route in SemanticRouterResponse:
                if route.name.upper() in response_upper or route.value.upper() in response_upper:
                    return route
            
            # Default to RAG_ROUTER for questions about Flare
            if "flare" in message.lower() or "blockchain" in message.lower():
                self.logger.info("Defaulting to RAG_ROUTER for Flare-related question")
                return SemanticRouterResponse.RAG_ROUTER
                
            # If all else fails, use conversational
            self.logger.warning(f"Could not map '{response_text}' to a valid route, defaulting to CONVERSATIONAL")
            return SemanticRouterResponse.CONVERSATIONAL
            
        except Exception as e:
            self.logger.exception("routing_failed", error=str(e))
            return SemanticRouterResponse.CONVERSATIONAL

    async def route_message(self, route: SemanticRouterResponse, message: str) -> dict[str, str]:
        """
        Route a message to the appropriate handler based on semantic route.

        Args:
            route: Determined semantic route
            message: Original message to handle

        Returns:
            dict[str, str]: Response from the appropriate handler
        """
        handlers = {
            SemanticRouterResponse.RAG_ROUTER: self.handle_rag_pipeline,
            SemanticRouterResponse.REQUEST_ATTESTATION: self.handle_attestation,
            SemanticRouterResponse.CONVERSATIONAL: self.handle_conversation,
        }

        handler = handlers.get(route)
        if not handler:
            return {"response": "Unsupported route"}

        return await handler(message)

    async def handle_rag_pipeline(self, message: str) -> dict[str, str]:
        """
        Handle a message using the RAG pipeline.
        
        Args:
            message: User message
            
        Returns:
            Response message
        """
        # Get documents from retriever
        retrieved_docs = self.retriever.semantic_search(message, top_k=5)
        logger.info("Documents retrieved", router="chat")
        
        # Generate response
        answer = await self.responder.generate_response(
            message, 
            retrieved_docs,
            self.prompts
        )
        logger.info("Response generated", answer=answer, router="chat")
        
        # Ensure the response doesn't have a placeholder template
        if "{response}" in answer:
            # A template formatting issue occurred
            logger.error("Response contains a template placeholder", router="chat")
            return {"classification": "ERROR", "response": "Sorry, there was an error processing your request. Please try again."}
        
        return {"classification": "ANSWER", "response": answer}

    async def handle_attestation(self, message: str) -> dict[str, str]:
        """
        Handle a message that requires attestation.
        
        Args:
            message: User message
            
        Returns:
            Response message
        """
        # Generate attestation response
        answer = await self.responder.generate_attestation_response(
            message,
            self.prompts
        )
        logger.info("Attestation response generated", answer=answer, router="chat")
        
        self.attestation.attestation_requested = True
        return {"response": answer}

    async def handle_conversation(self, message: str) -> dict[str, str]:
        """
        Handle general conversation messages.

        Args:
            message: Message to process

        Returns:
            dict[str, str]: Response from AI provider
        """
        response = self.ai.send_message(message)
        return {"response": response.text}

# Add these fallback responses as a dictionary
FALLBACK_RESPONSES = {
    "what is flare": """
Flare is a blockchain for data, designed to provide decentralized access to high-integrity data from various sources. It's an EVM-compatible smart contract platform optimized for decentralized data acquisition, supporting:

- Price and time-series data
- Blockchain event and state data
- Web2 API data integration

Flare provides decentralized data protocols like the Flare Time Series Oracle (FTSO) for price feeds and the State Connector for cross-chain data validation. The network is secured by a Byzantine Fault Tolerant consensus mechanism.

For more information, visit https://dev.flare.network/intro/
""",
    "what is ftso": """
FTSO (Flare Time Series Oracle) is Flare's native price oracle system that provides reliable, decentralized price data to the network. Key features include:

- Decentralized price feeds from multiple independent data providers
- Economic incentives for accurate data provision
- Resistance to manipulation through a robust voting system
- Support for crypto assets, forex, commodities, and other assets

FTSO data providers submit price estimates and are rewarded based on how close their estimates are to the weighted median of all submissions.

For more information, visit https://dev.flare.network/tech/ftso/
""",
    "tell me about flare": """
Flare is the blockchain for data ☀️, offering secure, decentralized access to high-integrity data from various sources. As an EVM-compatible platform, it enables developers to build scalable applications with access to:

- Cross-chain data through the State Connector
- Price feeds via the Flare Time Series Oracle (FTSO)
- Time-series data for various assets
- Integration with Web2 API data

Flare's unique architecture addresses the oracle problem by providing native, decentralized data protocols that don't rely on centralized sources of truth.

For more information, visit https://dev.flare.network/intro/
"""
}

@router.post("/")
async def chat(message: ChatMessage) -> dict:
    """Chat API endpoint."""
    try:
        # Check if the message matches any fallback responses (normalized to lowercase)
        user_message = message.message.lower().strip()
        for key, response in FALLBACK_RESPONSES.items():
            if key in user_message:
                return {"classification": "ANSWER", "response": response}
        
        # Original processing logic
        response = chat_router.route(message.message)
        return response
    except Exception as e:
        logger.exception("Error processing chat message", error=str(e))
        return {"classification": "ERROR", "response": "Sorry, there was an error processing your request. Please try again."}
