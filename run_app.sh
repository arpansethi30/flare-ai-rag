#!/bin/bash

# Flare AI RAG Application Runner
# This script sets up and runs both the backend and frontend of the Flare AI RAG application

echo "🔄 Starting Flare AI RAG application..."
echo "======================================="

# Configuration
BACKEND_PORT=${BACKEND_PORT:-8080}
FRONTEND_PORT=${FRONTEND_PORT:-3000}
QDRANT_PORT=6333

echo "📋 Using ports: Backend=$BACKEND_PORT, Frontend=$FRONTEND_PORT"

# Activate virtual environment
echo "📋 Activating virtual environment..."
if [ -d ".venv" ]; then
  source .venv/bin/activate
  echo "✅ Virtual environment activated"
elif [ -d "venv" ]; then
  source venv/bin/activate
  echo "✅ Virtual environment activated"
else
  echo "⚠️ No virtual environment found. Creating one..."
  python -m venv .venv
  source .venv/bin/activate
  
  # Install dependencies
  echo "📋 Installing dependencies..."
  pip install -U pip
  pip install -e .
  echo "✅ Dependencies installed"
fi

# Verify Python environment
echo "📋 Verifying Python environment..."
python -c "import sys; print(f'Python version: {sys.version}')"

# Kill any existing processes
echo "📋 Stopping existing processes..."
pkill -f "python -m flare_ai_rag.main" || true
pkill -f "npm start" || true
sleep 2

# Create or update .env file if needed
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    echo "⚠️ No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "⚠️ Please edit .env and add your GEMINI_API_KEY"
    exit 1
  else
    echo "❌ ERROR: No .env or .env.example found!"
    exit 1
  fi
fi

# Check if the .env file has a working API key
if grep -q "YOUR_API_KEY" .env; then
  echo "❌ ERROR: You need to update the API key in .env file."
  echo "   Please visit https://aistudio.google.com/app/apikey to get a new key"
  echo "   Then update the .env file with your new API key"
  exit 1
fi

# Start Qdrant if not running
echo "📋 Checking if Qdrant is running..."
if ! docker ps | grep -q qdrant; then
  echo "🚀 Starting Qdrant container..."
  docker run -d -p $QDRANT_PORT:6333 qdrant/qdrant
  sleep 5
  echo "✅ Qdrant started on port $QDRANT_PORT"
else
  echo "✅ Qdrant is already running"
fi

# Make sure ports are free
echo "📋 Checking if port $BACKEND_PORT is free..."
if lsof -i :$BACKEND_PORT > /dev/null 2>&1; then
  echo "❌ ERROR: Port $BACKEND_PORT is already in use. Please free up this port and try again."
  exit 1
fi

echo "📋 Checking if port $FRONTEND_PORT is free..."
if lsof -i :$FRONTEND_PORT > /dev/null 2>&1; then
  echo "❌ ERROR: Port $FRONTEND_PORT is already in use. Please free up this port and try again."
  exit 1
fi

# Check if data exists and needs to be scraped
DOCS_PATH="src/data/docs.csv"
if [ ! -f "$DOCS_PATH" ] || [ ! -s "$DOCS_PATH" ]; then
  echo "📋 No data found. Running data scraper..."
  python flare_scraper.py
  
  # Check if scraper was successful
  if [ $? -ne 0 ]; then
    echo "❌ Data scraper failed."
    exit 1
  fi
fi

# Update frontend config to use the correct port
echo "📋 Updating frontend configuration..."
FRONTEND_CONFIG="chat-ui/src/App.js"

if [ -f "$FRONTEND_CONFIG" ]; then
  # Backup the original App.js
  cp $FRONTEND_CONFIG ${FRONTEND_CONFIG}.bak
  
  # Update the backend URL
  sed -i.bak "s|const BACKEND_ROUTE = .*;|const BACKEND_ROUTE = \"http://localhost:${BACKEND_PORT}/api/routes/chat/\";|" $FRONTEND_CONFIG
  echo "✅ Frontend configured to use backend on port $BACKEND_PORT"
fi

# Start backend
echo "🚀 Starting backend service on port $BACKEND_PORT..."
PORT=$BACKEND_PORT python -m flare_ai_rag.main > backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started with PID $BACKEND_PID"
echo "📋 Backend logs will be saved to backend.log"

# Wait for backend to initialize
echo "⏳ Waiting for backend to initialize..."
sleep 10

# Start frontend
echo "🚀 Starting frontend service on port $FRONTEND_PORT..."
cd chat-ui && PORT=$FRONTEND_PORT npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started with PID $FRONTEND_PID"
echo "📋 Frontend logs will be saved to frontend.log"
cd ..

# Final instructions
echo ""
echo "✅ Application started successfully!"
echo "📌 Access the frontend at: http://localhost:$FRONTEND_PORT"
echo "📌 Backend API is running at: http://localhost:$BACKEND_PORT"
echo ""
echo "📋 To view backend logs: tail -f backend.log"
echo "📋 To view frontend logs: tail -f frontend.log"
echo ""
echo "🔍 Try asking these questions to test the system:"
echo "   1. \"What is Flare Network?\""
echo "   2. \"How do FTSO work?\""
echo "   3. \"Tell me about Flare's approach to data oracle services\""
echo ""
echo "⚠️  If you encounter any issues:"
echo "   1. Check the logs for errors"
echo "   2. Ensure your Gemini API key is valid and has quota available"
echo "   3. Check if Qdrant is running: docker ps | grep qdrant"
echo "" 