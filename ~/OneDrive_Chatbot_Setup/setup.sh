#!/bin/bash
# DocuMind — One-Click Setup Script
# Installs dependencies, configures environment, and starts the app

set -e

PROJECT_DIR="~/OneDrive_Chatbot_Setup"
VENV_DIR="$PROJECT_DIR/.venv"

echo "╔══════════════════════════════════════════════╗"
echo "║       DocuMind — Setup & Launch Script       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION found"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip -q
pip install -r "$PROJECT_DIR/requirements.txt" -q

echo "✅ Dependencies installed"

# Setup .env if not exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo ""
    echo "⚙️  Creating .env from .env.example..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "✅ .env created — edit it to add your API keys"
    echo ""
    echo "   Required: GEMINI_API_KEY"
    echo "   Optional: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET (for OneDrive)"
    echo ""
    read -p "Press Enter to continue (or Ctrl+C to edit .env first)..."
fi

# Start the app
echo ""
echo "🚀 Starting DocuMind..."
echo ""

cd "$PROJECT_DIR"
python3 run.py
