"""
Data expansion service.

This module provides a service for expanding the dataset with
additional sources while maintaining compatibility with the original dataset.
"""

import hashlib
import logging
import os
import uuid
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any, List, Dict, Optional

from qdrant_client import QdrantClient

from flare_ai_rag.ai import GeminiEmbedding, EmbeddingTaskType
from flare_ai_rag.data_expansion.config import DataExpansionConfig
from flare_ai_rag.data_expansion.processors import SemanticChunker
from flare_ai_rag.data_expansion.schemas import Document, DocumentChunk, DocumentMetadata
from flare_ai_rag.data_expansion.scrapers import WebScraper
from flare_ai_rag.data_expansion.storage import ExtendedCollection

logger = logging.getLogger(__name__)


class DataExpansionService:
    """
    Service for expanding the dataset with additional sources.
    
    This class orchestrates the data collection, processing, and storage process.
    """
    
    def __init__(
        self,
        config: DataExpansionConfig,
        qdrant_client: QdrantClient,
        embedding_client: GeminiEmbedding
    ):
        """
        Initialize the data expansion service.
        
        Args:
            config: Data expansion configuration
            qdrant_client: Qdrant client
            embedding_client: Embedding client
        """
        self.config = config
        self.qdrant_client = qdrant_client
        self.embedding_client = embedding_client
        
        # Create data directory if it doesn't exist
        Path(self.config.data_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.scraper = WebScraper(config.scraper)
        self.chunker = SemanticChunker(config.processor)
        self.collection = ExtendedCollection(
            client=qdrant_client,
            config=config.storage,
            embedding_client=embedding_client
        )
    
    def expand_dataset(self) -> dict[str, Any]:
        """
        Expand the dataset with additional sources.
        
        Returns:
            Dictionary with results
        """
        if not self.config.enabled:
            logger.info("Data expansion is disabled")
            return {"status": "disabled"}
        
        start_time = datetime.now()
        
        results = {
            "sources_processed": 0,
            "documents_collected": 0,
            "chunks_stored": 0,
            "errors": [],
            "start_time": start_time.isoformat(),
        }
        
        # Process each enabled source
        for source in self.config.sources:
            if not source.get("enabled", False):
                logger.info(f"Skipping disabled source: {source['name']}")
                continue
            
            try:
                logger.info(f"Processing source: {source['name']}")
                
                # Scrape documents from the source
                url = source["url"]
                source_name = source["name"]
                
                # Count documents collected from this source
                source_docs = 0
                source_chunks = 0
                
                # Process documents
                for document in self.scraper.scrape(url, source_name):
                    # Save raw document to disk
                    self._save_document(document)
                    
                    # Chunk document
                    chunks = self.chunker.chunk_document(document)
                    
                    # Store chunks
                    self.collection.store_chunks(chunks)
                    
                    source_docs += 1
                    source_chunks += len(chunks)
                    
                    # Log progress
                    logger.info(
                        f"Processed document: {document.id} ({len(chunks)} chunks)")
                    
                    # Respect the max documents limit
                    if source_docs >= self.config.processor.max_documents_per_run:
                        logger.info(
                            f"Reached maximum documents limit ({self.config.processor.max_documents_per_run})")
                        break
                
                # Update results
                results["sources_processed"] += 1
                results["documents_collected"] += source_docs
                results["chunks_stored"] += source_chunks
                
                logger.info(
                    f"Completed source: {source_name} - {source_docs} documents, {source_chunks} chunks")
            
            except Exception as e:
                logger.error(f"Error processing source {source['name']}: {str(e)}")
                results["errors"].append({
                    "source": source["name"],
                    "error": str(e)
                })
        
        # Record end time
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        results["end_time"] = end_time.isoformat()
        results["duration_seconds"] = duration
        
        logger.info(f"Data expansion completed in {duration:.2f} seconds")
        logger.info(f"Processed {results['sources_processed']} sources, "
                    f"collected {results['documents_collected']} documents, "
                    f"stored {results['chunks_stored']} chunks")
        
        if results["errors"]:
            logger.warning(f"Encountered {len(results['errors'])} errors during processing")
        
        return results
    
    def search_expanded_dataset(self, 
                                query: str, 
                                top_k: int = 5, 
                                filter_params: dict | None = None
                               ) -> list[dict[str, Any]]:
        """
        Search the expanded dataset.
        
        Args:
            query: Search query
            top_k: Maximum number of results to return
            filter_params: Optional filter parameters
            
        Returns:
            List of matching documents
        """
        if not self.config.enabled:
            logger.info("Data expansion is disabled, returning empty results")
            return []
        
        return self.collection.search(query, top_k, filter_params)
    
    def get_collection_info(self) -> dict[str, Any]:
        """
        Get information about the extended collection.
        
        Returns:
            Dictionary with collection information
        """
        return self.collection.get_collection_info()
    
    def clear_collection(self) -> None:
        """Clear all documents from the collection."""
        self.collection.clear_collection()
    
    def _save_document(self, document: Document) -> None:
        """
        Save a document to disk.
        
        Args:
            document: Document to save
        """
        # Create a directory for the source if it doesn't exist
        source_dir = os.path.join(
            self.config.data_dir,
            document.metadata.source_name.replace(" ", "_").lower()
        )
        Path(source_dir).mkdir(parents=True, exist_ok=True)
        
        # Save document as JSON
        document_path = os.path.join(source_dir, f"{document.id}.json")
        
        # Use Path to write the file
        doc_dict = document.to_dict()
        
        # Write to a temporary file first and then rename to avoid partial writes
        temp_path = f"{document_path}.tmp"
        with open(temp_path, "w") as f:
            import json
            json.dump(doc_dict, f, indent=2)
        
        # Rename to final path
        os.rename(temp_path, document_path)
        
        logger.debug(f"Saved document to {document_path}") 