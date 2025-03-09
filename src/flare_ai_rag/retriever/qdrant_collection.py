import google.api_core.exceptions
import pandas as pd
import structlog
import uuid
import time
import random
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, PointStruct, VectorParams
from typing import Any

from flare_ai_rag.ai import EmbeddingTaskType, GeminiEmbedding
from flare_ai_rag.retriever.config import RetrieverConfig
from flare_ai_rag.utils.text_utils import chunk_text, calculate_text_size

logger = structlog.get_logger(__name__)

# Set to 7500 to be safely under Gemini's 8000 byte limit
MAX_CHUNK_SIZE = 7500


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
    for idx, (_, row) in enumerate(
        df_docs.iterrows(), start=1
    ):  # Using _ for unused variable
        content = row["content"]

        if not isinstance(content, str):
            logger.warning(
                "Skipping document due to missing or invalid content.",
                filename=row["file_name"],
            )
            continue

        try:
            embedding = embedding_client.embed_content(
                embedding_model=retriever_config.embedding_model,
                task_type=EmbeddingTaskType.RETRIEVAL_DOCUMENT,
                contents=content,
                title=str(row["file_name"]),
            )
        except google.api_core.exceptions.InvalidArgument as e:
            # Check if it's the known "Request payload size exceeds the limit" error
            # If so, downgrade it to a warning
            if "400 Request payload size exceeds the limit" in str(e):
                logger.warning(
                    "Skipping document due to size limit.",
                    filename=row["file_name"],
                )
                continue
            # Log the full traceback for other InvalidArgument errors
            logger.exception(
                "Error encoding document (InvalidArgument).",
                filename=row["file_name"],
            )
            continue
        except Exception:
            # Log the full traceback for any other errors
            logger.exception(
                "Error encoding document (general).",
                filename=row["file_name"],
            )
            continue

        payload = {
            "filename": row["file_name"],
            "metadata": row["meta_data"],
            "text": content,
        }

        point = PointStruct(
            id=idx,  # Using integer ID starting from 1
            vector=embedding,
            payload=payload,
        )
        points.append(point)

    if points:
        qdrant_client.upsert(
            collection_name=retriever_config.collection_name,
            points=points,
        )
        logger.info(
            "Collection generated and documents inserted into Qdrant successfully.",
            collection_name=retriever_config.collection_name,
            num_points=len(points),
        )
    else:
        logger.warning("No valid documents found to insert.")


