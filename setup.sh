#!/usr/bin/env bash
# Quick setup script for AI-Powered Web Crawler

set -e

echo "🕷️  AI-Powered Web Crawler - Quick Setup"
echo "========================================"

# Check if virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  No virtual environment detected."
    echo "   Please activate your virtual environment first:"
    echo "   source ../venv/bin/activate"
    exit 1
fi

echo "✅ Virtual environment active: $VIRTUAL_ENV"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

if [[ $? -eq 0 ]]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Create .env file if it doesn't exist
if [[ ! -f .env ]]; then
    echo ""
    echo "📝 Creating .env configuration file..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo "   ⚠️  Please edit .env with your seed URLs and configuration"
else
    echo "✅ .env file already exists"
fi

# Test Ollama connection
echo ""
echo "🤖 Testing Ollama connection..."
OLLAMA_URL=$(grep OLLAMA_BASE_URL .env | cut -d'=' -f2)
OLLAMA_URL=${OLLAMA_URL:-http://10.0.228.180:31134}

if curl -s -f "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    echo "✅ Ollama server is accessible at $OLLAMA_URL"
else
    echo "⚠️  Cannot reach Ollama server at $OLLAMA_URL"
    echo "   You can still use the crawler with --skip-llm flag"
fi

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p obsidian_vault
echo "✅ Directories created"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📚 Next steps:"
echo "   1. Edit .env with your seed URLs:"
echo "      nano .env"
echo ""
echo "   2. Run the crawler:"
echo "      python main.py --seeds https://example.com --max-pages 10"
echo ""
echo "   3. Or with configuration from .env:"
echo "      python main.py"
echo ""
echo "   4. To skip LLM processing:"
echo "      python main.py --skip-llm"
echo ""
echo "📖 For more information, see README.md"
