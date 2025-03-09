#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${YELLOW}No Python virtual environment detected. Make sure to activate your virtual environment before running this script.${NC}"
    echo -e "Example: ${BLUE}source .venv/bin/activate${NC} or ${BLUE}conda activate your-env-name${NC}"
    exit 1
fi

# Check if required environment variables are set
if [[ -f .env ]]; then
    source .env
    echo -e "${GREEN}Loaded environment variables from .env file${NC}"
else
    echo -e "${YELLOW}No .env file found. Using environment variables from current shell.${NC}"
fi

if [[ -z "${GEMINI_API_KEY}" ]]; then
    echo -e "${RED}ERROR: GEMINI_API_KEY environment variable is not set. Please set it before running the app.${NC}"
    echo -e "You can create an API key at: ${BLUE}https://makersuite.google.com/app/apikey${NC}"
    exit 1
fi

# Function to check if a port is in use
is_port_in_use() {
    if command -v lsof > /dev/null; then
        lsof -i :$1 > /dev/null
        return $?
    else
        # Fallback to netstat if lsof is not available
        netstat -an | grep $1 > /dev/null
        return $?
    fi
}

# Check if Qdrant is running
QDRANT_PORT=6333
if ! is_port_in_use $QDRANT_PORT; then
    echo -e "${YELLOW}Qdrant is not running on port $QDRANT_PORT.${NC}"
    echo -e "Starting Qdrant with Docker..."
    
    # Check if Docker is available
    if ! command -v docker > /dev/null; then
        echo -e "${RED}ERROR: Docker is not installed or not in PATH. Please install Docker to use Qdrant.${NC}"
        exit 1
    fi
    
    # Start Qdrant with Docker
    docker run -d -p $QDRANT_PORT:$QDRANT_PORT -v $(pwd)/storage:/qdrant/storage qdrant/qdrant
    
    echo -e "${GREEN}Qdrant is now running on port $QDRANT_PORT${NC}"
else
    echo -e "${GREEN}Qdrant is already running on port $QDRANT_PORT${NC}"
fi

# Check if data directory exists
if [[ ! -d "src/data" ]]; then
    echo -e "${RED}ERROR: Data directory not found at src/data${NC}"
    exit 1
fi

# Check if docs.csv exists
if [[ ! -f "src/data/docs.csv" ]]; then
    echo -e "${RED}ERROR: docs.csv not found in data directory${NC}"
    exit 1
fi

# Start the backend
echo -e "${BLUE}Starting backend server...${NC}"
chmod +x src/start-backend
src/start-backend > backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}Backend started with PID: $BACKEND_PID${NC}"

# Wait for backend to be ready
echo -e "${BLUE}Waiting for backend to start...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0
BACKEND_URL="http://localhost:8080/api/chat/health"

while ! curl -s $BACKEND_URL > /dev/null && [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    sleep 1
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo -n "."
done

if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo -e "\n${RED}ERROR: Backend failed to start within the expected time.${NC}"
    echo -e "Please check backend.log for details"
    kill $BACKEND_PID
    exit 1
fi

echo -e "\n${GREEN}✅ Backend started successfully${NC}"

# Start the frontend
echo -e "${BLUE}Starting frontend server...${NC}"
cd chat-ui
npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend started with PID: $FRONTEND_PID${NC}"

# Wait for frontend to be ready
echo -e "${BLUE}Waiting for frontend to start...${NC}"
RETRY_COUNT=0
FRONTEND_URL="http://localhost:3000"

while ! curl -s $FRONTEND_URL > /dev/null && [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    sleep 1
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo -n "."
done

if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo -e "\n${RED}ERROR: Frontend failed to start within the expected time.${NC}"
    echo -e "Please check frontend.log for details"
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit 1
fi

echo -e "\n${GREEN}✅ Frontend started successfully${NC}"
cd ..

# Print success message
echo -e "${GREEN}🚀 Flare AI RAG is running!${NC}"
echo -e "${BLUE}📊 Backend API: ${NC}http://localhost:8080"
echo -e "${BLUE}🖥️ Frontend UI: ${NC}http://localhost:3000"
echo -e "${YELLOW}⌨️  Press Ctrl+C to stop all processes${NC}"

# Function to clean up processes on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}Services stopped${NC}"
    exit 0
}

# Register the cleanup function for when the script is interrupted
trap cleanup SIGINT SIGTERM

# Keep script running to allow easy shutdown with Ctrl+C
wait 