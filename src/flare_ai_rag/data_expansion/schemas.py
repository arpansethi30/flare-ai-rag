"""
Schema classes for data expansion.

This module contains schema classes for documents and metadata.
"""

from dataclasses import dataclass
from typing import Any

@dataclass
class DocumentMetadata:
    """Metadata for a document."""
    
    source_name: str
    """Name of the source (e.g., 'Flare Documentation')."""
    
    source_url: str
    """URL where the document was found."""
    
    url: str
    """URL of the document."""
    
    title: str | None = None
    """Document title."""
    
    description: str | None = None
    """Document description."""
    
    author: str | None = None
    """Document author."""
    
    date: str | None = None
    """Document creation date."""
    
    last_updated: str | None = None
    """Document last updated date."""
    
    tags: list[str] | None = None
    """Document tags."""
    
    language: str | None = None
    """Document language."""
    
    version: str | None = None
    """Document version."""

@dataclass
class Document:
    """A document with content and metadata."""
    
    id: str
    """Unique identifier for the document."""
    
    content: str
    """Document content."""
    
    metadata: DocumentMetadata
    """Document metadata."""
    
    raw_html: str | None = None
    """Raw HTML content if from web."""

@dataclass
class DocumentChunk:
    """A chunk of a document."""
    
    id: str
    """Unique identifier for the chunk."""
    
    document_id: str
    """ID of the parent document."""
    
    content: str
    """Chunk content."""
    
    metadata: DocumentMetadata
    """Document metadata."""
    
    chunk_index: int
    """Index of this chunk in the document."""
    
    total_chunks: int
    """Total number of chunks in the document.""" 