@echo off
REM Discord Bot Setup Script for Windows
REM This script sets up a virtual environment and installs dependencies

echo 🎮 Setting up Discord Voice Mute Bot...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo ✅ Python is installed

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️ Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

echo ✅ Setup complete!
echo.
echo 📋 Next steps:
echo 1. Copy env_example.txt to .env
echo 2. Add your Discord bot token to .env
echo 3. Run the bot with: run_bot.bat
echo.
echo For more information, see README.md
pause
