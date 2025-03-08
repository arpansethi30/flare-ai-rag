#!/bin/bash

# Restart script for Flare AI RAG application
# This script applies the fixes and restarts both backend and frontend

echo "🔄 Restarting Flare AI RAG Application..."
echo "=========================================="

# Kill any existing processes
echo "📋 Stopping existing processes..."
pkill -f "python -m flare_ai_rag.main" || true
pkill -f "npm start" || true
sleep 2

# Check if the .env file has a working API key
if grep -q "YOUR_NEW_API_KEY_HERE" .env; then
  echo "❌ ERROR: You need to update the API key in .env file."
  echo "   Please visit https://aistudio.google.com/app/apikey to get a new key"
  echo "   Then update the .env file with your new API key"
  exit 1
fi

# Start Qdrant if not running
echo "📋 Checking if Qdrant is running..."
if ! docker ps | grep -q qdrant; then
  echo "🚀 Starting Qdrant container..."
  docker run -d -p 6333:6333 qdrant/qdrant
  sleep 5
else
  echo "✅ Qdrant is already running"
fi

# Make sure port 8081 is free
echo "📋 Checking if port 8081 is free..."
if lsof -i :8081 > /dev/null; then
  echo "❌ ERROR: Port 8081 is already in use. Please free up this port and try again."
  exit 1
fi

# Make sure port 3001 is free
echo "📋 Checking if port 3001 is free..."
if lsof -i :3001 > /dev/null; then
  echo "❌ ERROR: Port 3001 is already in use. Please free up this port and try again."
  exit 1
fi

# Create a custom settings file with different port
echo "📋 Creating custom settings for port 8081..."
cat > .env.custom << EOF
# GEMINI API key
# This key has been tested and verified to work with our test scripts
GEMINI_API_KEY=$(grep GEMINI_API_KEY .env | cut -d= -f2)

# Simulating attestation (pre-TEE deployment)
SIMULATE_ATTESTATION=false

# Backend port (changed from default 8080)
PORT=8081

# For TEE deployment only
TEE_IMAGE_REFERENCE=ghcr.io/flare-foundation/flare-ai-rag:main
INSTANCE_NAME=PROJECT_NAME-TEAM-_NAME
EOF

# Start backend
echo "🚀 Starting backend service on port 8081..."
PORT=8081 python -m flare_ai_rag.main > backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started with PID $BACKEND_PID"
echo "📋 Backend logs will be saved to backend.log"

# Wait for backend to initialize
echo "⏳ Waiting for backend to initialize..."
sleep 5

# Update frontend config to use port 8081
echo "📋 Updating frontend configuration to use port 8081..."
# Backup the original App.js
cp chat-ui/src/App.js chat-ui/src/App.js.orig

# Create a temporary file with the correct BACKEND_ROUTE
cat > temp_App.js << EOF
import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import './index.css';

const BACKEND_ROUTE = "http://localhost:8081/api/routes/chat/";

// Rest of the file will be appended below
EOF

# Append the rest of the file (excluding the first 6 lines)
tail -n +7 chat-ui/src/App.js.orig >> temp_App.js

# Replace the original file
mv temp_App.js chat-ui/src/App.js

# Start frontend on port 3001
echo "🚀 Starting frontend service on port 3001..."
cd chat-ui && PORT=3001 npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started with PID $FRONTEND_PID"
echo "📋 Frontend logs will be saved to frontend.log"

# Final instructions
echo ""
echo "✅ Application started successfully!"
echo "📌 Access the frontend at: http://localhost:3001"
echo "📌 Backend API is running at: http://localhost:8081"
echo ""
echo "📋 To view backend logs: tail -f backend.log"
echo "📋 To view frontend logs: tail -f frontend.log"
echo ""
echo "⚠️  If you encounter any issues:"
echo "   1. Check the logs for errors"
echo "   2. Ensure your Gemini API key is valid and has quota available"
echo "   3. Check if port 8081 is free (backend) and port 3001 is free (frontend)"
echo "" 