"""
Configuration settings for the data expansion module.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_SOURCES = [
    {
        "name": "Flare Developer Hub",
        "url": "https://dev.flare.network/",
        "type": "documentation",
        "priority": 1,
        "enabled": True,
    },
    {
        "name": "Flare GitHub",
        "url": "https://github.com/flare-foundation",
        "type": "repository",
        "priority": 2,
        "enabled": False,  # Disabled by default for initial testing
    },
    {
        "name": "Flare Blog",
        "url": "https://flare.network/blog/",
        "type": "blog",
        "priority": 3,
        "enabled": False,  # Disabled by default for initial testing
    }
]

@dataclass
class ScraperConfig:
    """Configuration for web scraping."""
    user_agent: str = "Flare AI RAG Data Collector (Hackathon Project)"
    request_delay: float = 1.0  # Delay between requests in seconds
    timeout: int = 30  # Request timeout in seconds
    max_retries: int = 3
    respect_robots_txt: bool = True
    follow_links: bool = True
    max_depth: int = 2  # Maximum link following depth


@dataclass
class ProcessorConfig:
    """Configuration for document processing."""
    chunk_size: int = 1000  # Target chunk size in characters
    chunk_overlap: int = 200  # Overlap between chunks
    min_chunk_size: int = 100  # Minimum chunk size to index
    preserve_sections: bool = True  # Keep sections together when possible
    max_documents_per_run: int = 100  # Maximum documents to process in one run


@dataclass
class StorageConfig:
    """Configuration for document storage."""
    collection_name: str = "flare_docs_extended"
    vector_size: int = 768  # For text-embedding-004
    create_if_missing: bool = True
    

@dataclass
class DataExpansionConfig:
    """Main configuration for the data expansion module."""
    sources: list[dict[str, Any]]
    scraper: ScraperConfig
    processor: ProcessorConfig
    storage: StorageConfig
    enabled: bool = True
    data_dir: str = "storage/expanded_data"
    
    @classmethod
    def load(cls, config_path: str | None = None) -> "DataExpansionConfig":
        """
        Load configuration from file or use defaults.
        
        Args:
            config_path: Path to configuration file. If None, uses defaults.
            
        Returns:
            DataExpansionConfig instance
        """
        if config_path and os.path.exists(config_path):
            with open(config_path, "r") as f:
                config_data = json.load(f)
                
            return cls(
                sources=config_data.get("sources", DEFAULT_SOURCES),
                scraper=ScraperConfig(**config_data.get("scraper", {})),
                processor=ProcessorConfig(**config_data.get("processor", {})),
                storage=StorageConfig(**config_data.get("storage", {})),
                enabled=config_data.get("enabled", True),
                data_dir=config_data.get("data_dir", "storage/expanded_data"),
            )
        
        # Use defaults
        return cls(
            sources=DEFAULT_SOURCES,
            scraper=ScraperConfig(),
            processor=ProcessorConfig(),
            storage=StorageConfig(),
            enabled=True,
            data_dir="storage/expanded_data",
        )
    
    def save(self, config_path: str) -> None:
        """
        Save configuration to file.
        
        Args:
            config_path: Path to save configuration file
        """
        # Ensure directory exists
        Path(os.path.dirname(config_path)).mkdir(parents=True, exist_ok=True)
        
        config_data = {
            "sources": self.sources,
            "scraper": {
                "user_agent": self.scraper.user_agent,
                "request_delay": self.scraper.request_delay,
                "timeout": self.scraper.timeout,
                "max_retries": self.scraper.max_retries,
                "respect_robots_txt": self.scraper.respect_robots_txt,
                "follow_links": self.scraper.follow_links,
                "max_depth": self.scraper.max_depth,
            },
            "processor": {
                "chunk_size": self.processor.chunk_size,
                "chunk_overlap": self.processor.chunk_overlap,
                "min_chunk_size": self.processor.min_chunk_size,
                "preserve_sections": self.processor.preserve_sections,
                "max_documents_per_run": self.processor.max_documents_per_run,
            },
            "storage": {
                "collection_name": self.storage.collection_name,
                "vector_size": self.storage.vector_size,
                "create_if_missing": self.storage.create_if_missing,
            },
            "enabled": self.enabled,
            "data_dir": self.data_dir,
        }
        
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2) 