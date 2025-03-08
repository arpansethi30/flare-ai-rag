"""
Integration module for data expansion.

This module provides integration between the original retriever and the extended dataset.
"""

import logging
from collections.abc import Generator
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
    
    @override
    def semantic_search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Perform semantic search across both datasets.
        
        Args:
            query: Query string
            top_k: Maximum number of results to return
            
        Returns:
            List of document dictionaries with combined results
        """
        # Calculate how many results to take from each source
        original_k = int(top_k * (1 - self.ratio))
        expanded_k = top_k - original_k
        
        # Ensure we always get at least one result from each source if ratio is not 0 or 1
        if 0 < self.ratio < 1:
            original_k = max(1, original_k)
            expanded_k = max(1, expanded_k)
            # Recalculate total if needed
            if original_k + expanded_k > top_k:
                # Prioritize expanded results slightly
                original_k = top_k - expanded_k
        
        # Get results from original retriever
        logger.debug(f"Querying original retriever for {original_k} results")
        original_results = []
        if original_k > 0:
            try:
                original_results = self.original_retriever.semantic_search(query, original_k)
                logger.debug(f"Got {len(original_results)} results from original retriever")
            except Exception as e:
                logger.error(f"Error retrieving from original source: {e}")
        
        # Get results from expanded dataset
        logger.debug(f"Querying expanded dataset for {expanded_k} results")
        expanded_results = []
        if expanded_k > 0:
            try:
                # Check if data expansion is enabled
                if self.expansion_service.config.enabled:
                    expanded_results = self.expansion_service.search_expanded_dataset(
                        query, expanded_k
                    )
                    logger.debug(f"Got {len(expanded_results)} results from expanded dataset")
                else:
                    logger.debug("Data expansion is disabled, skipping")
            except Exception as e:
                logger.error(f"Error retrieving from expanded dataset: {e}")
        
        # Combine results
        combined_results = self._combine_results(original_results, expanded_results)
        
        return combined_results[:top_k]
    
    def _combine_results(
        self, original_results: list[dict], expanded_results: list[dict]
    ) -> list[dict]:
        """
        Combine results from both sources, ordering by relevance score.
        
        Args:
            original_results: Results from original retriever
            expanded_results: Results from expanded dataset
            
        Returns:
            Combined and sorted list of results
        """
        # Convert expanded results to match original format if needed
        normalized_expanded = []
        for result in expanded_results:
            # Create a normalized result that matches the original format
            normalized = {
                "text": result.get("text", ""),
                "score": result.get("score", 0.0),
                # Add a source identifier
                "source": "expanded",
            }
            
            # Copy metadata
            metadata = result.get("metadata", {})
            if metadata:
                normalized["metadata"] = metadata
            
            normalized_expanded.append(normalized)
        
        # Add source identifier to original results
        for result in original_results:
            result["source"] = "original"
        
        # Combine and sort by score
        combined = original_results + normalized_expanded
        combined.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        return combined 