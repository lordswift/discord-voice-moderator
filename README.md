# 🎮 Discord Voice Mute Manager Bot

A Discord bot designed to help manage voice channels during gaming sessions, particularly useful for games like Among Us, Deceit, and other team-based games where voice communication needs to be controlled.

## 🎯 Use Cases

### Primary Use Cases
- **Among Us**: Mute everyone during gameplay, unmute between rounds for strategy discussion
- **Deceit**: Mute team members when using in-game voice chat to avoid confusion
- **Team-based games**: Quick mute/unmute functionality for better communication control
- **Any multiplayer game**: Manage voice channels efficiently during different game phases

### Why This Bot?
- **Quick Commands**: Instantly mute/unmute all members in your voice channel
- **Permission Aware**: Only works if you have proper permissions
- **Voice Channel Specific**: Only affects members in the same voice channel as the command user
- **Individual Control**: Mute/unmute specific users when needed
- **Gaming Focused**: Designed specifically for gaming scenarios

## 🚀 Features

### Core Commands
- `/muteall` - Mute all members in your voice channel
- `/unmuteall` - Unmute all members in your voice channel
- `/unmuteundeafenall` - Unmute and undeafen all members in your voice channel
- `/mute <user>` - Mute a specific user in your voice channel
- `/unmute <user>` - Unmute a specific user in your voice channel
- `/help` - Show available commands and usage information

### Full Command Reference
The bot supports channel-wide and per-user voice state commands. For each action below there is a channel-wide command (applies to everyone in your voice channel) and a per-user command (target a single member).

Channel-wide commands:
- `/muteall` — mute everyone in your current voice channel
- `/unmuteall` — unmute everyone in your current voice channel
- `/deafenall` — deafen everyone in your current voice channel
- `/undeafenall` — undeafen everyone in your current voice channel
- `/mutedeafenall` — mute and deafen everyone
- `/muteundeafenall` — mute and undeafen everyone
- `/unmuteundeafenall` — unmute and undeafen everyone
- `/unmutedeafenall` — unmute and then deafen everyone

Per-user commands (use `@user` to mention target):
- `/mute @user` — mute the target
- `/unmute @user` — unmute the target
- `/deafen @user` — deafen the target
- `/undeafen @user` — undeafen the target
- `/mutedeafen @user` — mute and deafen the target
- `/muteundeafen @user` — mute and undeafen the target
- `/unmuteundeafen @user` — unmute and undeafen the target
- `/unmutedeafen @user` — unmute and then deafen the target

Examples:
1. Mute everyone during gameplay:
```
/muteall
```
2. Unmute and undeafen after a round:
```
/unmuteundeafenall
```
3. Mute and deafen a specific user:
```
/mutedeafen @troublesomePlayer
```
4. Unmute a user but keep them deafened:
```
/unmutedeafen @spectator
```

### Key Features
- ✅ **Permission Checks**: Ensures users have proper permissions before executing commands
- ✅ **Voice Channel Validation**: Commands only work when you're in a voice channel
- ✅ **Error Handling**: Comprehensive error handling with user-friendly messages
- ✅ **Logging**: Optional action logging for moderation purposes
- ✅ **Configurable**: Fully customizable through configuration files
- ✅ **Slash Commands**: Modern Discord slash command interface

## 📋 Requirements

### System Requirements
- Python 3.8 or higher
- Discord Bot Token
- Bot with proper permissions in your Discord server

### Bot Permissions Required
- `Mute Members` - To mute/unmute users
- `Send Messages` - To send command responses
- `Use Slash Commands` - To use slash command interface

### User Permissions Required
- `Mute Members` - Users must have this permission to use the bot commands

## 🛠️ Setup Instructions

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Add Bot"
5. Copy the bot token (keep this secret!)
6. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent (if needed)

### 2. Invite Bot to Server

1. Go to "OAuth2" > "URL Generator"
2. Select scopes: `bot` and `applications.commands`
3. Select bot permissions: `Mute Members`, `Send Messages`, `Use Slash Commands`
4. Copy the generated URL and open it to invite the bot

### 3. Install and Configure

#### Option A: Automated Setup (Recommended)

**For Windows:**
```bash
# Run the setup script
setup_venv.bat

# Copy environment template
copy env_example.txt .env

# Edit .env file and add your bot token
# DISCORD_BOT_TOKEN=your_bot_token_here
```

**For Linux/Mac:**
```bash
# Make scripts executable
chmod +x setup_venv.sh run_bot.sh

# Run the setup script
./setup_venv.sh

# Copy environment template
cp env_example.txt .env

# Edit .env file and add your bot token
# DISCORD_BOT_TOKEN=your_bot_token_here
```

