#!/bin/bash

# AI Agent Builder - Debug Startup Script
# This script starts the backend with full logging for debugging

echo "=========================================="
echo "AI Agent Builder - Debug Mode"
echo "=========================================="
echo ""

# Check if backend is already running
if lsof -i :8001 > /dev/null 2>&1; then
    echo "⚠️  Backend is already running on port 8001"
    echo "   Kill it first with: pkill -f 'python main.py'"
    echo ""
    read -p "Kill existing process and restart? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "python main.py"
        sleep 2
    else
        exit 1
    fi
fi

# Check if Ollama is running
echo "Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running"
else
    echo "❌ Ollama is not running"
    echo "   Start it with: ollama serve"
    exit 1
fi

# Check if qwen2.5-coder:7b is available
if ollama list | grep -q "qwen2.5-coder:7b"; then
    echo "✅ Model qwen2.5-coder:7b is available"
else
    echo "❌ Model qwen2.5-coder:7b not found"
    echo "   Pull it with: ollama pull qwen2.5-coder:7b"
    exit 1
fi

# Check if PostgreSQL is running
echo "Checking PostgreSQL..."
if pg_isready -h 127.0.0.1 -p 5433 > /dev/null 2>&1; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL is not running on port 5433"
    echo "   Start it first"
    exit 1
fi

echo ""
echo "=========================================="
echo "Starting backend with full logging..."
echo "=========================================="
echo ""
echo "Logs will be saved to: backend.log"
echo "Press Ctrl+C to stop"
echo ""

cd "$(dirname "$0")/backend"
bash -c 'source venv/bin/activate && PORT=8001 python main.py 2>&1 | tee backend.log'
