#!/bin/bash

# Hublink Hypervisor Startup Script
# This script starts the Hublink Hypervisor Flask application

set -e

echo "Starting Hublink.cloud™ Hypervisor..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if required files exist
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found. Please run this script from the Hublink-Hypervisor directory."
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo "Error: requirements.txt not found. Please run this script from the Hublink-Hypervisor directory."
    exit 1
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Virtual environment found. Activating..."
    source venv/bin/activate
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    echo "No virtual environment found. Using system Python..."
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
fi

# Check if dependencies are installed
echo "Checking dependencies..."
if ! $PYTHON_CMD -c "import flask, flask_cors, requests" 2>/dev/null; then
    echo "Installing dependencies..."
    $PIP_CMD install -r requirements.txt
fi

# Check if Hublink directory exists
if [ ! -d "/opt/hublink" ]; then
    echo "Warning: /opt/hublink directory not found. The application may not work correctly."
    echo "Please ensure your Hublink containers are set up in /opt/hublink"
fi

# Start the application
echo "Starting Flask application on http://localhost:8080"
echo "Press Ctrl+C to stop the application"
echo ""

$PYTHON_CMD app.py 