#!/bin/bash
# =====================================================================
# MONARCH — ONE-COMMAND PRODUCTION DEPLOYMENT SCRIPT
# Automated setup for Docker, Environment, & FastAPI Service on Linux / EC2
# =====================================================================

set -e

echo "👑 Starting Monarch One-Command Deployment..."

# 1. Check for .env file
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "⚠️ .env file not found. Copying from .env.example..."
        cp .env.example .env
        echo "⚠️ Please fill in your GROQ_API_KEY inside .env before proceeding."
    else
        echo "❌ Error: Neither .env nor .env.example found!"
        exit 1
    fi
fi

# 2. Check if Docker is installed
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "🐳 Docker & Docker Compose detected. Building and launching containers..."
    docker-compose up -d --build
    echo "✅ Monarch containers launched via Docker Compose!"
else
    echo "🐍 Docker not found. Falling back to native Python setup..."
    if ! command -v python3 &> /dev/null; then
        echo "❌ Error: python3 is not installed!"
        exit 1
    fi

    # Create virtual environment if missing
    if [ ! -d ".venv" ]; then
        echo "📦 Creating Python virtual environment..."
        python3 -m venv .venv
    fi

    echo "⚡ Activating virtualenv and installing dependencies..."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    echo "🚀 Starting Monarch API Server..."
    python main.py --serve-api &
    echo "✅ Monarch server running in background!"
fi

echo "========================================================="
echo "🎉 Monarch is LIVE!"
echo "🌐 Web Workbench: http://localhost:8000"
echo "📄 Swagger API Docs: http://localhost:8000/docs"
echo "========================================================="