class QdrantCollection:
    """Manages a Qdrant collection for document storage and retrieval."""

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str,
        vector_size: int,
        embeddings: GeminiEmbedding,
    ) -> None:
        """Initialize QdrantCollection."""
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.embeddings = embeddings

    def process_document(self, content: str, metadata: dict) -> list[dict]:
        """Process a document by chunking it and preparing it for embedding."""
        # Clean the content
        content = content.strip()
        if not content:
            return []
            
        # Check if text needs chunking
        content_size = calculate_text_size(content)
        logger.info(f"Processing document: {metadata.get('file_name', 'unknown')} ({content_size} bytes)")
        
        # Always chunk the content to ensure consistent processing
        chunks = chunk_text(content, MAX_CHUNK_SIZE)
        num_chunks = len(chunks)
        logger.info(f"Created {num_chunks} chunks for {metadata.get('file_name', 'unknown')}")
        
        # Prepare chunks with metadata
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            # Skip empty chunks
            if not chunk.strip():
                continue
                
            # Calculate chunk size
            chunk_size = calculate_text_size(chunk)
            if chunk_size > MAX_CHUNK_SIZE:
                logger.warning(
                    f"Chunk {i} in {metadata.get('file_name', 'unknown')} exceeds size limit "
                    f"({chunk_size} > {MAX_CHUNK_SIZE}), splitting further"
                )
                # Try to split the chunk further
                subchunks = chunk_text(chunk, MAX_CHUNK_SIZE)
                for j, subchunk in enumerate(subchunks):
                    subchunk_size = calculate_text_size(subchunk)
                    if subchunk_size > MAX_CHUNK_SIZE:
                        logger.error(
                            f"Subchunk {j} in chunk {i} of {metadata.get('file_name', 'unknown')} "
                            f"still exceeds limit ({subchunk_size} > {MAX_CHUNK_SIZE}), skipping"
                        )
                        continue
                    
                    if not subchunk.strip():
                        continue
                        
                    chunk_data = {
                        "text": subchunk,
                        "chunk_index": i * 1000 + j,  # Ensure unique index
                        "total_chunks": len(chunks) * 1000,  # Update total to account for subchunks
                        "is_subchunk": True,
                        "parent_chunk": i,
                        "subchunk_index": j,
                        "file_name": metadata.get("file_name", ""),
                        "meta_data": metadata.get("meta_data", {}),
                        "last_updated": metadata.get("last_updated", "")
                    }
                    processed_chunks.append(chunk_data)
            else:
                chunk_data = {
                    "text": chunk,
                    "chunk_index": i,
                    "total_chunks": num_chunks,
                    "is_subchunk": False,
                    "file_name": metadata.get("file_name", ""),
                    "meta_data": metadata.get("meta_data", {}),
                    "last_updated": metadata.get("last_updated", "")
                }
                processed_chunks.append(chunk_data)
        
        logger.info(
            f"Processed {metadata.get('file_name', 'unknown')} into {len(processed_chunks)} final chunks"
        )
        return processed_chunks

    def generate_collection(
        self,
        df: pd.DataFrame,
        collection_name: str,
        batch_size: int = 10,
        max_retries: int = 5,
        initial_delay: float = 1.0,
    ) -> None:
        """Generate a Qdrant collection from a DataFrame of documents."""
        # Initialize counters
        total_docs = len(df)
        successful_docs = 0
        failed_docs = 0
        total_chunks = 0
        failed_chunks = 0
        
        logger.info(f"Starting collection generation for {total_docs} documents")
        
        # Create collection if it doesn't exist
        _create_collection(self.client, collection_name, self.vector_size)
        
        # Skip if collection already has points
        collection_info = self.client.get_collection(collection_name)
        if collection_info.points_count > 0:
            logger.info(f"Collection {collection_name} already has points, skipping embedding generation")
            return
        
        # Process documents in batches
        for start_idx in range(0, len(df), batch_size):
            batch_df = df.iloc[start_idx:start_idx + batch_size]
            batch_points = []
            
            for _, row in batch_df.iterrows():
                try:
                    # Skip if content is missing or invalid
                    if not row.get('content') or not isinstance(row['content'], str):
                        logger.warning(f"Skipping document {row.get('file_name', 'unknown')}: Invalid or missing content")
                        failed_docs += 1
                        continue
                    
                    # Process document and get chunks
                    chunks = self.process_document(row['content'], row.to_dict())
                    if not chunks:
                        logger.warning(f"No valid chunks generated for document {row.get('file_name', 'unknown')}")
                        failed_docs += 1
                        continue
                    
                    # Generate embeddings for each chunk with rate limit handling
                    for chunk in chunks:
                        try:
                            embedding = self.embeddings.embed_content(
                                content=chunk['text'],
                                max_retries=max_retries,
                                initial_delay=initial_delay
                            )
                            
                            # Create point for the chunk
                            point = PointStruct(
                                id=str(uuid.uuid4()),
                                payload={
                                    'content': chunk['text'],
                                    'file_name': chunk['file_name'],
                                    'meta_data': chunk['meta_data'],
                                    'last_updated': chunk['last_updated'],
                                    'chunk_index': chunk['chunk_index'],
                                    'total_chunks': chunk['total_chunks'],
                                    'is_subchunk': chunk['is_subchunk'],
                                    'parent_chunk': chunk.get('parent_chunk'),
                                    'subchunk_index': chunk.get('subchunk_index')
                                },
                                vector=embedding
                            )
                            batch_points.append(point)
                            total_chunks += 1
                            
                        except Exception as e:
                            logger.error(f"Failed to generate embedding for chunk: {str(e)}")
                            failed_chunks += 1
                            continue
                    
                    successful_docs += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process document {row.get('file_name', 'unknown')}: {str(e)}")
                    failed_docs += 1
                    continue
            
            # Upload batch points if any were generated
            if batch_points:
                try:
                    self.client.upsert(
                        collection_name=collection_name,
                        points=batch_points,
                        wait=True
                    )
                    logger.info(f"Uploaded batch of {len(batch_points)} points to collection")
                except Exception as e:
                    logger.error(f"Failed to upload batch points: {str(e)}")
                    failed_chunks += len(batch_points)
            
            # Log progress
            progress = (start_idx + len(batch_df)) / total_docs * 100
            logger.info(
                f"Progress: {progress:.1f}% - "
                f"Processed {successful_docs}/{total_docs} documents "
                f"({failed_docs} failed) - "
                f"Generated {total_chunks} chunks ({failed_chunks} failed)"
            )
        
        # Log final statistics
        logger.info(
            f"Collection generation complete:\n"
            f"- Documents: {successful_docs} successful, {failed_docs} failed\n"
            f"- Chunks: {total_chunks} successful, {failed_chunks} failed"
        )
