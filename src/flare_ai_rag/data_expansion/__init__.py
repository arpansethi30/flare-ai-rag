"""
Data Expansion Module for Flare AI RAG.

This module extends the dataset with additional Flare documentation sources
while maintaining compatibility with the original dataset.
"""

from .config import DataExpansionConfig, ScraperConfig, ProcessorConfig, StorageConfig
from .integration import CombinedRetriever
from .schemas import Document, DocumentChunk, DocumentMetadata
from .service import DataExpansionService

__all__ = [
    "CombinedRetriever",
    "DataExpansionConfig",
    "DataExpansionService",
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
    "ProcessorConfig",
    "ScraperConfig",
    "StorageConfig",
] 