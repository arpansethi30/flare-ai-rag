"""
Integration module for data expansion.

This module provides integration between the original retriever and the extended dataset.
"""

import logging
from typing import Any, override

from flare_ai_rag.data_expansion.service import DataExpansionService
from flare_ai_rag.retriever.base import BaseRetriever

logger = logging.getLogger(__name__)


class CombinedRetriever(BaseRetriever):
    """
    Retriever that combines results from the original and extended datasets.
    
    This retriever performs semantic search across both the original collection
    and the extended dataset, and combines the results.
    """
    
    def __init__(
        self,
        original_retriever: BaseRetriever,
        expansion_service: DataExpansionService,
        max_results: int = 10,
        ratio: float = 0.5,  # 0.5 means equal weight to both sources
    ):
        """
        Initialize the combined retriever.
        
        Args:
            original_retriever: Original retriever
            expansion_service: Data expansion service
            max_results: Maximum number of results to return
            ratio: Ratio of results to take from original vs expanded (0-1)
                  where 0 means all from original, 1 means all from expanded
        """
        self.original_retriever = original_retriever
        self.expansion_service = expansion_service
        self.max_results = max_results
        self.ratio = max(0.0, min(1.0, ratio))  # Ensure ratio is between 0 and 1
        
        # For convenience, expose the embedding client from the original retriever
        self.embedding_client = original_retriever.embedding_client
    
    @override
    def semantic_search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Perform semantic search across both datasets.
        
        Args:
            query: Query string
            top_k: Number of results to return
            
        Returns:
            Combined search results
        """
        # Calculate how many results to take from each source
        expanded_k = max(1, int(top_k * self.ratio))
        original_k = max(1, top_k - expanded_k)
        
        # Get results from original retriever
        try:
            original_results = self.original_retriever.semantic_search(query, top_k=original_k)
            logger.info(f"Got {len(original_results)} results from original retriever")
        except Exception as e:
            logger.error(f"Error getting results from original retriever: {e}")
            original_results = []
        
        # Get results from expanded dataset
        try:
            expanded_results = self.expansion_service.search(query, limit=expanded_k)
            logger.info(f"Got {len(expanded_results)} results from expanded dataset")
        except Exception as e:
            logger.error(f"Error getting results from expanded dataset: {e}")
            expanded_results = []
        
        # Combine results
        combined_results = []
        
        # Add original results
        for result in original_results:
            # Add a source marker
            result["source"] = "original"
            combined_results.append(result)
        
        # Add expanded results
        for result in expanded_results:
            # Convert to the same format as original results
            formatted_result = {
                "text": result.get("text", ""),
                "score": result.get("score", 0.0),
                "source": "expanded",
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "file_name": result.get("file_name", ""),
            }
            combined_results.append(formatted_result)
        
        # Sort by score
        combined_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        # Limit to max_results
        return combined_results[:self.max_results]


class EnhancedRetriever(BaseRetriever):
    """
    Enhanced retriever that uses only the expanded dataset.
    
    This retriever is useful for testing the expanded dataset without
    the original dataset.
    """
    
    def __init__(
        self,
        expansion_service: DataExpansionService,
        embedding_client: Any,
    ):
        """
        Initialize the enhanced retriever.
        
        Args:
            expansion_service: Data expansion service
            embedding_client: Embedding client
        """
        self.expansion_service = expansion_service
        self.embedding_client = embedding_client
    
    @override
    def semantic_search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Perform semantic search on the expanded dataset.
        
        Args:
            query: Query string
            top_k: Number of results to return
            
        Returns:
            Search results
        """
        try:
            results = self.expansion_service.search(query, limit=top_k)
            logger.info(f"Got {len(results)} results from expanded dataset")
            
            # Convert to the same format as original results
            formatted_results = []
            for result in results:
                formatted_result = {
                    "text": result.get("text", ""),
                    "score": result.get("score", 0.0),
                    "source": "expanded",
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "file_name": result.get("file_name", ""),
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error getting results from expanded dataset: {e}")
            return [] 