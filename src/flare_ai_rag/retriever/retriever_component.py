"""RetrieverComponent for handling document search and retrieval."""

import structlog
from typing import Any

from flare_ai_rag.ai import GeminiEmbedding
from flare_ai_rag.retriever.qdrant_collection import QdrantCollection

logger = structlog.get_logger(__name__)

class RetrieverComponent:
    """Component for retrieving relevant documents using semantic search."""

    def __init__(
        self,
        collection: QdrantCollection,
        embeddings: GeminiEmbedding,
        top_k: int = 5,
        score_threshold: float = 0.7,
    ) -> None:
        """Initialize RetrieverComponent.
        
        Args:
            collection: QdrantCollection for document storage
            embeddings: Embedding model for query encoding
            top_k: Number of results to return
            score_threshold: Minimum similarity score to include results
        """
        self.collection = collection
        self.embeddings = embeddings
        self.top_k = top_k
        self.score_threshold = score_threshold

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Search for relevant documents using semantic similarity.
        
        Args:
            query: Search query string
            
        Returns:
            List of relevant documents with metadata and similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_content(
                content=query,
                max_retries=5,
                initial_delay=1.0
            )
            
            # Search collection
            search_results = self.collection.client.search(
                collection_name=self.collection.collection_name,
                query_vector=query_embedding,
                limit=self.top_k,
                score_threshold=self.score_threshold
            )
            
            # Format results
            results = []
            for hit in search_results:
                result = {
                    'content': hit.payload['content'],
                    'file_name': hit.payload['file_name'],
                    'meta_data': hit.payload['meta_data'],
                    'last_updated': hit.payload['last_updated'],
                    'chunk_index': hit.payload['chunk_index'],
                    'total_chunks': hit.payload['total_chunks'],
                    'score': hit.score
                }
                results.append(result)
            
            logger.info(
                f"Found {len(results)} relevant documents for query",
                query=query[:100],
                top_score=results[0]['score'] if results else None
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return [] 