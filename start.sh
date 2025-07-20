#!/bin/bash

echo "🚀 Starting Secure Login System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "⚠️  Warning: TELEGRAM_BOT_TOKEN not set"
fi

if [ -z "$ADMIN_CHAT_ID" ]; then
    echo "⚠️  Warning: ADMIN_CHAT_ID not set"
fi

# Start the application
echo "🎯 Starting application..."
python main.py
