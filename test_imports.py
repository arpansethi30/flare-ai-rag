"""
Simple test script to verify imports work correctly.
"""

def test_imports():
    """Test that all necessary imports work."""
    print("Testing imports...")
    
    # Test BeautifulSoup
    print("Importing BeautifulSoup...", end=" ")
    try:
        from bs4 import BeautifulSoup
        print("Success!")
    except ImportError as e:
        print(f"Failed: {e}")
    
    # Test Qdrant
    print("Importing Qdrant...", end=" ")
    try:
        from qdrant_client import QdrantClient
        print("Success!")
    except ImportError as e:
        print(f"Failed: {e}")
    
    # Test Google Generative AI
    print("Importing Google Generative AI...", end=" ")
    try:
        import google.generativeai as genai
        print("Success!")
    except ImportError as e:
        print(f"Failed: {e}")
    
    # Test dotenv
    print("Importing dotenv...", end=" ")
    try:
        from dotenv import load_dotenv
        print("Success!")
    except ImportError as e:
        print(f"Failed: {e}")
    
    print("\nAll imports tested!")

if __name__ == "__main__":
    test_imports() 