#### Option B: Manual Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp env_example.txt .env
# Edit .env and add your bot token
```

### 4. Run the Bot

**Windows:**
```bash
run_bot.bat
```

**Linux/Mac:**
```bash
./run_bot.sh
```

**Manual:**
```bash
# Activate virtual environment first
python src/voice_mute_bot.py
```

## ⚙️ Configuration

The bot is fully configurable through `config/bot_config.json`:

### Bot Settings
```json
{
    "bot_settings": {
        "command_prefix": "!",
        "description": "Voice Channel Mute Manager Bot",
        "activity_type": "playing",
        "activity_name": "with voice channels"
    }
}
```

### Messages
Customize all bot messages:
```json
{
    "messages": {
        "mute_all_success": "🔇 Muted all members in voice channel",
        "unmute_all_success": "🔊 Unmuted all members in voice channel",
        "no_voice_channel": "❌ You must be in a voice channel to use this command",
        "no_permission": "❌ You don't have permission to mute/unmute members"
    }
}
```

### Features
Enable/disable features:
```json
{
    "features": {
        "allow_self_mute": true,
        "log_actions": true,
        "auto_unmute_on_leave": false
    }
}
```

## 🎮 Usage Examples

### Among Us Session
```
1. Everyone joins voice channel
2. During game: /muteall
3. Between rounds: /unmuteall
4. Repeat as needed
```

### Deceit Game
```
1. Team members in voice channel
2. When using in-game voice: /muteall
3. When back to Discord: /unmuteall
4. Individual control: /mute @player or /unmute @player
```

### General Gaming
```
- Quick mute during intense moments: /muteall
- Unmute for strategy discussion: /unmuteall
- Mute specific disruptive player: /mute @username
- Unmute when they're ready: /unmute @username
```

## 🔧 Troubleshooting

### Common Issues

**Bot doesn't respond to commands:**
- Check if bot is online
- Verify bot has proper permissions
- Ensure slash commands are synced (restart bot)

**"You don't have permission" error:**
- User needs "Mute Members" permission
- Check role hierarchy and permissions

**"Bot doesn't have permission" error:**
- Bot needs "Mute Members" permission
- Re-invite bot with proper permissions

**Commands not showing up:**
- Slash commands may take up to 1 hour to sync globally
- Try restarting the bot
- Check bot is in the server

## 🧭 Command Styles

This bot supports both modern Discord slash commands and legacy prefix text commands. If your server or workflow prefers the classic prefix style you can use `!` commands as aliases for the slash commands. Example: `!muteall` behaves the same as `/muteall`.

All supported commands (both slash and `!` prefix):

Channel-wide commands:
- `/muteall` or `!muteall` — mute everyone in your current voice channel
- `/unmuteall` or `!unmuteall` — unmute everyone in your current voice channel
- `/deafenall` or `!deafenall` — deafen everyone in your current voice channel
- `/undeafenall` or `!undeafenall` — undeafen everyone in your current voice channel
- `/mutedeafenall` or `!mutedeafenall` — mute and deafen everyone
- `/muteundeafenall` or `!muteundeafenall` — mute and undeafen everyone
- `/unmuteundeafenall` or `!unmuteundeafenall` — unmute and undeafen everyone
- `/unmutedeafenall` or `!unmutedeafenall` — unmute and then deafen everyone

Per-user commands (use `@user` to mention target):
- `/mute @user` or `!mute @user` — mute the target
- `/unmute @user` or `!unmute @user` — unmute the target
- `/deafen @user` or `!deafen @user` — deafen the target
- `/undeafen @user` or `!undeafen @user` — undeafen the target
- `/mutedeafen @user` or `!mutedeafen @user` — mute and deafen the target
- `/muteundeafen @user` or `!muteundeafen @user` — mute and undeafen the target
- `/unmuteundeafen @user` or `!unmuteundeafen @user` — unmute and undeafen the target
- `/unmutedeafen @user` or `!unmutedeafen @user` — unmute and then deafen the target

### Logs
The bot logs important events. Check console output for:
- Command usage
- Permission errors
- Connection status
- Error details

## 📁 Project Structure

```
DiscordBot/
├── src/
│   └── voice_mute_bot.py      # Main bot file
├── config/
│   └── bot_config.json        # Configuration file
├── requirements.txt           # Python dependencies
├── env_example.txt           # Environment variables template
├── setup_venv.sh/.bat        # Setup scripts
├── run_bot.sh/.bat           # Run scripts
└── README.md                 # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

If you encounter any issues:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Ensure all requirements are met
4. Create an issue with detailed information

## 🎯 Future Features

Potential enhancements:
- [ ] Auto-unmute when leaving voice channel
- [ ] Mute duration timers
- [ ] Role-based command restrictions
- [ ] Voice channel statistics
- [ ] Integration with game APIs
- [ ] Web dashboard for management

---

**Happy Gaming! 🎮**

*Perfect for maintaining clear communication during intense gaming sessions.*
