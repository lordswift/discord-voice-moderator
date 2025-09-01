# 🚀 Quick Start Guide

## 1. Create Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create new application → Bot → Copy token
3. Invite bot with `Mute Members` permission

## 2. Setup Bot
```bash
# Windows
setup_venv.bat

# Linux/Mac
./setup_venv.sh
```

## 3. Configure
```bash
# Copy environment template
copy env_example.txt .env  # Windows
cp env_example.txt .env    # Linux/Mac

# Edit .env file and add your bot token
DISCORD_BOT_TOKEN=your_bot_token_here
```

## 4. Run Bot
```bash
# Windows
run_bot.bat

# Linux/Mac
./run_bot.sh
```

## 5. Use Commands
- `/muteall` - Mute everyone in your voice channel
- `/unmuteall` - Unmute everyone in your voice channel
- `/unmuteundeafenall` - Unmute and undeafen everyone in your voice channel
- `/mute @user` - Mute specific user
- `/unmute @user` - Unmute specific user
- `/help` - Show all commands

Extended commands:
- `/deafenall`, `/undeafenall`
- `/mutedeafenall`, `/muteundeafenall`
- `/unmuteundeafenall`, `/unmutedeafenall`

Per-user variants (use `@user`):
- `/deafen @user`, `/undeafen @user`
- `/mutedeafen @user`, `/muteundeafen @user`
- `/unmuteundeafen @user`, `/unmutedeafen @user`

Examples:
```
# Mute everyone during gameplay
/muteall

# Unmute and undeafen after the round
/unmuteundeafenall

# Mute and deafen a player
/mutedeafen @player
```

## 🎮 Perfect for:
- **Among Us**: Mute during gameplay, unmute between rounds
- **Deceit**: Mute when using in-game voice
- **Any team game**: Quick voice control

## ⚠️ Requirements:
- You must be in a voice channel
- You need "Mute Members" permission
- Bot needs "Mute Members" permission

Note: Legacy prefix commands are supported. You can use `!` as an alternative to slash commands (for example `!muteall` behaves the same as `/muteall`).

Full command list (slash and `!` prefix):

Channel-wide:
- `/muteall` or `!muteall`
- `/unmuteall` or `!unmuteall`
- `/deafenall` or `!deafenall`
- `/undeafenall` or `!undeafenall`
- `/mutedeafenall` or `!mutedeafenall`
- `/muteundeafenall` or `!muteundeafenall`
- `/unmuteundeafenall` or `!unmuteundeafenall`
- `/unmutedeafenall` or `!unmutedeafenall`

Per-user:
- `/mute @user` or `!mute @user`
- `/unmute @user` or `!unmute @user`
- `/deafen @user` or `!deafen @user`
- `/undeafen @user` or `!undeafen @user`
- `/mutedeafen @user` or `!mutedeafen @user`
- `/muteundeafen @user` or `!muteundeafen @user`
- `/unmuteundeafen @user` or `!unmuteundeafen @user`
- `/unmutedeafen @user` or `!unmutedeafen @user`

That's it! Your bot is ready to help manage voice channels during gaming sessions! 🎮
