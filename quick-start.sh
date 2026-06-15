#!/bin/bash

# Shared Expenses App - Quick Start Script

echo "🚀 Shared Expenses App - Quick Start"
echo "===================================="
echo ""

# Check dependencies
echo "📦 Checking dependencies..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 16+"
    exit 1
fi

if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL not found. Using SQLite for development."
fi

echo "✅ Dependencies found"
echo ""

# Backend Setup
echo "🔧 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Installing Python packages..."
pip install -q -r requirements.txt

echo "✅ Backend setup complete"
cd ..
echo ""

# Frontend Setup
echo "🎨 Setting up frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node packages..."
    npm install -q
fi

echo "✅ Frontend setup complete"
cd ..
echo ""

# Create .env files if they don't exist
echo "⚙️  Configuring environment..."

if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env"
fi

if [ ! -f "frontend/.env.local" ]; then
    cp frontend/.env.example frontend/.env.local
    echo "✅ Created frontend/.env.local"
fi

echo ""
echo "===================================="
echo "✅ Setup Complete!"
echo "===================================="
echo ""
echo "To start the app:"
echo ""
echo "1. Terminal 1 - Start Backend:"
echo "   cd backend && source venv/bin/activate"
echo "   uvicorn src.index:app --reload --port 5000"
echo ""
echo "2. Terminal 2 - Start Frontend:"
echo "   cd frontend && npm run dev"
echo ""
echo "Then open: http://localhost:5173"
echo ""
echo "API Docs: http://localhost:5000/docs"
echo ""
