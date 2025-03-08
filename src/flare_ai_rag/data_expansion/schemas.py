"""
Schemas for the data expansion module.

This module defines the document schemas used for expanded data sources.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Dict


@dataclass
class DocumentMetadata:
    """Metadata for a document."""
    source_name: str
    source_url: str
    url: str
    title: str
    description: str = ""
    author: str = ""
    date: str = ""
    last_updated: str = ""
    type: str = "documentation"  # documentation, blog, repository, etc.
    section: str = ""
    subsection: str = ""
    tags: List[str] = field(default_factory=list)
    language: str = "en"
    version: str = ""
    priority: int = 5  # 1 is highest priority, 10 is lowest
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """A document from an expanded data source."""
    id: str  # Unique identifier
    content: str  # Full document content
    metadata: DocumentMetadata
    raw_html: str = ""  # Original HTML if applicable
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": {
                "source_name": self.metadata.source_name,
                "source_url": self.metadata.source_url,
                "url": self.metadata.url,
                "title": self.metadata.title,
                "description": self.metadata.description,
                "author": self.metadata.author,
                "date": self.metadata.date,
                "last_updated": self.metadata.last_updated,
                "type": self.metadata.type,
                "section": self.metadata.section,
                "subsection": self.metadata.subsection,
                "tags": self.metadata.tags,
                "language": self.metadata.language,
                "version": self.metadata.version,
                "priority": self.metadata.priority,
                "extra": self.metadata.extra,
            },
            "raw_html": self.raw_html,
            "processed_at": self.processed_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            metadata=DocumentMetadata(
                source_name=data["metadata"]["source_name"],
                source_url=data["metadata"]["source_url"],
                url=data["metadata"]["url"],
                title=data["metadata"]["title"],
                description=data["metadata"].get("description", ""),
                author=data["metadata"].get("author", ""),
                date=data["metadata"].get("date", ""),
                last_updated=data["metadata"].get("last_updated", ""),
                type=data["metadata"].get("type", "documentation"),
                section=data["metadata"].get("section", ""),
                subsection=data["metadata"].get("subsection", ""),
                tags=data["metadata"].get("tags", []),
                language=data["metadata"].get("language", "en"),
                version=data["metadata"].get("version", ""),
                priority=data["metadata"].get("priority", 5),
                extra=data["metadata"].get("extra", {}),
            ),
            raw_html=data.get("raw_html", ""),
            processed_at=data.get("processed_at", datetime.now().isoformat()),
        )


@dataclass
class DocumentChunk:
    """A chunk of a document for embedding and retrieval."""
    id: str  # Unique identifier (document_id + chunk_index)
    document_id: str  # ID of the parent document
    content: str  # Chunk content
    metadata: DocumentMetadata
    chunk_index: int  # Index of this chunk in the document
    total_chunks: int  # Total number of chunks in the document
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "metadata": {
                "source_name": self.metadata.source_name,
                "source_url": self.metadata.source_url,
                "url": self.metadata.url,
                "title": self.metadata.title,
                "description": self.metadata.description,
                "author": self.metadata.author,
                "date": self.metadata.date,
                "last_updated": self.metadata.last_updated,
                "type": self.metadata.type,
                "section": self.metadata.section,
                "subsection": self.metadata.subsection,
                "tags": self.metadata.tags,
                "language": self.metadata.language,
                "version": self.metadata.version,
                "priority": self.metadata.priority,
                "extra": self.metadata.extra,
            },
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentChunk":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            document_id=data["document_id"],
            content=data["content"],
            metadata=DocumentMetadata(
                source_name=data["metadata"]["source_name"],
                source_url=data["metadata"]["source_url"],
                url=data["metadata"]["url"],
                title=data["metadata"]["title"],
                description=data["metadata"].get("description", ""),
                author=data["metadata"].get("author", ""),
                date=data["metadata"].get("date", ""),
                last_updated=data["metadata"].get("last_updated", ""),
                type=data["metadata"].get("type", "documentation"),
                section=data["metadata"].get("section", ""),
                subsection=data["metadata"].get("subsection", ""),
                tags=data["metadata"].get("tags", []),
                language=data["metadata"].get("language", "en"),
                version=data["metadata"].get("version", ""),
                priority=data["metadata"].get("priority", 5),
                extra=data["metadata"].get("extra", {}),
            ),
            chunk_index=data["chunk_index"],
            total_chunks=data["total_chunks"],
        ) 