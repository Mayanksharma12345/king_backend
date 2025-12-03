#!/bin/bash
# Setup script for Medical Scribe AI

set -e

echo "Setting up Medical Scribe AI..."

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please edit .env with your Azure OpenAI credentials"
fi

# Initialize database
echo "Initializing database..."
python scripts/init_db.py

echo "Setup complete! Run 'python -m src.main' to start the server"
