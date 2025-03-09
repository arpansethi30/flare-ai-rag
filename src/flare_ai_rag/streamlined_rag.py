"""
Streamlined RAG Pipeline

This module provides a consolidated RAG (Retrieval-Augmented Generation) pipeline
for the Flare AI application. It combines the router, retriever, and responder
components into a single, coherent workflow to reduce complexity and improve
maintainability.
"""

import json
import pandas as pd
import structlog
from pathlib import Path

from flare_ai_rag.ai import GeminiEmbedding, GeminiProvider
from flare_ai_rag.prompts import PromptService
from flare_ai_rag.settings import settings
from flare_ai_rag.retriever import generate_collection, RetrieverConfig, QdrantRetriever

# Configure logging
logger = structlog.get_logger(__name__)

class StreamlinedRAG:
    """
    A streamlined RAG pipeline that combines router, retriever, and responder
    functionality into a single class for clearer workflow and easier maintenance.
    """
    
    def __init__(self, data_path: Path | None = None, use_fallbacks: bool = True):
        """
        Initialize the streamlined RAG pipeline.
        
        Args:
            data_path: Path to data files (defaults to settings.data_path)
            use_fallbacks: Whether to use fallback responses for common queries
        """
        self.data_path = data_path or settings.data_path
        self.use_fallbacks = use_fallbacks
        self.prompt_service = PromptService()
        
        # Initialize instance variables
        self.ai_provider = None
        self.documents_df = pd.DataFrame()
        self.retriever = None
        self.qdrant_client = None
        self.embedding_client = None
        
        # Anti-hallucination system prompt
        self.anti_hallucination_prompt = """
        You are an AI assistant for Flare Network. Answer ONLY based on the provided context.
        If you don't know the answer, clearly indicate this rather than guessing.
        Never fabricate information, technical details, URLs, or documentation that isn't in the context.
        Maintain factual accuracy at all costs.
        """
        
        # Cache for fallback responses
        self.fallback_responses = {}
        
        # Load data
        self._initialize()
    
    def _initialize(self):
        """Initialize components and load necessary data."""
        logger.info("Initializing streamlined RAG pipeline")
        
        # Load document data
        self._load_documents()
        
        # Load fallback responses if enabled
        if self.use_fallbacks:
            self._load_fallback_responses()
        
        # Initialize Gemini provider
        self.ai_provider = GeminiProvider(
            api_key=settings.gemini_api_key,
            model="models/gemini-1.5-pro",
            system_instruction=self.anti_hallucination_prompt
        )
        
        # Initialize vector database connection
        self._initialize_vector_db()
        
        logger.info("Streamlined RAG pipeline initialized successfully")
    
    def _load_documents(self):
        """Load document data from CSV file."""
        try:
            csv_path = self.data_path / "docs.csv"
            logger.info(f"Loading document data from {csv_path}")
            
            if not csv_path.exists():
                logger.error(f"Document data file not found: {csv_path}")
                self.documents_df = pd.DataFrame()
                return
            
            self.documents_df = pd.read_csv(csv_path, delimiter=",", quotechar='"', escapechar='\\')
            logger.info(f"Loaded {len(self.documents_df)} documents from CSV")
            
            # Ensure required columns exist
            required_columns = ['file_name', 'meta_data', 'content', 'last_updated']
            missing_columns = [col for col in required_columns if col not in self.documents_df.columns]
            
            if missing_columns:
                logger.error(f"Missing required columns in CSV: {missing_columns}")
                self.documents_df = pd.DataFrame()
                return
                
            # Remove any rows with empty content
            initial_count = len(self.documents_df)
            self.documents_df = self.documents_df.dropna(subset=['content'])
            self.documents_df = self.documents_df[self.documents_df['content'].str.strip() != '']
            
            if len(self.documents_df) < initial_count:
                logger.warning(f"Removed {initial_count - len(self.documents_df)} rows with empty content")
            
            # Log sample of first document for debugging
            if not self.documents_df.empty:
                logger.debug("Sample document", 
                             sample=self.documents_df.iloc[0].to_dict())
        except Exception as e:
            logger.error(f"Failed to load documents: {str(e)}")
            self.documents_df = pd.DataFrame()
    
    def _load_fallback_responses(self):
        """Load fallback responses for common queries."""
        # Define basic fallbacks inline
        self.fallback_responses = {
            "what is flare": "Flare is the blockchain for data, offering secure, decentralized access to high-integrity data from other chains and the internet. Flare's Layer-1 network uniquely supports enshrined data protocols at the network layer, making it the only EVM-compatible smart contract platform optimized for decentralized data acquisition.",
            "what is ftso": "FTSO (Flare Time Series Oracle) is Flare's native price oracle system that provides reliable, decentralized price data to the network. It leverages a network of independent data providers to fetch offchain data and deliver it onchain with high integrity and minimal latency. The latest version, FTSOv2, provides feeds updating approximately every 1.8 seconds.",
            "tell me about flare": "Flare is the blockchain for data, offering developers and users secure, decentralized access to high-integrity data from other chains and the internet. Flare's Layer-1 network uniquely supports enshrined data protocols at the network layer, making it the only EVM-compatible smart contract platform optimized for decentralized data acquisition. Its core protocols include the Flare Time Series Oracle (FTSO) for price and time-series data, and the Flare Data Connector (FDC) for accessing blockchain event and state data.",
        }
        logger.info(f"Loaded {len(self.fallback_responses)} fallback responses")
    
    def _initialize_vector_db(self):
        """Initialize connection to vector database."""
        try:
            from qdrant_client import QdrantClient
            
            # Create a retriever config
            retriever_config = RetrieverConfig(
                embedding_model="models/text-embedding-004",
                collection_name="docs_collection",
                vector_size=768,
                host="localhost",
                port=6333
            )
            
            # Set up Qdrant client
            self.qdrant_client = QdrantClient(host=retriever_config.host, port=retriever_config.port)
            logger.info("Connected to Qdrant server")
            
            # Set up embedding client
            self.embedding_client = GeminiEmbedding(api_key=settings.gemini_api_key)
            
            # Only generate collection if we have documents
            if not self.documents_df.empty:
                try:
                    # Check if collection exists by attempting to get its info
                    try:
                        # This will raise an exception if the collection doesn't exist
                        self.qdrant_client.get_collection(retriever_config.collection_name)
                        logger.info(f"Collection {retriever_config.collection_name} already exists")
                        
                        # Check if it has points
                        collection_info = self.qdrant_client.get_collection(retriever_config.collection_name)
                        if collection_info.points_count > 0:
                            logger.info(f"Collection already has {collection_info.points_count} points, skipping generation")
                        else:
                            # Generate vectors if collection exists but is empty
                            logger.info("Collection exists but is empty, generating vectors")
                            generate_collection(
                                self.documents_df,
                                self.qdrant_client,
                                retriever_config,
                                self.embedding_client
                            )
                    except Exception:
                        # Collection doesn't exist, create it
                        logger.info("Collection doesn't exist, creating new collection")
                        generate_collection(
                            self.documents_df,
                            self.qdrant_client,
                            retriever_config,
                            self.embedding_client
                        )
                    
                    logger.info("Vector collection setup complete")
                except Exception as e:
                    logger.error(f"Failed to handle collection: {str(e)}")
            
            # Initialize retriever component
            self.retriever = QdrantRetriever(
                client=self.qdrant_client,
                retriever_config=retriever_config,
                embedding_client=self.embedding_client
            )
            
            logger.info("Vector database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {str(e)}")
            self.retriever = None
    
    def get_response(self, query: str) -> str:
        """
        Process a user query and generate a response using the RAG pipeline.
        
        Args:
            query: User query string
            
        Returns:
            Generated response text
        """
        logger.info(f"Processing query: {query}")
        
        # Check for fallback responses first (for common questions)
        if self.use_fallbacks:
            query_lower = query.lower().strip()
            for key, response in self.fallback_responses.items():
                if key in query_lower:
                    logger.info(f"Using fallback response for query: {query}")
                    return response
        
        # If retriever is not available, use direct answer approach
        if self.retriever is None:
            logger.warning("Retriever not available, using direct answer approach")
            return self._generate_direct_answer(query)
        
        # Retrieve relevant documents
        try:
            retrieved_docs = self.retriever.semantic_search(query, top_k=5)
            logger.info(f"Retrieved {len(retrieved_docs)} documents for query")
            
            if not retrieved_docs:
                logger.warning("No relevant documents found, using direct answer approach")
                return self._generate_direct_answer(query)
            
            # Log the top result for debugging
            if retrieved_docs:
                for i, doc in enumerate(retrieved_docs[:3]):
                    logger.debug(f"Retrieved document {i+1} (score: {doc.get('score', 0):.4f})",
                                text=doc.get("text", "")[:500] + "..." if len(doc.get("text", "")) > 500 else doc.get("text", ""),
                                metadata=doc.get("metadata", {}))
            
            # Generate response with retrieved context
            response = self._generate_response_with_context(query, retrieved_docs)
            return response
        except Exception as e:
            logger.error(f"Error in retrieval process: {str(e)}")
            return self._generate_direct_answer(query)
    
    def _generate_direct_answer(self, query: str) -> str:
        """Generate a direct answer without using retrieved context."""
        from flare_ai_rag.prompts.templates import DIRECT_ANSWER_PROMPT
        
        prompt = DIRECT_ANSWER_PROMPT.format(query=query)
        logger.debug("Using direct answer prompt", prompt_sample=prompt[:200] + "...")
        
        try:
            response = self.ai_provider.generate(prompt)
            logger.info(f"Generated direct answer: {response.text[:100]}...")
            return response.text
        except Exception as e:
            logger.error(f"Failed to generate direct answer: {str(e)}")
            return f"I apologize, but I couldn't find specific information about '{query}' in my knowledge base."
    
    def _generate_response_with_context(self, query: str, context: list[dict]) -> str:
        """Generate a response using retrieved context documents."""
        # Format context for the prompt
        formatted_context = self._format_context(context)
        
        # Get the system prompt with context
        from flare_ai_rag.prompts.templates import RESPONDER_SYSTEM_PROMPT
        
        prompt = RESPONDER_SYSTEM_PROMPT.format(
            context=formatted_context,
            query=query
        )
        
        try:
            response = self.ai_provider.generate(prompt)
            logger.info(f"Generated response with context: {response.text[:100]}...")
            return response.text
        except Exception as e:
            logger.error(f"Failed to generate response with context: {str(e)}")
            return self._generate_direct_answer(query)
    
    def _format_context(self, context_docs: list[dict]) -> str:
        """Format retrieved context documents for inclusion in the prompt."""
        if not context_docs:
            return "No relevant context available."
        
        formatted_context = []
        for i, doc in enumerate(context_docs, 1):
            # First try to get text from the 'text' field as expected
            text = doc.get("text", "")
            
            # If text is empty, check the metadata for 'content' field (seen in logs)
            if not text and "metadata" in doc and "content" in doc["metadata"]:
                text = doc["metadata"]["content"]
                
            if not text:
                continue
                
            # Truncate very long texts to avoid context overflow
            if len(text) > 2000:
                text = text[:2000] + "... [truncated]"
                
            # Include metadata if available
            metadata = doc.get("metadata", {})
            source = metadata.get("file_name", metadata.get("filename", f"Document {i}"))
            score = doc.get("score", 0)
            
            formatted_doc = f"SOURCE {i} (Relevance: {score:.4f}): {source}\n{text}"
            formatted_context.append(formatted_doc)
            
        return "\n\n".join(formatted_context)


def create_streamlined_rag() -> StreamlinedRAG:
    """Create and return a StreamlinedRAG instance with default settings."""
    return StreamlinedRAG() 