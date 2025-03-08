"""
Semantic chunker for document processing.

This module provides a semantic chunker for processing documents into chunks.
"""

import hashlib
import logging
import re
from typing import Any

from flare_ai_rag.data_expansion.config import ProcessorConfig
from flare_ai_rag.data_expansion.schemas import Document, DocumentChunk

logger = logging.getLogger(__name__)

class SemanticChunker:
    """
    Semantic chunker for documents.
    
    This class chunks documents into semantically meaningful pieces.
    """
    
    def __init__(self, config: ProcessorConfig):
        """
        Initialize the chunker.
        
        Args:
            config: Processor configuration
        """
        self.config = config
    
    def chunk_document(self, document: Document) -> list[DocumentChunk]:
        """
        Split a document into chunks.
        
        Args:
            document: Document to chunk
            
        Returns:
            List of document chunks
        """
        # Extract sections from the document
        sections = self._extract_sections(document.content)
        
        # Process each section
        document_chunks = []
        chunk_index = 0
        
        for section in sections:
            # Skip empty sections
            if not section.strip():
                continue
            
            # Check if section is too long
            if len(section) > self.config.chunk_size:
                # Split long section
                subsections = self._split_long_section(section)
                
                # Process each subsection
                for subsection in subsections:
                    # Create chunk
                    chunk = DocumentChunk(
                        id=f"{document.id}_{chunk_index}",
                        document_id=document.id,
                        content=subsection,
                        metadata=document.metadata,
                        chunk_index=chunk_index,
                        total_chunks=0,  # Will update later
                    )
                    
                    document_chunks.append(chunk)
                    chunk_index += 1
            else:
                # Create chunk for the section
                chunk = DocumentChunk(
                    id=f"{document.id}_{chunk_index}",
                    document_id=document.id,
                    content=section,
                    metadata=document.metadata,
                    chunk_index=chunk_index,
                    total_chunks=0,  # Will update later
                )
                
                document_chunks.append(chunk)
                chunk_index += 1
        
        # Update total chunks
        total_chunks = len(document_chunks)
        for chunk in document_chunks:
            chunk.total_chunks = total_chunks
        
        return document_chunks
    
    def _extract_sections(self, text: str) -> list[str]:
        """
        Extract logical sections from text.
        
        Args:
            text: Text to extract sections from
            
        Returns:
            List of sections
        """
        # If preserve_sections is disabled, just split by size
        if not self.config.preserve_sections:
            return self._split_with_overlap(
                text, self.config.chunk_size, self.config.chunk_overlap
            )
        
        # Split by headings
        heading_pattern = r"(?:^|\n)(?:#{1,6}|\*{1,3}|\={3,}|\-{3,})\s+(.+?)(?:\n|$)"
        sections = []
        
        # Find all headings
        headings = list(re.finditer(heading_pattern, text))
        
        if not headings:
            # No headings found, split by paragraphs
            paragraphs = re.split(r"\n\s*\n", text)
            
            # Combine paragraphs to form sections
            current_section = ""
            for paragraph in paragraphs:
                if len(current_section) + len(paragraph) > self.config.chunk_size:
                    # Current section is full, start a new one
                    if current_section:
                        sections.append(current_section)
                    current_section = paragraph
                else:
                    # Add paragraph to current section
                    if current_section:
                        current_section += "\n\n" + paragraph
                    else:
                        current_section = paragraph
            
            # Add the last section
            if current_section:
                sections.append(current_section)
        else:
            # Process sections defined by headings
            for i in range(len(headings)):
                start = headings[i].start()
                
                # Determine end of section
                if i < len(headings) - 1:
                    end = headings[i + 1].start()
                else:
                    end = len(text)
                
                # Extract section
                section = text[start:end].strip()
                
                # Add section if not empty
                if section:
                    sections.append(section)
            
            # Check if there's content before the first heading
            if headings[0].start() > 0:
                first_section = text[:headings[0].start()].strip()
                if first_section:
                    sections.insert(0, first_section)
        
        # Check if any section is too long
        result = []
        for section in sections:
            if len(section) > self.config.chunk_size:
                # Split long section
                result.extend(self._split_long_section(section))
            else:
                result.append(section)
        
        return result
    
    def _split_long_section(self, section: str) -> list[str]:
        """
        Split a long section into smaller subsections.
        
        Args:
            section: Section to split
            
        Returns:
            List of subsections
        """
        # Try to split by paragraphs first
        paragraphs = re.split(r"\n\s*\n", section)
        
        if len(paragraphs) > 1:
            # Combine paragraphs to form subsections
            subsections = []
            current_subsection = ""
            
            for paragraph in paragraphs:
                if len(current_subsection) + len(paragraph) > self.config.chunk_size:
                    # Current subsection is full, start a new one
                    if current_subsection:
                        subsections.append(current_subsection)
                    
                    # Check if paragraph itself is too long
                    if len(paragraph) > self.config.chunk_size:
                        # Split paragraph by sentences
                        paragraph_parts = self._split_with_overlap(
                            paragraph, self.config.chunk_size, self.config.chunk_overlap
                        )
                        subsections.extend(paragraph_parts)
                        current_subsection = ""
                    else:
                        current_subsection = paragraph
                else:
                    # Add paragraph to current subsection
                    if current_subsection:
                        current_subsection += "\n\n" + paragraph
                    else:
                        current_subsection = paragraph
            
            # Add the last subsection
            if current_subsection:
                subsections.append(current_subsection)
            
            return subsections
        else:
            # No paragraphs, split by sentences
            return self._split_with_overlap(
                section, self.config.chunk_size, self.config.chunk_overlap
            )
    
    def _split_with_overlap(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """
        Split text into chunks of specified size with overlap.
        
        Args:
            text: Text to split
            chunk_size: Maximum chunk size
            overlap: Overlap between chunks
            
        Returns:
            List of chunks
        """
        # If text is shorter than chunk size, return as is
        if len(text) <= chunk_size:
            return [text]
        
        # Split by sentences
        sentence_pattern = r"(?<=[.!?])\s+"
        sentences = re.split(sentence_pattern, text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) > chunk_size:
                # Add current chunk to list
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Start new chunk with overlap
                if overlap > 0 and current_chunk:
                    # Try to include some context from previous chunk
                    words = current_chunk.split()
                    overlap_words = min(len(words), overlap // 5)  # Approximate words in overlap
                    
                    if overlap_words > 0:
                        overlap_text = " ".join(words[-overlap_words:])
                        current_chunk = overlap_text + " " + sentence
                    else:
                        current_chunk = sentence
                else:
                    current_chunk = sentence
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks 