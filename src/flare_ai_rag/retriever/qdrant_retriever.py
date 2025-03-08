from typing import override

from qdrant_client import QdrantClient

from flare_ai_rag.ai import EmbeddingTaskType, GeminiEmbedding
from flare_ai_rag.retriever.base import BaseRetriever
from flare_ai_rag.retriever.config import RetrieverConfig
from flare_ai_rag.utils.text_utils import chunk_text, calculate_text_size


class QdrantRetriever(BaseRetriever):
    def __init__(
        self,
        client: QdrantClient,
        retriever_config: RetrieverConfig,
        embedding_client: GeminiEmbedding,
    ) -> None:
        """Initialize the QdrantRetriever."""
        self.client = client
        self.retriever_config = retriever_config
        self.embedding_client = embedding_client
        self.max_chunk_size = 10000  # 10kb limit for Gemini embeddings

    def process_document(self, text: str, metadata: dict | None = None) -> list[dict]:
        """
        Process a document by chunking it and preparing it for embedding.
        
        Args:
            text (str): The document text
            metadata (dict | None): Additional metadata for the document
        
        Returns:
            list[dict]: List of processed chunks with metadata
        """
        # Check if text needs chunking
        if calculate_text_size(text) > self.max_chunk_size:
            chunks = chunk_text(text, self.max_chunk_size)
        else:
            chunks = [text]
        
        # Prepare chunks with metadata
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_data = {
                "text": chunk,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            if metadata:
                chunk_data.update(metadata)
            processed_chunks.append(chunk_data)
        
        return processed_chunks

    @override
    def semantic_search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Perform semantic search by converting the query into a vector
        and searching in Qdrant.

        Args:
            query (str): The input query
            top_k (int): Number of top results to return
        
        Returns:
            list[dict]: A list of dictionaries, each representing a retrieved document
        """
        # Convert the query into a vector embedding using Gemini
        query_vector = self.embedding_client.embed_content(
            embedding_model="models/text-embedding-004",
            contents=query,
            task_type=EmbeddingTaskType.RETRIEVAL_QUERY,
        )

        # Search Qdrant for similar vectors
        results = self.client.search(
            collection_name=self.retriever_config.collection_name,
            query_vector=query_vector,
            limit=top_k,
        )

        # Process and return results
        output = []
        for hit in results:
            if hit.payload:
                result = {
                    "text": hit.payload.get("text", ""),
                    "score": hit.score,
                }
                # Include any additional metadata from the payload
                for key, value in hit.payload.items():
                    if key != "text":
                        result[key] = value
                output.append(result)
        
        return output
