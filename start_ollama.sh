#!/bin/bash

# Change to the aicode directory
cd "/media/aashikant/GAME Volume/aicode"

# Start Ollama with host binding
export OLLAMA_HOST=0.0.0.0:11434

echo "Starting Ollama server on 0.0.0.0:11434 from $(pwd)..."
ollama serve
