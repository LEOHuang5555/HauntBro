#!/bin/bash
set -e

# Configuration
OLLAMA_HOST="${OLLAMA_HOST:-0.0.0.0:11434}"
MAX_RETRIES=30
RETRY_DELAY=2

# Color codes for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Start Ollama server
log_info "Starting Ollama server..."
OLLAMA_HOST=0.0.0.0:11434 ollama serve &
OLLAMA_PID=$!

# Wait for Ollama server to be ready
log_info "Waiting for Ollama server to be ready..."
retry_count=0
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $MAX_RETRIES ]; then
        log_error "Ollama server failed to start after $MAX_RETRIES attempts"
        exit 1
    fi
    log_warn "Ollama not ready yet. Retrying in ${RETRY_DELAY}s... (${retry_count}/${MAX_RETRIES})"
    sleep $RETRY_DELAY
done

log_info "Ollama server is ready!"

# Define models to pull (can be overridden by environment variable)
MODELS="${OLLAMA_MODELS:-llama3.2 mistral phi3}"

# Convert models string to array
IFS=' ' read -ra MODEL_ARRAY <<< "$MODELS"

# Pull models if not already present
for MODEL in "${MODEL_ARRAY[@]}"; do
    log_info "Checking model: $MODEL"
    
    if ollama list 2>/dev/null | grep -q "^$MODEL"; then
        log_info "Model $MODEL already exists. Skipping..."
    else
        log_info "Pulling model: $MODEL"
        if ollama pull "$MODEL"; then
            log_info "Successfully pulled model: $MODEL"
        else
            log_error "Failed to pull model: $MODEL"
            # Continue with other models even if one fails
        fi
    fi
done

log_info "Model initialization complete. Keeping Ollama server running..."

# Monitor Ollama process
wait $OLLAMA_PID