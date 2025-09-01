@echo off
REM Discord Bot Run Script for Windows
REM This script activates the virtual environment and runs the bot

echo 🎮 Starting Discord Voice Mute Bot...

REM Check if virtual environment exists
if not exist "venv" (
    echo ❌ Virtual environment not found. Please run setup_venv.bat first.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo ❌ .env file not found. Please copy env_example.txt to .env and add your bot token.
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Run the bot
echo 🚀 Starting bot...
python src\voice_mute_bot.py

pause
