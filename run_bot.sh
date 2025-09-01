#!/bin/bash

# Discord Bot Run Script
# This script activates the virtual environment and runs the bot

echo "🎮 Starting Discord Voice Mute Bot..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup_venv.sh first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please copy env_example.txt to .env and add your bot token."
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Run the bot
echo "🚀 Starting bot..."
python src/voice_mute_bot.py
