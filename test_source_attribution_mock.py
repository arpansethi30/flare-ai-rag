"""
Mock test for source attribution feature.

This test demonstrates how the source attribution feature works
without making actual API calls.
"""

def test_source_attribution_mock():
    """
    Demonstrate how source attribution works in the responder.
    
    This function shows the enhanced context formatting with source attribution
    that would be sent to the LLM.
    """
    print("Starting source attribution mock test...")
    
    # Create mock retrieved documents with metadata
    retrieved_docs = [
        {
            "text": "Flare Network is a blockchain designed to provide data to smart contracts safely and securely.",
            "metadata": {
                "filename": "introduction.md",
                "title": "Introduction to Flare",
                "author": "Flare Team",
                "date": "2023-01-15",
                "url": "https://dev.flare.network/intro/"
            },
            "score": 0.92
        },
        {
            "text": "The Flare Time Series Oracle (FTSO) provides decentralized price feeds for various cryptocurrencies.",
            "metadata": {
                "filename": "ftso.md",
                "title": "Flare Time Series Oracle",
                "author": "Flare Labs",
                "date": "2023-02-20",
                "url": "https://dev.flare.network/ftso/"
            },
            "score": 0.85
        }
    ]
    
    # Test query
    query = "What is Flare Network and what is FTSO?"
    
    # Build enhanced context from the retrieved documents with better source information
    context = "List of retrieved documents:\n"
    for idx, doc in enumerate(retrieved_docs, start=1):
        # Extract all available metadata for better source attribution
        metadata = doc.get("metadata", {})
        identifier = metadata.get("filename", f"Doc{idx}")
        url = metadata.get("url", "")
        title = metadata.get("title", "")
        author = metadata.get("author", "")
        date = metadata.get("date", "")
        
        # Create a structured source reference
        source_info = f"Document {idx} [Source: {identifier}]"
        if title:
            source_info += f" - {title}"
        if author:
            source_info += f" by {author}"
        if date:
            source_info += f" ({date})"
        if url:
            source_info += f" URL: {url}"
            
        context += f"{source_info}:\n{doc.get('text', '')}\n\n"

    # Add citation instructions to the prompt
    citation_instructions = """
When answering, please cite your sources using the document numbers provided (e.g., [Doc1], [Doc2]).
Each claim or piece of information should be attributed to its specific source.
If information comes from multiple sources, cite all relevant documents.
If you're unsure about any information or it's not in the provided documents, clearly state this.
"""

    # Compose the enhanced prompt with citation instructions
    prompt = (
        context + 
        citation_instructions + 
        f"\nUser query: {query}\n" + 
        "Generate an answer to the user query based solely on the given context. Include proper citations to documents."
    )
    
    # Print the prompt that would be sent to the LLM
    print("\nEnhanced prompt with source attribution:")
    print("-" * 80)
    print(prompt)
    print("-" * 80)
    
    # Example of what a response with source attribution might look like
    mock_response = """
Flare Network is a blockchain designed to provide data to smart contracts safely and securely [Doc1]. It features the Flare Time Series Oracle (FTSO), which provides decentralized price feeds for various cryptocurrencies [Doc2].

The FTSO is a key component of the Flare ecosystem, enabling reliable price data to be used by applications built on the network [Doc2].

Sources:
[Doc1] Introduction to Flare by Flare Team (2023-01-15)
[Doc2] Flare Time Series Oracle by Flare Labs (2023-02-20)
"""
    
    print("\nExample response with source attribution:")
    print("-" * 80)
    print(mock_response)
    print("-" * 80)
    
    return prompt, mock_response

if __name__ == "__main__":
    test_source_attribution_mock() 