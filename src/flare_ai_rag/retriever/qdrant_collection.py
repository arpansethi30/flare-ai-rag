import google.api_core.exceptions
import pandas as pd
import structlog
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from flare_ai_rag.ai import EmbeddingTaskType, GeminiEmbedding
from flare_ai_rag.retriever.config import RetrieverConfig
from flare_ai_rag.utils.text_utils import chunk_text, calculate_text_size

logger = structlog.get_logger(__name__)

MAX_CHUNK_SIZE = 8000  # Reduced from 10kb to ensure we stay under the limit


def _create_collection(
    client: QdrantClient, collection_name: str, vector_size: int
) -> None:
    """
    Creates a Qdrant collection with the given parameters.
    :param collection_name: Name of the collection.
    :param vector_size: Dimension of the vectors.
    """
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )


def process_document(content: str, metadata: dict) -> list[dict]:
    """
    Process a document by chunking it if necessary and preparing it for embedding.
    
    Args:
        content (str): The document content
        metadata (dict): Additional metadata for the document
    
    Returns:
        list[dict]: List of processed chunks with metadata
    """
    # Check if text needs chunking
    if calculate_text_size(content) > MAX_CHUNK_SIZE:
        logger.info(f"Chunking document with size {calculate_text_size(content)} bytes")
        chunks = chunk_text(content, MAX_CHUNK_SIZE)
    else:
        chunks = [content]
    
    # Prepare chunks with metadata
    processed_chunks = []
    for i, chunk in enumerate(chunks):
        chunk_data = {
            "text": chunk,
            "chunk_index": i,
            "total_chunks": len(chunks)
        }
        # Keep the original metadata but add our chunk info
        chunk_metadata = metadata.copy()
        chunk_metadata.update(chunk_data)
        processed_chunks.append(chunk_metadata)
    
    return processed_chunks


def generate_collection(
    df_docs: pd.DataFrame,
    qdrant_client: QdrantClient,
    retriever_config: RetrieverConfig,
    embedding_client: GeminiEmbedding,
) -> None:
    """Routine for generating a Qdrant collection for a specific CSV file type."""
    _create_collection(
        qdrant_client, retriever_config.collection_name, retriever_config.vector_size
    )
    logger.info(
        "Created the collection.", collection_name=retriever_config.collection_name
    )

    points = []
    for idx, (_, row) in enumerate(df_docs.iterrows(), start=1):
        content = row.get("content")
        if not isinstance(content, str):
            logger.warning(
                "Skipping document due to missing or invalid content.",
                filename=row.get("file_name", "unknown")
            )
            continue

        # Prepare metadata
        metadata = {
            "file_name": row.get("file_name", ""),
            "meta_data": row.get("meta_data", ""),
            "last_updated": row.get("last_updated", "")
        }
        
        # Process document into chunks with metadata
        processed_chunks = process_document(content, metadata)
        
        # Generate embeddings and create points for each chunk
        for chunk_data in processed_chunks:
            text_content = chunk_data.get("text", "")
            
            # Skip empty or oversized chunks
            if not text_content or calculate_text_size(text_content) > MAX_CHUNK_SIZE:
                logger.warning(
                    "Skipping chunk due to invalid size",
                    size=calculate_text_size(text_content) if text_content else 0,
                    max_size=MAX_CHUNK_SIZE,
                    filename=metadata["file_name"]
                )
                continue
                
            try:
                embedding = embedding_client.embed_content(
                    embedding_model=retriever_config.embedding_model,
                    contents=text_content,
                    task_type=EmbeddingTaskType.RETRIEVAL_DOCUMENT,
                )
                
                # Generate a unique integer ID by combining the document index and chunk index
                point_id = idx * 1000 + chunk_data.get("chunk_index", 0)
                
                point = PointStruct(
                    id=point_id,  # Using numeric ID format
                    vector=embedding,
                    payload=chunk_data
                )
                points.append(point)
                
            except google.api_core.exceptions.InvalidArgument as e:
                logger.warning(
                    "Failed to generate embedding.",
                    error=str(e),
                    filename=metadata["file_name"],
                    chunk_index=chunk_data.get("chunk_index", 0)
                )
                continue

    # Upload points in batches
    if points:
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            qdrant_client.upsert(
                collection_name=retriever_config.collection_name,
                points=batch
            )
            logger.info(
                "Uploaded batch of points",
                start=i,
                end=min(i + batch_size, len(points)),
                total_points=len(points)
            )
    else:
        logger.warning("No valid documents found to insert.")
