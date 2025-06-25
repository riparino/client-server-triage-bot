#!/bin/bash

# Azure Sentinel Triage Bot Server Startup Script
# Use this script to start the server with proper configuration

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export FLASK_APP=app.py
export FLASK_ENV=production

# Create logs directory if it doesn't exist
mkdir -p ../logs

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check Azure CLI authentication
echo "Checking Azure CLI authentication..."
if ! az account show > /dev/null 2>&1; then
    echo "Error: Not authenticated with Azure CLI"
    echo "Please run 'az login' first"
    exit 1
fi

# Start the server
echo "Starting Azure Sentinel Triage Bot Server..."
python app.py