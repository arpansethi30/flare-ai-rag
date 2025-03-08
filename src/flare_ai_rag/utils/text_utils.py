import re

def chunk_text(text: str, max_chunk_size: int = 10000, overlap: int = 200) -> list[str]:
    """
    Split text into chunks that respect sentence boundaries and stay within size limits.
    
    Args:
        text (str): The input text to be chunked
        max_chunk_size (int): Maximum size of each chunk in bytes (default 10kb for Gemini)
        overlap (int): Number of characters to overlap between chunks for context
    
    Returns:
        list[str]: List of text chunks
    """
    # Clean and normalize text
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Split into sentences (basic implementation)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence_size = len(sentence.encode('utf-8'))
        
        # If adding this sentence would exceed the limit
        if current_size + sentence_size > max_chunk_size and current_chunk:
            # Join current chunk and add to chunks list
            chunks.append(' '.join(current_chunk))
            
            # Start new chunk with overlap
            if current_chunk and len(current_chunk) > 1:
                # Keep last sentence for overlap
                current_chunk = [current_chunk[-1]]
                current_size = len(current_chunk[-1].encode('utf-8'))
            else:
                current_chunk = []
                current_size = 0
        
        current_chunk.append(sentence)
        current_size += sentence_size
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def calculate_text_size(text: str) -> int:
    """
    Calculate the size of text in bytes.
    
    Args:
        text (str): Input text
    
    Returns:
        int: Size in bytes
    """
    return len(text.encode('utf-8')) 