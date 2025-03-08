# Data Expansion Feature for Flare AI RAG

This module enhances the Flare AI RAG system by expanding the document collection with additional data sources while maintaining compatibility with the original dataset.

## 🔑 Key Features

- **Web Scraping**: Automatically collect content from Flare's documentation websites
- **Semantic Chunking**: Intelligent document splitting that preserves document structure
- **Extended Vector Storage**: Separate collection that works alongside the original
- **Combined Retrieval**: Query both original and expanded datasets for comprehensive answers
- **Robust Error Handling**: Graceful fallback to the original collection if issues arise
- **Configurable Source Priorities**: Control which sources have higher relevance

## 🏗️ Architecture

The data expansion feature consists of the following components:

1. **Scrapers**: Web scrapers for collecting content from various sources.
2. **Processors**: Document chunkers and formatters for optimal embedding.
3. **Storage**: Vector database integration for the expanded collection.
4. **Service**: Main orchestration service that manages the expansion process.
5. **Integration**: Combined retriever that integrates with the original system.

## 🚀 Usage

### Basic Usage

```python
from qdrant_client import QdrantClient
from src.flare_ai_rag.ai import GeminiEmbedding
from src.flare_ai_rag.data_expansion import (
    DataExpansionConfig, 
    DataExpansionService,
    CombinedRetriever
)
from src.flare_ai_rag.retriever import QdrantRetriever

# Initialize components
qdrant_client = QdrantClient("localhost", port=6333)
embedding_client = GeminiEmbedding(api_key="YOUR_API_KEY")

# Initialize original retriever
original_retriever = QdrantRetriever(...)

# Initialize expansion service
config = DataExpansionConfig.load()  # Load from config or use defaults
expansion_service = DataExpansionService(
    config=config,
    qdrant_client=qdrant_client,
    embedding_client=embedding_client
)

# Run expansion (can be scheduled as a background task)
expansion_service.expand_dataset()

# Create combined retriever
combined_retriever = CombinedRetriever(
    original_retriever=original_retriever,
    expansion_service=expansion_service,
    ratio=0.5  # Equal weight to original and expanded sources
)

# Use the combined retriever in your application
results = combined_retriever.semantic_search("What is Flare Network?", top_k=5)
```

### Configuration

The data expansion feature is highly configurable:

```python
from src.flare_ai_rag.data_expansion import (
    DataExpansionConfig,
    ScraperConfig,
    ProcessorConfig,
    StorageConfig
)

# Configure web scraping
scraper_config = ScraperConfig(
    user_agent="Flare AI RAG Bot",
    request_delay=1.0,  # Be respectful with rate limiting
    follow_links=True,
    max_depth=2
)

# Configure document processing
processor_config = ProcessorConfig(
    chunk_size=1000,
    chunk_overlap=200,
    preserve_sections=True
)

# Configure storage
storage_config = StorageConfig(
    collection_name="flare_docs_expanded",
    vector_size=768
)

# Define data sources
sources = [
    {
        "name": "Flare Developer Hub",
        "url": "https://dev.flare.network/",
        "type": "documentation",
        "priority": 1,
        "enabled": True
    },
    {
        "name": "Flare Blog",
        "url": "https://flare.network/blog/",
        "type": "blog",
        "priority": 2,
        "enabled": True
    }
]

# Create main configuration
config = DataExpansionConfig(
    sources=sources,
    scraper=scraper_config,
    processor=processor_config,
    storage=storage_config,
    enabled=True,
    data_dir="storage/expanded_data"
)

# Save configuration for future use
config.save("config/data_expansion.json")
```

## 📊 Testing

The module includes several test scripts to validate functionality:

- `test_data_expansion.py`: Tests the data collection and processing pipeline
- `test_combined_retriever.py`: Tests the integrated search functionality

To run the tests:

```bash
python test_data_expansion.py
python test_combined_retriever.py
```

## 🛠️ Implementation Details

### Web Scraper

The web scraper uses BeautifulSoup to extract content from web pages, respecting robots.txt and rate limiting. It extracts:

- Document title and content
- Metadata like author, date, sections
- Hierarchical structure
- Related links (with configurable depth)

### Semantic Chunker

The semantic chunker preserves document structure when splitting text:

- Headers stay with their content
- Lists remain intact where possible
- Paragraphs are kept whole when possible
- Long sections split at natural boundaries (sentences, list items)

### Vector Storage

The expanded dataset is stored in a separate Qdrant collection:

- Configurable vector size and distance metric
- Metadata indexed for faster filtering
- Document chunks linked to original sources
- Content stored with full source attribution

### Combined Retriever

The combined retriever enhances the original retriever:

- Queries both collections in parallel
- Configurable ratio of results from each source
- Results ranked by relevance score
- Fallback to original collection if expanded is unavailable
- Source attribution maintained in results

## 🔄 Integration with Existing System

The data expansion feature integrates seamlessly with the existing RAG system:

- No changes needed to original collection
- Expanded dataset complements rather than replaces
- Combined retriever follows the same interface as the original
- Graceful fallback if expanded dataset is unavailable
- Source attribution preserved for verifiability

## 🔒 Security and Ethics

The data expansion feature follows best practices for web scraping:

- Respects robots.txt directives
- Implements rate limiting to avoid overwhelming servers
- User-agent clearly identifies as a bot
- Only scrapes publicly available content
- Preserves attribution to original sources

## 🧩 Future Enhancements

Potential improvements to consider:

1. **Scheduled Updates**: Automatic periodic updates of expanded dataset
2. **More Data Sources**: Support for additional source types (GitHub, PDFs, etc.)
3. **Advanced Filtering**: Filter by source type, recency, or author
4. **Hybrid Search**: Combine semantic search with keyword search
5. **Incremental Updates**: Only process new or changed content

## 📝 License

This feature is part of the Flare AI RAG project and is subject to the same license terms. 