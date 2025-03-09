"""
Text utility functions for processing text data.

This module provides utility functions for working with text data,
including chunking text into smaller pieces, calculating text size, etc.
"""

import re

def calculate_text_size(text: str) -> int:
    """
    Calculate the approximate byte size of a text string.
    
    Args:
        text: The text to measure
        
    Returns:
        The approximate size in bytes
    """
    return len(text.encode('utf-8'))

def chunk_text(text: str, max_chunk_size: int = 7500) -> list[str]:
    """
    Split text into chunks that are approximately within the specified size limit.
    Attempts to split on paragraph boundaries where possible, falling back to 
    sentence boundaries if necessary.
    
    Args:
        text: The text to chunk
        max_chunk_size: Maximum bytes per chunk
        
    Returns:
        List of text chunks
    """
    # If text is already small enough, return it as a single chunk
    if calculate_text_size(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    
    # Split by paragraphs first (two newlines)
    paragraphs = re.split(r'\n\s*\n', text)
    
    current_chunk = []
    current_size = 0
    
    for paragraph in paragraphs:
        paragraph_size = calculate_text_size(paragraph)
        
        # If a single paragraph is larger than max_chunk_size, split it by sentences
        if paragraph_size > max_chunk_size:
            sentences = split_into_sentences(paragraph)
            for sentence in sentences:
                sentence_size = calculate_text_size(sentence)
                
                # If adding this sentence would exceed the chunk size, 
                # save the current chunk and start a new one
                if current_size + sentence_size > max_chunk_size and current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # If a single sentence is too large, split it by word count
                if sentence_size > max_chunk_size:
                    sentence_chunks = split_by_words(sentence, max_chunk_size)
                    for s_chunk in sentence_chunks:
                        chunks.append(s_chunk)
                else:
                    current_chunk.append(sentence)
                    current_size += sentence_size
        else:
            # If adding this paragraph would exceed the chunk size, 
            # save the current chunk and start a new one
            if current_size + paragraph_size > max_chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_size = 0
            
            current_chunk.append(paragraph)
            current_size += paragraph_size
    
    # Add the final chunk if it's not empty
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks

def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences, trying to preserve sentence boundaries.
    
    Args:
        text: The text to split
        
    Returns:
        List of sentences
    """
    # Basic sentence splitting - not perfect but good enough for most cases
    sentence_endings = r'(?<=[.!?])\s+'
    sentences = re.split(sentence_endings, text)
    return [s.strip() for s in sentences if s.strip()]

def split_by_words(text: str, max_chunk_size: int) -> list[str]:
    """
    Split text by word boundaries to stay within the max_chunk_size.
    
    Args:
        text: The text to split
        max_chunk_size: Maximum bytes per chunk
        
    Returns:
        List of text chunks
    """
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    
    for word in words:
        word_size = calculate_text_size(word + ' ')
        
        if current_size + word_size > max_chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_size = 0
        
        current_chunk.append(word)
        current_size += word_size
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks 