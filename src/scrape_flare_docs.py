import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from flare_ai_rag.data_expansion.scrapers.web_scraper import WebScraper
from flare_ai_rag.data_expansion.config import ScraperConfig
from flare_ai_rag.data_expansion.processors.chunker import SemanticChunker
from flare_ai_rag.data_expansion.config import ProcessorConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define sources to scrape
SOURCES = [
    {
        "url": "https://docs.flare.network/",
        "name": "Flare Documentation"
    },
    {
        "url": "https://github.com/flare-foundation",
        "name": "Flare GitHub"
    },
    {
        "url": "https://flare.network/",
        "name": "Flare Website"
    },
    {
        "url": "https://docs.flare.network/dev/",
        "name": "Flare Developer Hub"
    }
]

def main():
    # Configure scraper
    scraper_config = ScraperConfig(
        user_agent="FlareAIBot/1.0",
        follow_links=True,
        follow_external_links=True,
        request_delay=1.0,
        max_depth=3
    )
    
    # Configure chunker
    processor_config = ProcessorConfig(
        chunk_size=1000,
        overlap=100
    )
    
    # Initialize scraper and chunker
    scraper = WebScraper(scraper_config)
    chunker = SemanticChunker(processor_config)
    
    # Create data directory if it doesn't exist
    data_dir = Path("src/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Load existing docs if any
    docs_file = data_dir / "docs.csv"
    if docs_file.exists():
        existing_docs = pd.read_csv(docs_file)
        existing_urls = set(existing_docs.get("source_url", []))
    else:
        existing_docs = pd.DataFrame()
        existing_urls = set()
    
    # Collect new documents
    new_docs = []
    
    for source in SOURCES:
        logger.info(f"Scraping {source['name']} from {source['url']}")
        try:
            for doc in scraper.scrape(source["url"], source["name"]):
                # Skip if already exists
                if doc.metadata.source_url in existing_urls:
                    continue
                    
                # Chunk document if needed
                chunks = chunker.chunk_document(doc)
                
                # Add each chunk as a separate document
                for chunk in chunks:
                    new_docs.append({
                        "file_name": f"{doc.metadata.source_name}/{chunk.id}",
                        "meta_data": {
                            "title": doc.metadata.title,
                            "description": doc.metadata.description,
                            "author": doc.metadata.author,
                            "tags": doc.metadata.tags,
                            "language": doc.metadata.language,
                            "version": doc.metadata.version,
                            "source_url": doc.metadata.source_url,
                            "chunk_index": chunk.chunk_index,
                            "total_chunks": chunk.total_chunks
                        },
                        "content": chunk.content,
                        "last_updated": doc.metadata.last_updated or datetime.now().isoformat()
                    })
                
                if len(new_docs) % 10 == 0:
                    logger.info(f"Collected {len(new_docs)} new documents")
                    
        except Exception as e:
            logger.error(f"Error scraping {source['name']}: {e}")
            continue
    
    if new_docs:
        # Convert to DataFrame
        new_docs_df = pd.DataFrame(new_docs)
        
        # Combine with existing docs
        if not existing_docs.empty:
            combined_docs = pd.concat([existing_docs, new_docs_df], ignore_index=True)
        else:
            combined_docs = new_docs_df
        
        # Save to CSV
        combined_docs.to_csv(docs_file, index=False)
        logger.info(f"Saved {len(new_docs)} new documents to {docs_file}")
    else:
        logger.info("No new documents found")

if __name__ == "__main__":
    main() 