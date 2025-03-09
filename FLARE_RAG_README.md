# Flare Developer Hub RAG System

This system scrapes data from the Flare Developer Hub and uses it to provide answers in a chat interface using Retrieval Augmented Generation (RAG).

## Features

- **Web Scraping**: Automatically scrapes content from the Flare Developer Hub, focusing on key sections like the introduction, FTSO overview, and getting started guides.
- **Vector Storage**: Stores the scraped data in a Qdrant vector database for efficient semantic search.
- **RAG Integration**: Integrates the scraped data with the Flare AI RAG system to provide accurate answers to user queries.
- **Chat Interface**: Provides a user-friendly chat interface for interacting with the system.

## Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/flare-foundation/flare-ai-rag.git
   cd flare-ai-rag
   ```

2. **Set Up Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

3. **Configure API Keys**:
   - Copy `.env.example` to `.env`
   - Add your Gemini API key to the `.env` file

4. **Install Additional Dependencies**:
   ```bash
   pip install requests beautifulsoup4 python-dotenv
   ```

## Usage

### Option 1: Run the Fix Script (Recommended)

This script will fix all issues, scrape the Flare Developer Hub, and start the application:

```bash
./fix_rag_system.sh
```

### Option 2: Run Components Individually

1. **Scrape the Flare Developer Hub**:
   ```bash
   ./flare_scraper.py
   ```

2. **Verify the Data**:
   ```bash
   ./verify_data.py
   ```

3. **Start the Application**:
   ```bash
   ./run_enhanced_app.sh
   ```

## Testing

Once the application is running, you can access the chat interface at:
- Frontend: http://localhost:3001
- Backend API: http://localhost:8081

Try asking questions like:
1. "What is Flare?"
2. "How does FTSO work?"
3. "What is the Flare Time Series Oracle?"
4. "How can I participate in the Flare hackathon?"

## Troubleshooting

If you encounter issues:

1. **Check Logs**:
   ```bash
   tail -f backend.log
   tail -f scraper.log
   ```

2. **Verify Qdrant**:
   Make sure Qdrant is running:
   ```bash
   docker ps | grep qdrant
   ```
   If not running, start it:
   ```bash
   docker run -d -p 6333:6333 qdrant/qdrant
   ```

3. **Check API Key**:
   Ensure your Gemini API key is valid and has quota available.

4. **Reset the System**:
   If all else fails, run the fix script again:
   ```bash
   ./fix_rag_system.sh
   ```

## Architecture

- **flare_scraper.py**: Handles web scraping, document processing, and vector storage.
- **verify_data.py**: Verifies that the data is properly indexed and can be retrieved.
- **run_enhanced_app.sh**: Starts the application with the enhanced data.
- **fix_rag_system.sh**: Fixes all issues and ensures the system is working properly.

## Data Sources

The system scrapes the following URLs from the Flare Developer Hub:
- https://dev.flare.network/intro/ (Introduction to Flare)
- https://dev.flare.network/ftso/overview/ (FTSO Overview)
- https://dev.flare.network/hackathon/onboarding/ (Hackathon Onboarding)
- https://dev.flare.network/hackathon/cookbook/ (Hackathon Cookbook)

Additional URLs are discovered and crawled during the scraping process.

## License

This project is based on the [Flare AI RAG template](https://github.com/flare-foundation/flare-ai-rag) and is subject to its license terms.

# Flare AI RAG - Issues and Fixes

This document outlines the issues identified in the Flare AI RAG project and provides solutions to fix them.

## Identified Issues

1. **Import Error**: The main application fails to start due to a missing `PromptTemplate` class.
2. **Multiple Environment Files**: The project has multiple `.env` files causing confusion.
3. **Qdrant Integration**: Issues with connecting to Qdrant and processing data.
4. **Disorganized Scripts**: Multiple runner scripts with overlapping functionality.
5. **Bloatware Files**: Several unnecessary files that complicate the project.

## Solutions Implemented

1. **Fixed Import Error**: Added `PromptTemplate` class to the templates.py file and updated the __init__.py file to export it.
2. **Environment File Consolidation**: We'll consolidate the environment files into a single, well-documented .env file.
3. **Qdrant Integration**: The Qdrant collection creation code appears to be functional but might need testing.

## Project Structure

The project follows this structure:

```
flare-ai-rag/
├── src/
│   ├── flare_ai_rag/         # Core RAG implementation
│   │   ├── ai/              # AI provider interfaces
│   │   ├── api/             # API endpoints
│   │   ├── attestation/     # TEE attestation
│   │   ├── prompts/         # Prompt templates
│   │   ├── responder/       # Response generation
│   │   ├── retriever/       # Qdrant integration
│   │   ├── router/          # Query routing
│   │   └── utils/           # Utility functions
│   └── data/                # Training data
├── chat-ui/                 # React-based frontend
├── tests/                   # Test suite
├── .env                     # Main environment file
└── run_app.sh               # Main runner script
```

## How to Use

1. Set up your environment:
   ```bash
   # Copy example env and add your API key
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

2. Install dependencies:
   ```bash
   uv sync --all-extras
   ```

3. Start Qdrant:
   ```bash
   docker run -d -p 6333:6333 qdrant/qdrant
   ```

4. Run the application:
   ```bash
   bash run_app.sh
   ```

## Files That Can Be Removed

These files are redundant and can be safely removed:

1. `.env.enhanced` - Use .env instead
2. `.env.custom` - Use .env instead
3. `.env.data_expansion` - Use .env instead
4. `run_enhanced_app.sh` - Use run_app.sh instead
5. `fix_rag_system.sh` - Use run_app.sh instead
6. `run_with_expansion.sh` - Use run_app.sh instead
7. `restart_app.sh` - Use run_app.sh instead

## Critical Files to Keep

These files are essential for the project:

1. `flare_scraper.py` - Used for scraping and indexing content
2. `src/flare_ai_rag/main.py` - Core application
3. `chat-ui/` - Frontend interface
4. `.env` - Configuration
5. `Dockerfile` - Docker configuration
6. `nginx.conf` - Web server configuration
7. `supervisord.conf` - Process management 