#!/bin/bash

echo "Starting Ollama server..."
ollama serve &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for Ollama to start..."
sleep 10

# Pull models
MODELS="${OLLAMA_MODELS:-llama3.2 deepseek-coder}"
for MODEL in $MODELS; do
    echo "Pulling model: $MODEL"
    ollama pull $MODEL || echo "Failed to pull $MODEL"
done

echo "Keeping server running..."
wait $SERVER_PID