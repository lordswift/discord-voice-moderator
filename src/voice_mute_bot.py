import discord
from discord.ext import commands
import json
import os
import asyncio
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()


def persist_env_var(key: str, value: str, env_path: str = '.env'):
    """Write or update a key=value pair in the .env file (creates file if missing)."""
    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        key_eq = f"{key}="
        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(key_eq):
                lines[i] = f"{key}={value}\n"
                found = True
                break

        if not found:
            lines.append(f"{key}={value}\n")

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        logger.info(f"Persisted {key} to {env_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to persist env var {key}: {e}")
        return False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VoiceMuteBot(commands.Bot):
    def __init__(self):
        # Load configuration
        self.config = self.load_config()
        
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        
        super().__init__(
            command_prefix=self.config['bot_settings']['command_prefix'],
            description=self.config['bot_settings']['description'],
            intents=intents
        )
        
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            # Explicitly open with utf-8 encoding to avoid decoding issues on Windows
            with open('config/bot_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("Configuration file not found!")
            return self.get_default_config()
        except json.JSONDecodeError:
            logger.error("Invalid JSON in configuration file!")
            return self.get_default_config()
    
    def get_default_config(self):
        """Return default configuration if config file is missing"""
        return {
            'bot_settings': {
                'command_prefix': '!',
                'description': 'Voice Channel Mute Manager Bot',
                'activity_type': 'playing',
                'activity_name': 'with voice channels'
            },
            'messages': {
                'mute_all_success': '🔇 Muted all members in voice channel',
                'unmute_all_success': '🔊 Unmuted all members in voice channel',
                'no_voice_channel': '❌ You must be in a voice channel to use this command',
                'no_permission': '❌ You don\'t have permission to mute/unmute members',
                'bot_no_permission': '❌ Bot doesn\'t have permission to mute/unmute members',
                'error_occurred': '❌ An error occurred while processing the command'
            }
        }
    
    async def on_ready(self):
        """Event triggered when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        
        # Set bot activity
        activity_type = getattr(discord.ActivityType, 
                              self.config['bot_settings']['activity_type'], 
                              discord.ActivityType.playing)
        activity = discord.Activity(
            type=activity_type, 
            name=self.config['bot_settings']['activity_name']
        )
        await self.change_presence(activity=activity)
        
        # First try global sync (may take up to 1 hour to appear globally)
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} global command(s)")
        except Exception as e:
            logger.error(f"Failed to sync global commands: {e}")

        # If a test guild is configured (DISCORD_GUILD_ID) sync commands to that guild for immediate availability
        try:
            guild_id = os.getenv('DISCORD_GUILD_ID')
            if guild_id:
                try:
                    guild_obj = discord.Object(id=int(guild_id))
                    synced_guild = await self.tree.sync(guild=guild_obj)
                    logger.info(f"Synced {len(synced_guild)} command(s) to guild {guild_id}")
                except Exception as ge:
                    logger.error(f"Failed to sync commands to guild {guild_id}: {ge}")
        except Exception:
            # non-fatal
            pass
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(self.config['messages']['no_permission'])
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(self.config['messages']['bot_no_permission'])
        else:
            logger.error(f"Command error: {error}")
            await ctx.send(self.config['messages']['error_occurred'])

# Initialize bot
bot = VoiceMuteBot()

@bot.tree.command(name="muteall", description="Mute all members in your voice channel")
async def mute_all(interaction: discord.Interaction):
    """Mute all members in the voice channel where the command user is present"""
    try:
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                bot.config['messages']['no_voice_channel'], 
                ephemeral=True
            )
            return
        
        voice_channel = interaction.user.voice.channel
        
        # Check if user has permission to mute members
        if not interaction.user.guild_permissions.mute_members:
            await interaction.response.send_message(
                bot.config['messages']['no_permission'], 
                ephemeral=True
            )
            return
        
        # Check if bot has permission to mute members
        if not interaction.guild.me.guild_permissions.mute_members:
            await interaction.response.send_message(
                bot.config['messages']['bot_no_permission'], 
                ephemeral=True
            )
            return
        
        # Get all members in the voice channel
        members_to_mute = [member for member in voice_channel.members 
                          if not member.bot and not member.voice.mute]
        
        if not members_to_mute:
            await interaction.response.send_message(
                "🔇 All members in the voice channel are already muted!", 
                ephemeral=True
            )
            return
        
        # Mute all members
        muted_count = 0
        for member in members_to_mute:
            try:
                await member.edit(mute=True)
                muted_count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot mute {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error muting {member.display_name}: {e}")
        
        # Send success message
        success_message = f"{bot.config['messages']['mute_all_success']} ({muted_count} members)"
        await interaction.response.send_message(success_message)
        
        # Log the action
        if bot.config['features']['log_actions']:
            logger.info(f"{interaction.user.display_name} muted {muted_count} members in {voice_channel.name}")
            
    except Exception as e:
        logger.error(f"Error in mute_all command: {e}")
        await interaction.response.send_message(
            bot.config['messages']['error_occurred'], 
            ephemeral=True
        )

@bot.tree.command(name="unmuteall", description="Unmute all members in your voice channel")
async def unmute_all(interaction: discord.Interaction):
    """Unmute all members in the voice channel where the command user is present"""
    try:
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                bot.config['messages']['no_voice_channel'], 
                ephemeral=True
            )
            return
        
        voice_channel = interaction.user.voice.channel
        
        # Check if user has permission to mute members
        if not interaction.user.guild_permissions.mute_members:
            await interaction.response.send_message(
                bot.config['messages']['no_permission'], 
                ephemeral=True
            )
            return
        
        # Check if bot has permission to mute members
        if not interaction.guild.me.guild_permissions.mute_members:
            await interaction.response.send_message(
                bot.config['messages']['bot_no_permission'], 
                ephemeral=True
            )
            return
        
        # Get all members in the voice channel
        members_to_unmute = [member for member in voice_channel.members 
                            if not member.bot and member.voice.mute]
        
        if not members_to_unmute:
            await interaction.response.send_message(
                "🔊 All members in the voice channel are already unmuted!", 
                ephemeral=True
            )
            return
        
        # Unmute all members
        unmuted_count = 0
        for member in members_to_unmute:
            try:
                await member.edit(mute=False)
                unmuted_count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot unmute {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error unmuting {member.display_name}: {e}")
        
        # Send success message
        success_message = f"{bot.config['messages']['unmute_all_success']} ({unmuted_count} members)"
        await interaction.response.send_message(success_message)
        
        # Log the action
        if bot.config['features']['log_actions']:
            logger.info(f"{interaction.user.display_name} unmuted {unmuted_count} members in {voice_channel.name}")
            
    except Exception as e:
        logger.error(f"Error in unmute_all command: {e}")
        await interaction.response.send_message(
            bot.config['messages']['error_occurred'], 
            ephemeral=True
        )


@bot.tree.command(name="deafenall", description="Deafen all members in your voice channel")
async def deafen_all(interaction: discord.Interaction):
    """Deafen all members in the voice channel where the command user is present"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                bot.config['messages']['no_voice_channel'], 
                ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel

        # Check if user has permission to deafen members
        if not interaction.user.guild_permissions.deafen_members:
            await interaction.response.send_message(
                bot.config['messages']['no_permission'], 
                ephemeral=True
            )
            return

        # Check if bot has permission to deafen members
        if not interaction.guild.me.guild_permissions.deafen_members:
            await interaction.response.send_message(
                bot.config['messages']['bot_no_permission'], 
                ephemeral=True
            )
            return

        members_to_deafen = [member for member in voice_channel.members 
                             if not member.bot and not member.voice.deaf]

        if not members_to_deafen:
            await interaction.response.send_message(
                "\ud83d\udd07 All members in the voice channel are already deafened!", 
                ephemeral=True
            )
            return

        deafened_count = 0
        for member in members_to_deafen:
            try:
                await member.edit(deafen=True)
                deafened_count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot deafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error deafening {member.display_name}: {e}")

        success_message = f"{bot.config['messages'].get('deafen_all_success', '\ud83d\udd07 Deafened all members in voice channel')} ({deafened_count} members)"
        await interaction.response.send_message(success_message)

        if bot.config['features']['log_actions']:
            logger.info(f"{interaction.user.display_name} deafened {deafened_count} members in {voice_channel.name}")

    except Exception as e:
        logger.error(f"Error in deafen_all command: {e}")
        await interaction.response.send_message(
            bot.config['messages']['error_occurred'], 
            ephemeral=True
        )


@bot.tree.command(name="undeafenall", description="Undeafen all members in your voice channel")
async def undeafen_all(interaction: discord.Interaction):
    """Undeafen all members in the voice channel where the command user is present"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                bot.config['messages']['no_voice_channel'], 
                ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel

        if not interaction.user.guild_permissions.deafen_members:
            await interaction.response.send_message(
                bot.config['messages']['no_permission'], 
                ephemeral=True
            )
            return

        if not interaction.guild.me.guild_permissions.deafen_members:
            await interaction.response.send_message(
                bot.config['messages']['bot_no_permission'], 
                ephemeral=True
            )
            return

        members_to_undeafen = [member for member in voice_channel.members 
                               if not member.bot and member.voice.deaf]

        if not members_to_undeafen:
            await interaction.response.send_message(
                "\ud83d\udd0a All members in the voice channel are already undeafened!", 
                ephemeral=True
            )
            return

        undeafened_count = 0
        for member in members_to_undeafen:
            try:
                await member.edit(deafen=False)
                undeafened_count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot undeafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error undeafening {member.display_name}: {e}")

        success_message = f"{bot.config['messages'].get('undeafen_all_success', '\ud83d\udd0a Undeafen all members in voice channel')} ({undeafened_count} members)"
        await interaction.response.send_message(success_message)

        if bot.config['features']['log_actions']:
            logger.info(f"{interaction.user.display_name} undeafened {undeafened_count} members in {voice_channel.name}")

    except Exception as e:
        logger.error(f"Error in undeafen_all command: {e}")
        await interaction.response.send_message(
            bot.config['messages']['error_occurred'], 
            ephemeral=True
        )


@bot.tree.command(name="mutedeafenall", description="Mute and deafen all members in your voice channel")
async def mutedeafen_all(interaction: discord.Interaction):
    """Mute and deafen all members in the voice channel"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                bot.config['messages']['no_voice_channel'], 
                ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel

        # require both permissions
        if not (interaction.user.guild_permissions.mute_members and interaction.user.guild_permissions.deafen_members):
            await interaction.response.send_message(
                bot.config['messages']['no_permission'], 
                ephemeral=True
            )
            return

        if not (interaction.guild.me.guild_permissions.mute_members and interaction.guild.me.guild_permissions.deafen_members):
            await interaction.response.send_message(
                bot.config['messages']['bot_no_permission'], 
                ephemeral=True
            )
            return

        members = [m for m in voice_channel.members if not m.bot and (not m.voice.mute or not m.voice.deaf)]
        if not members:
            await interaction.response.send_message("\ud83d\udd07 All members already muted+deafened!", ephemeral=True)
            return

        count = 0
        for member in members:
            try:
                await member.edit(mute=True, deafen=True)
                count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot mute+deafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error muting+deafening {member.display_name}: {e}")

        msg = f"{bot.config['messages'].get('mutedeafen_all_success', '\ud83d\udd07 Muted+Deafened all members in voice channel')} ({count} members)"
        await interaction.response.send_message(msg)

        if bot.config['features']['log_actions']:
            logger.info(f"{interaction.user.display_name} muted+deafened {count} members in {voice_channel.name}")

    except Exception as e:
        logger.error(f"Error in mutedeafen_all command: {e}")
        await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)


@bot.tree.command(name="muteundeafenall", description="Mute and undeafen all members in your voice channel")
async def muteundeafen_all(interaction: discord.Interaction):
    """Mute and undeafen all members in the voice channel"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(bot.config['messages']['no_voice_channel'], ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        if not (interaction.user.guild_permissions.mute_members and interaction.user.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['no_permission'], ephemeral=True)
            return

        if not (interaction.guild.me.guild_permissions.mute_members and interaction.guild.me.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['bot_no_permission'], ephemeral=True)
            return

        members = [m for m in voice_channel.members if not m.bot and (not m.voice.mute or m.voice.deaf)]
        if not members:
            await interaction.response.send_message("\ud83d\udd07 All members already muted+undeafened!", ephemeral=True)
            return

        count = 0
        for member in members:
            try:
                await member.edit(mute=True, deafen=False)
                count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot mute+undeafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error muting+undeafening {member.display_name}: {e}")

        msg = f"{bot.config['messages'].get('muteundeafen_all_success', '\ud83d\udd07 Muted+Undeafened all members in voice channel')} ({count} members)"
        await interaction.response.send_message(msg)

        if bot.config['features']['log_actions']:
            logger.info(f"{interaction.user.display_name} muted+undeafened {count} members in {voice_channel.name}")

    except Exception as e:
        logger.error(f"Error in muteundeafen_all command: {e}")
        await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)


@bot.tree.command(name="unmuteundeafenall", description="Unmute and undeafen all members in your voice channel")
async def unmuteundeafen_all(interaction: discord.Interaction):
    """Unmute and undeafen all members in the voice channel"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(bot.config['messages']['no_voice_channel'], ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        # require both permissions
        if not (interaction.user.guild_permissions.mute_members and interaction.user.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['no_permission'], ephemeral=True)
            return

        if not (interaction.guild.me.guild_permissions.mute_members and interaction.guild.me.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['bot_no_permission'], ephemeral=True)
            return

        members = [m for m in voice_channel.members if not m.bot and (m.voice.mute or m.voice.deaf)]
        if not members:
            await interaction.response.send_message("\ud83d\udd0a All members already unmuted+undeafened!", ephemeral=True)
            return

        count = 0
        for member in members:
            try:
                await member.edit(mute=False, deafen=False)
                count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot unmute+undeafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error unmuting+undeafening {member.display_name}: {e}")

        msg = f"{bot.config['messages'].get('unmuteundeafen_all_success', '\ud83d\udd0a Unmuted+Undeafened all members in voice channel')} ({count} members)"
        await interaction.response.send_message(msg)

        if bot.config['features']['log_actions']:
            logger.info(f"{interaction.user.display_name} unmuted+undeafened {count} members in {voice_channel.name}")

    except Exception as e:
        logger.error(f"Error in unmuteundeafen_all command: {e}")
        await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)


@bot.tree.command(name="unmutedeafenall", description="Unmute and deafen all members in your voice channel")
async def unmutedeafen_all(interaction: discord.Interaction):
    """Unmute and deafen all members in the voice channel"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(bot.config['messages']['no_voice_channel'], ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        # require both permissions
        if not (interaction.user.guild_permissions.mute_members and interaction.user.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['no_permission'], ephemeral=True)
            return

        if not (interaction.guild.me.guild_permissions.mute_members and interaction.guild.me.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['bot_no_permission'], ephemeral=True)
            return

        # select members that either are muted or not deafened so the operation is meaningful
        members = [m for m in voice_channel.members if not m.bot and (m.voice.mute or not m.voice.deaf)]
        if not members:
            await interaction.response.send_message("\ud83d\udd07 All members already unmuted+deafened!", ephemeral=True)
            return

        count = 0
        for member in members:
            try:
                await member.edit(mute=False, deafen=True)
                count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot unmute+deafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error unmuting+deafening {member.display_name}: {e}")

        msg = f"{bot.config['messages'].get('unmutedeafen_all_success', '\ud83d\udd0a Unmuted+Deafened all members in voice channel')} ({count} members)"
        await interaction.response.send_message(msg)

        if bot.config['features']['log_actions']:
            logger.info(f"{interaction.user.display_name} unmuted+deafened {count} members in {voice_channel.name}")

    except Exception as e:
        logger.error(f"Error in unmutedeafen_all command: {e}")
        await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)


@bot.tree.command(name="mute", description="Mute a specific user in your voice channel")
async def mute_user(interaction: discord.Interaction, user: discord.Member):
    """Mute a specific user in the voice channel"""
    try:
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                bot.config['messages']['no_voice_channel'], 
                ephemeral=True
            )
            return
        
        voice_channel = interaction.user.voice.channel
        
        # Check if target user is in the same voice channel
        if not user.voice or user.voice.channel != voice_channel:
            await interaction.response.send_message(
                "❌ The specified user is not in your voice channel!", 
                ephemeral=True
            )
            return
        
        # Check if user has permission to mute members
        if not interaction.user.guild_permissions.mute_members:
            await interaction.response.send_message(
                bot.config['messages']['no_permission'], 
                ephemeral=True
            )
            return
        
        # Check if bot has permission to mute members
        if not interaction.guild.me.guild_permissions.mute_members:
            await interaction.response.send_message(
                bot.config['messages']['bot_no_permission'], 
                ephemeral=True
            )
            return
        
        # Check if user is already muted
        if user.voice.mute:
            await interaction.response.send_message(
                f"❌ {user.display_name} is already muted!", 
                ephemeral=True
            )
            return
        
        # Mute the user
        try:
            await user.edit(mute=True)
            success_message = f"🔇 Muted {user.display_name}"
            await interaction.response.send_message(success_message)
            
            # Log the action
            if bot.config['features']['log_actions']:
                logger.info(f"{interaction.user.display_name} muted {user.display_name} in {voice_channel.name}")
                
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ Cannot mute {user.display_name} - insufficient permissions!", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error muting {user.display_name}: {e}")
            await interaction.response.send_message(
                bot.config['messages']['error_occurred'], 
                ephemeral=True
            )
            
    except Exception as e:
        logger.error(f"Error in mute_user command: {e}")
        await interaction.response.send_message(
            bot.config['messages']['error_occurred'], 
            ephemeral=True
        )

@bot.tree.command(name="unmute", description="Unmute a specific user in your voice channel")
async def unmute_user(interaction: discord.Interaction, user: discord.Member):
    """Unmute a specific user in the voice channel"""
    try:
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                bot.config['messages']['no_voice_channel'], 
                ephemeral=True
            )
            return
        
        voice_channel = interaction.user.voice.channel
        
        # Check if target user is in the same voice channel
        if not user.voice or user.voice.channel != voice_channel:
            await interaction.response.send_message(
                "❌ The specified user is not in your voice channel!", 
                ephemeral=True
            )
            return
        
        # Check if user has permission to mute members
        if not interaction.user.guild_permissions.mute_members:
            await interaction.response.send_message(
                bot.config['messages']['no_permission'], 
                ephemeral=True
            )
            return
        
        # Check if bot has permission to mute members
        if not interaction.guild.me.guild_permissions.mute_members:
            await interaction.response.send_message(
                bot.config['messages']['bot_no_permission'], 
                ephemeral=True
            )
            return
        
        # Check if user is already unmuted
        if not user.voice.mute:
            await interaction.response.send_message(
                f"❌ {user.display_name} is not muted!", 
                ephemeral=True
            )
            return
        
        # Unmute the user
        try:
            await user.edit(mute=False)
            success_message = f"🔊 Unmuted {user.display_name}"
            await interaction.response.send_message(success_message)
            
            # Log the action
            if bot.config['features']['log_actions']:
                logger.info(f"{interaction.user.display_name} unmuted {user.display_name} in {voice_channel.name}")
                
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ Cannot unmute {user.display_name} - insufficient permissions!", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error unmuting {user.display_name}: {e}")
            await interaction.response.send_message(
                bot.config['messages']['error_occurred'], 
                ephemeral=True
            )
            
    except Exception as e:
        logger.error(f"Error in unmute_user command: {e}")
        await interaction.response.send_message(
            bot.config['messages']['error_occurred'], 
            ephemeral=True
        )


@bot.tree.command(name="deafen", description="Deafen a specific user in your voice channel")
async def deafen_user(interaction: discord.Interaction, user: discord.Member):
    """Deafen a specific user in the voice channel"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(bot.config['messages']['no_voice_channel'], ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await interaction.response.send_message("\u274c The specified user is not in your voice channel!", ephemeral=True)
            return

        if not interaction.user.guild_permissions.deafen_members:
            await interaction.response.send_message(bot.config['messages']['no_permission'], ephemeral=True)
            return

        if not interaction.guild.me.guild_permissions.deafen_members:
            await interaction.response.send_message(bot.config['messages']['bot_no_permission'], ephemeral=True)
            return

        if user.voice.deaf:
            await interaction.response.send_message(f"\u274c {user.display_name} is already deafened!", ephemeral=True)
            return

        try:
            await user.edit(deafen=True)
            await interaction.response.send_message(f"\ud83d\udd07 Deafened {user.display_name}")
            if bot.config['features']['log_actions']:
                logger.info(f"{interaction.user.display_name} deafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await interaction.response.send_message(f"\u274c Cannot deafen {user.display_name} - insufficient permissions!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error deafening {user.display_name}: {e}")
            await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)

    except Exception as e:
        logger.error(f"Error in deafen_user command: {e}")
        await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)


@bot.tree.command(name="undeafen", description="Undeafen a specific user in your voice channel")
async def undeafen_user(interaction: discord.Interaction, user: discord.Member):
    """Undeafen a specific user in the voice channel"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(bot.config['messages']['no_voice_channel'], ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await interaction.response.send_message("\u274c The specified user is not in your voice channel!", ephemeral=True)
            return

        if not interaction.user.guild_permissions.deafen_members:
            await interaction.response.send_message(bot.config['messages']['no_permission'], ephemeral=True)
            return

        if not interaction.guild.me.guild_permissions.deafen_members:
            await interaction.response.send_message(bot.config['messages']['bot_no_permission'], ephemeral=True)
            return

        if not user.voice.deaf:
            await interaction.response.send_message(f"\u274c {user.display_name} is not deafened!", ephemeral=True)
            return

        try:
            await user.edit(deafen=False)
            await interaction.response.send_message(f"\ud83d\udd0a Undeafened {user.display_name}")
            if bot.config['features']['log_actions']:
                logger.info(f"{interaction.user.display_name} undeafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await interaction.response.send_message(f"\u274c Cannot undeafen {user.display_name} - insufficient permissions!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error undeafening {user.display_name}: {e}")
            await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)

    except Exception as e:
        logger.error(f"Error in undeafen_user command: {e}")
        await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)


@bot.tree.command(name="mutedeafen", description="Mute and deafen a specific user in your voice channel")
async def mutedeafen_user(interaction: discord.Interaction, user: discord.Member):
    """Mute and deafen a specific user"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(bot.config['messages']['no_voice_channel'], ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await interaction.response.send_message("\u274c The specified user is not in your voice channel!", ephemeral=True)
            return

        if not (interaction.user.guild_permissions.mute_members and interaction.user.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['no_permission'], ephemeral=True)
            return

        if not (interaction.guild.me.guild_permissions.mute_members and interaction.guild.me.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['bot_no_permission'], ephemeral=True)
            return

        try:
            await user.edit(mute=True, deafen=True)
            await interaction.response.send_message(f"\ud83d\udd07 Muted+Deafened {user.display_name}")
            if bot.config['features']['log_actions']:
                logger.info(f"{interaction.user.display_name} muted+deafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await interaction.response.send_message(f"\u274c Cannot mute+deafen {user.display_name} - insufficient permissions!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error muting+deafening {user.display_name}: {e}")
            await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)

    except Exception as e:
        logger.error(f"Error in mutedeafen_user command: {e}")
        await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)


@bot.tree.command(name="muteundeafen", description="Mute and undeafen a specific user in your voice channel")
async def muteundeafen_user(interaction: discord.Interaction, user: discord.Member):
    """Mute and undeafen a specific user"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(bot.config['messages']['no_voice_channel'], ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await interaction.response.send_message("\u274c The specified user is not in your voice channel!", ephemeral=True)
            return

        if not (interaction.user.guild_permissions.mute_members and interaction.user.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['no_permission'], ephemeral=True)
            return

        if not (interaction.guild.me.guild_permissions.mute_members and interaction.guild.me.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['bot_no_permission'], ephemeral=True)
            return

        try:
            await user.edit(mute=True, deafen=False)
            await interaction.response.send_message(f"\ud83d\udd07 Muted+Undeafened {user.display_name}")
            if bot.config['features']['log_actions']:
                logger.info(f"{interaction.user.display_name} muted+undeafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await interaction.response.send_message(f"\u274c Cannot mute+undeafen {user.display_name} - insufficient permissions!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error muting+undeafening {user.display_name}: {e}")
            await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)

    except Exception as e:
        logger.error(f"Error in muteundeafen_user command: {e}")
        await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)


@bot.tree.command(name="unmuteundeafen", description="Unmute and undeafen a specific user in your voice channel")
async def unmuteundeafen_user(interaction: discord.Interaction, user: discord.Member):
    """Unmute and undeafen a specific user"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(bot.config['messages']['no_voice_channel'], ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await interaction.response.send_message("\u274c The specified user is not in your voice channel!", ephemeral=True)
            return

        if not (interaction.user.guild_permissions.mute_members and interaction.user.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['no_permission'], ephemeral=True)
            return

        if not (interaction.guild.me.guild_permissions.mute_members and interaction.guild.me.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['bot_no_permission'], ephemeral=True)
            return

        try:
            await user.edit(mute=False, deafen=False)
            await interaction.response.send_message(f"\ud83d\udd0a Unmuted+Undeafened {user.display_name}")
            if bot.config['features']['log_actions']:
                logger.info(f"{interaction.user.display_name} unmuted+undeafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await interaction.response.send_message(f"\u274c Cannot unmute+undeafen {user.display_name} - insufficient permissions!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error unmuting+undeafening {user.display_name}: {e}")
            await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)

    except Exception as e:
        logger.error(f"Error in unmuteundeafen_user command: {e}")
        await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)


@bot.tree.command(name="unmutedeafen", description="Unmute and deafen a specific user in your voice channel")
async def unmutedeafen_user(interaction: discord.Interaction, user: discord.Member):
    """Unmute and deafen a specific user"""
    try:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(bot.config['messages']['no_voice_channel'], ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await interaction.response.send_message("\u274c The specified user is not in your voice channel!", ephemeral=True)
            return

        if not (interaction.user.guild_permissions.mute_members and interaction.user.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['no_permission'], ephemeral=True)
            return

        if not (interaction.guild.me.guild_permissions.mute_members and interaction.guild.me.guild_permissions.deafen_members):
            await interaction.response.send_message(bot.config['messages']['bot_no_permission'], ephemeral=True)
            return

        try:
            await user.edit(mute=False, deafen=True)
            await interaction.response.send_message(f"\ud83d\udd0a Unmuted+Deafened {user.display_name}")
            if bot.config['features']['log_actions']:
                logger.info(f"{interaction.user.display_name} unmuted+deafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await interaction.response.send_message(f"\u274c Cannot unmute+deafen {user.display_name} - insufficient permissions!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error unmuting+deafening {user.display_name}: {e}")
            await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)

    except Exception as e:
        logger.error(f"Error in unmutedeafen_user command: {e}")
        await interaction.response.send_message(bot.config['messages']['error_occurred'], ephemeral=True)

@bot.tree.command(name="help", description="Show available commands and their usage")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    embed = discord.Embed(
        title="🎮 Voice Channel Mute Manager Bot",
        description="A bot designed to help manage voice channels during gaming sessions",
        color=0x00ff00
    )
    
    embed.add_field(
        name="🎯 Primary Commands",
        value=(
            "`/muteall` - Mute all members in your voice channel\n"
            "`/unmuteall` - Unmute all members in your voice channel\n"
            "`/deafenall` - Deafen all members in your voice channel\n"
            "`/undeafenall` - Undeafen all members in your voice channel\n"
            "`/mutedeafenall` - Mute and deafen all members\n"
            "`/muteundeafenall` - Mute and undeafen all members\n"
            "`/unmuteundeafenall` - Unmute and undeafen all members\n"
            "`/unmutedeafenall` - Unmute and deafen all members"
        ),
        inline=False
    )
    
    embed.add_field(
        name="👤 Individual Commands",
        value=(
            "`/mute <user>` - Mute a specific user in your voice channel\n"
            "`/unmute <user>` - Unmute a specific user in your voice channel\n"
            "`/deafen <user>` - Deafen a specific user\n"
            "`/undeafen <user>` - Undeafen a specific user\n"
            "`/mutedeafen <user>` - Mute and deafen a user\n"
            "`/muteundeafen <user>` - Mute and undeafen a user\n"
            "`/unmuteundeafen <user>` - Unmute and undeafen a user\n"
            "`/unmutedeafen <user>` - Unmute and deafen a user"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎮 Use Cases",
        value=(
            "• **Among Us**: Mute everyone during gameplay, unmute between rounds\n"
            "• **Deceit**: Mute team members when using in-game voice chat\n"
            "• **Any team game**: Quick mute/unmute for better communication control"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Requirements",
        value=(
            "• You must be in a voice channel\n"
            "• You need 'Mute Members' permission\n"
            "• Bot needs 'Mute Members' permission"
        ),
        inline=False
    )
    
    embed.set_footer(text="Perfect for gaming sessions where voice control is essential!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="sync_commands", description="(Admin) Sync application commands globally or to a guild (useful for testing)")
@discord.app_commands.checks.has_permissions(administrator=True)
@discord.app_commands.describe(guild_id="Optional guild id to sync to (for immediate registration)")
async def sync_commands(interaction: discord.Interaction, guild_id: str = None):
    """Force a command sync. If guild_id is provided, syncs to that guild immediately."""
    await interaction.response.defer(ephemeral=True)
    try:
        target_guild_id = None

        # If a guild_id param was provided, use it
        if guild_id:
            target_guild_id = int(guild_id)

        # Else, if invoked within a guild context, use that guild's id
        elif interaction.guild:
            target_guild_id = int(interaction.guild.id)

        if target_guild_id:
            guild_obj = discord.Object(id=target_guild_id)
            synced = await bot.tree.sync(guild=guild_obj)
            await interaction.followup.send(f"Synced {len(synced)} command(s) to guild {target_guild_id}")

            # Persist to .env for future runs
            try:
                persist_env_var('DISCORD_GUILD_ID', str(target_guild_id))
            except Exception:
                logger.warning("Could not persist DISCORD_GUILD_ID to .env")

            return

        # No guild target; perform global sync
        synced = await bot.tree.sync()
        await interaction.followup.send(f"Globally synced {len(synced)} command(s). Global propagation may take up to an hour.")
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")
        await interaction.followup.send(f"Failed to sync commands: {e}")

@sync_commands.error
async def sync_commands_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
    else:
        logger.error(f"Error in sync_commands command: {error}")
        await interaction.response.send_message("An error occurred while trying to sync commands.", ephemeral=True)


# ----------------------
# Legacy text (! prefix) commands
# These mirror the slash commands above so users can use the old prefix-based commands.
# ----------------------

@bot.command(name="muteall")
async def cmd_mute_all(ctx: commands.Context):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel

        if not ctx.author.guild_permissions.mute_members:
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not ctx.guild.me.guild_permissions.mute_members:
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        members_to_mute = [member for member in voice_channel.members if not member.bot and not member.voice.mute]
        if not members_to_mute:
            await ctx.send("🔇 All members in the voice channel are already muted!")
            return

        muted_count = 0
        for member in members_to_mute:
            try:
                await member.edit(mute=True)
                muted_count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot mute {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error muting {member.display_name}: {e}")

        success_message = f"{bot.config['messages']['mute_all_success']} ({muted_count} members)"
        await ctx.send(success_message)
        if bot.config.get('features', {}).get('log_actions'):
            logger.info(f"{ctx.author.display_name} muted {muted_count} members in {voice_channel.name}")
    except Exception as e:
        logger.error(f"Error in muteall (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="unmuteall")
async def cmd_unmute_all(ctx: commands.Context):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not ctx.author.guild_permissions.mute_members:
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not ctx.guild.me.guild_permissions.mute_members:
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        members_to_unmute = [member for member in voice_channel.members if not member.bot and member.voice.mute]
        if not members_to_unmute:
            await ctx.send("🔊 All members in the voice channel are already unmuted!")
            return

        unmuted_count = 0
        for member in members_to_unmute:
            try:
                await member.edit(mute=False)
                unmuted_count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot unmute {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error unmuting {member.display_name}: {e}")

        success_message = f"{bot.config['messages']['unmute_all_success']} ({unmuted_count} members)"
        await ctx.send(success_message)
        if bot.config.get('features', {}).get('log_actions'):
            logger.info(f"{ctx.author.display_name} unmuted {unmuted_count} members in {voice_channel.name}")
    except Exception as e:
        logger.error(f"Error in unmuteall (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="deafenall")
async def cmd_deafen_all(ctx: commands.Context):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not ctx.author.guild_permissions.deafen_members:
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not ctx.guild.me.guild_permissions.deafen_members:
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        members_to_deafen = [member for member in voice_channel.members if not member.bot and not member.voice.deaf]
        if not members_to_deafen:
            await ctx.send("🔇 All members in the voice channel are already deafened!")
            return

        deafened_count = 0
        for member in members_to_deafen:
            try:
                await member.edit(deafen=True)
                deafened_count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot deafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error deafening {member.display_name}: {e}")

        msg = f"{bot.config['messages'].get('deafen_all_success', '🔇 Deafened all members in voice channel')} ({deafened_count} members)"
        await ctx.send(msg)
        if bot.config.get('features', {}).get('log_actions'):
            logger.info(f"{ctx.author.display_name} deafened {deafened_count} members in {voice_channel.name}")
    except Exception as e:
        logger.error(f"Error in deafenall (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="undeafenall")
async def cmd_undeafen_all(ctx: commands.Context):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not ctx.author.guild_permissions.deafen_members:
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not ctx.guild.me.guild_permissions.deafen_members:
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        members_to_undeafen = [member for member in voice_channel.members if not member.bot and member.voice.deaf]
        if not members_to_undeafen:
            await ctx.send("🔊 All members in the voice channel are already undeafened!")
            return

        undeafened_count = 0
        for member in members_to_undeafen:
            try:
                await member.edit(deafen=False)
                undeafened_count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot undeafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error undeafening {member.display_name}: {e}")

        msg = f"{bot.config['messages'].get('undeafen_all_success', '🔊 Undeafen all members in voice channel')} ({undeafened_count} members)"
        await ctx.send(msg)
        if bot.config.get('features', {}).get('log_actions'):
            logger.info(f"{ctx.author.display_name} undeafened {undeafened_count} members in {voice_channel.name}")
    except Exception as e:
        logger.error(f"Error in undeafenall (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="mutedeafenall")
async def cmd_mutedeafen_all(ctx: commands.Context):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not (ctx.author.guild_permissions.mute_members and ctx.author.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not (ctx.guild.me.guild_permissions.mute_members and ctx.guild.me.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        members = [m for m in voice_channel.members if not m.bot and (not m.voice.mute or not m.voice.deaf)]
        if not members:
            await ctx.send("🔇 All members already muted+deafened!")
            return

        count = 0
        for member in members:
            try:
                await member.edit(mute=True, deafen=True)
                count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot mute+deafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error muting+deafening {member.display_name}: {e}")

        msg = f"{bot.config['messages'].get('mutedeafen_all_success', '🔇 Muted+Deafened all members in voice channel')} ({count} members)"
        await ctx.send(msg)
        if bot.config.get('features', {}).get('log_actions'):
            logger.info(f"{ctx.author.display_name} muted+deafened {count} members in {voice_channel.name}")
    except Exception as e:
        logger.error(f"Error in mutedeafenall (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="muteundeafenall")
async def cmd_muteundeafen_all(ctx: commands.Context):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not (ctx.author.guild_permissions.mute_members and ctx.author.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not (ctx.guild.me.guild_permissions.mute_members and ctx.guild.me.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        members = [m for m in voice_channel.members if not m.bot and (not m.voice.mute or m.voice.deaf)]
        if not members:
            await ctx.send("🔇 All members already muted+undeafened!")
            return

        count = 0
        for member in members:
            try:
                await member.edit(mute=True, deafen=False)
                count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot mute+undeafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error muting+undeafening {member.display_name}: {e}")

        msg = f"{bot.config['messages'].get('muteundeafen_all_success', '🔇 Muted+Undeafened all members in voice channel')} ({count} members)"
        await ctx.send(msg)
        if bot.config.get('features', {}).get('log_actions'):
            logger.info(f"{ctx.author.display_name} muted+undeafened {count} members in {voice_channel.name}")
    except Exception as e:
        logger.error(f"Error in muteundeafenall (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="unmuteundeafenall")
async def cmd_unmuteundeafen_all(ctx: commands.Context):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not (ctx.author.guild_permissions.mute_members and ctx.author.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not (ctx.guild.me.guild_permissions.mute_members and ctx.guild.me.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        members = [m for m in voice_channel.members if not m.bot and (m.voice.mute or m.voice.deaf)]
        if not members:
            await ctx.send("🔊 All members already unmuted+undeafened!")
            return

        count = 0
        for member in members:
            try:
                await member.edit(mute=False, deafen=False)
                count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot unmute+undeafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error unmuting+undeafening {member.display_name}: {e}")

        msg = f"{bot.config['messages'].get('unmuteundeafen_all_success', '🔊 Unmuted+Undeafened all members in voice channel')} ({count} members)"
        await ctx.send(msg)
        if bot.config.get('features', {}).get('log_actions'):
            logger.info(f"{ctx.author.display_name} unmuted+undeafened {count} members in {voice_channel.name}")
    except Exception as e:
        logger.error(f"Error in unmuteundeafenall (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="unmutedeafenall")
async def cmd_unmutedeafen_all(ctx: commands.Context):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not (ctx.author.guild_permissions.mute_members and ctx.author.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not (ctx.guild.me.guild_permissions.mute_members and ctx.guild.me.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        members = [m for m in voice_channel.members if not m.bot and (m.voice.mute or not m.voice.deaf)]
        if not members:
            await ctx.send("🔇 All members already unmuted+deafened!")
            return

        count = 0
        for member in members:
            try:
                await member.edit(mute=False, deafen=True)
                count += 1
            except discord.Forbidden:
                logger.warning(f"Cannot unmute+deafen {member.display_name} - insufficient permissions")
            except Exception as e:
                logger.error(f"Error unmuting+deafening {member.display_name}: {e}")

        msg = f"{bot.config['messages'].get('unmutedeafen_all_success', '🔊 Unmuted+Deafened all members in voice channel')} ({count} members)"
        await ctx.send(msg)
        if bot.config.get('features', {}).get('log_actions'):
            logger.info(f"{ctx.author.display_name} unmuted+deafened {count} members in {voice_channel.name}")
    except Exception as e:
        logger.error(f"Error in unmutedeafenall (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


# Individual/user text commands
@bot.command(name="mute")
async def cmd_mute_user(ctx: commands.Context, user: discord.Member):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await ctx.send("❌ The specified user is not in your voice channel!")
            return

        if not ctx.author.guild_permissions.mute_members:
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not ctx.guild.me.guild_permissions.mute_members:
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        if user.voice.mute:
            await ctx.send(f"❌ {user.display_name} is already muted!")
            return

        try:
            await user.edit(mute=True)
            await ctx.send(f"🔇 Muted {user.display_name}")
            if bot.config.get('features', {}).get('log_actions'):
                logger.info(f"{ctx.author.display_name} muted {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot mute {user.display_name} - insufficient permissions!")
        except Exception as e:
            logger.error(f"Error muting {user.display_name}: {e}")
            await ctx.send(bot.config['messages']['error_occurred'])
    except Exception as e:
        logger.error(f"Error in mute (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="unmute")
async def cmd_unmute_user(ctx: commands.Context, user: discord.Member):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await ctx.send("❌ The specified user is not in your voice channel!")
            return

        if not ctx.author.guild_permissions.mute_members:
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not ctx.guild.me.guild_permissions.mute_members:
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        if not user.voice.mute:
            await ctx.send(f"❌ {user.display_name} is not muted!")
            return

        try:
            await user.edit(mute=False)
            await ctx.send(f"🔊 Unmuted {user.display_name}")
            if bot.config.get('features', {}).get('log_actions'):
                logger.info(f"{ctx.author.display_name} unmuted {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot unmute {user.display_name} - insufficient permissions!")
        except Exception as e:
            logger.error(f"Error unmuting {user.display_name}: {e}")
            await ctx.send(bot.config['messages']['error_occurred'])
    except Exception as e:
        logger.error(f"Error in unmute (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="deafen")
async def cmd_deafen_user(ctx: commands.Context, user: discord.Member):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await ctx.send("❌ The specified user is not in your voice channel!")
            return

        if not ctx.author.guild_permissions.deafen_members:
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not ctx.guild.me.guild_permissions.deafen_members:
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        if user.voice.deaf:
            await ctx.send(f"❌ {user.display_name} is already deafened!")
            return

        try:
            await user.edit(deafen=True)
            await ctx.send(f"🔇 Deafened {user.display_name}")
            if bot.config.get('features', {}).get('log_actions'):
                logger.info(f"{ctx.author.display_name} deafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot deafen {user.display_name} - insufficient permissions!")
        except Exception as e:
            logger.error(f"Error deafening {user.display_name}: {e}")
            await ctx.send(bot.config['messages']['error_occurred'])
    except Exception as e:
        logger.error(f"Error in deafen (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="undeafen")
async def cmd_undeafen_user(ctx: commands.Context, user: discord.Member):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await ctx.send("❌ The specified user is not in your voice channel!")
            return

        if not ctx.author.guild_permissions.deafen_members:
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not ctx.guild.me.guild_permissions.deafen_members:
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        if not user.voice.deaf:
            await ctx.send(f"❌ {user.display_name} is not deafened!")
            return

        try:
            await user.edit(deafen=False)
            await ctx.send(f"🔊 Undeafened {user.display_name}")
            if bot.config.get('features', {}).get('log_actions'):
                logger.info(f"{ctx.author.display_name} undeafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot undeafen {user.display_name} - insufficient permissions!")
        except Exception as e:
            logger.error(f"Error undeafening {user.display_name}: {e}")
            await ctx.send(bot.config['messages']['error_occurred'])
    except Exception as e:
        logger.error(f"Error in undeafen (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="mutedeafen")
async def cmd_mutedeafen_user(ctx: commands.Context, user: discord.Member):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await ctx.send("❌ The specified user is not in your voice channel!")
            return

        if not (ctx.author.guild_permissions.mute_members and ctx.author.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not (ctx.guild.me.guild_permissions.mute_members and ctx.guild.me.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        try:
            await user.edit(mute=True, deafen=True)
            await ctx.send(f"🔇 Muted+Deafened {user.display_name}")
            if bot.config.get('features', {}).get('log_actions'):
                logger.info(f"{ctx.author.display_name} muted+deafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot mute+deafen {user.display_name} - insufficient permissions!")
        except Exception as e:
            logger.error(f"Error muting+deafening {user.display_name}: {e}")
            await ctx.send(bot.config['messages']['error_occurred'])
    except Exception as e:
        logger.error(f"Error in mutedeafen (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="muteundeafen")
async def cmd_muteundeafen_user(ctx: commands.Context, user: discord.Member):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await ctx.send("❌ The specified user is not in your voice channel!")
            return

        if not (ctx.author.guild_permissions.mute_members and ctx.author.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not (ctx.guild.me.guild_permissions.mute_members and ctx.guild.me.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        try:
            await user.edit(mute=True, deafen=False)
            await ctx.send(f"🔇 Muted+Undeafened {user.display_name}")
            if bot.config.get('features', {}).get('log_actions'):
                logger.info(f"{ctx.author.display_name} muted+undeafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot mute+undeafen {user.display_name} - insufficient permissions!")
        except Exception as e:
            logger.error(f"Error muting+undeafening {user.display_name}: {e}")
            await ctx.send(bot.config['messages']['error_occurred'])
    except Exception as e:
        logger.error(f"Error in muteundeafen (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="unmuteundeafen")
async def cmd_unmuteundeafen_user(ctx: commands.Context, user: discord.Member):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await ctx.send("❌ The specified user is not in your voice channel!")
            return

        if not (ctx.author.guild_permissions.mute_members and ctx.author.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not (ctx.guild.me.guild_permissions.mute_members and ctx.guild.me.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        try:
            await user.edit(mute=False, deafen=False)
            await ctx.send(f"🔊 Unmuted+Undeafened {user.display_name}")
            if bot.config.get('features', {}).get('log_actions'):
                logger.info(f"{ctx.author.display_name} unmuted+undeafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot unmute+undeafen {user.display_name} - insufficient permissions!")
        except Exception as e:
            logger.error(f"Error unmuting+undeafening {user.display_name}: {e}")
            await ctx.send(bot.config['messages']['error_occurred'])
    except Exception as e:
        logger.error(f"Error in unmuteundeafen (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])


@bot.command(name="unmutedeafen")
async def cmd_unmutedeafen_user(ctx: commands.Context, user: discord.Member):
    try:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(bot.config['messages']['no_voice_channel'])
            return

        voice_channel = ctx.author.voice.channel
        if not user.voice or user.voice.channel != voice_channel:
            await ctx.send("❌ The specified user is not in your voice channel!")
            return

        if not (ctx.author.guild_permissions.mute_members and ctx.author.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['no_permission'])
            return

        if not (ctx.guild.me.guild_permissions.mute_members and ctx.guild.me.guild_permissions.deafen_members):
            await ctx.send(bot.config['messages']['bot_no_permission'])
            return

        try:
            await user.edit(mute=False, deafen=True)
            await ctx.send(f"🔊 Unmuted+Deafened {user.display_name}")
            if bot.config.get('features', {}).get('log_actions'):
                logger.info(f"{ctx.author.display_name} unmuted+deafened {user.display_name} in {voice_channel.name}")
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot unmute+deafen {user.display_name} - insufficient permissions!")
        except Exception as e:
            logger.error(f"Error unmuting+deafening {user.display_name}: {e}")
            await ctx.send(bot.config['messages']['error_occurred'])
    except Exception as e:
        logger.error(f"Error in unmutedeafen (text) command: {e}")
        await ctx.send(bot.config['messages']['error_occurred'])

def main():
    """Main function to run the bot"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables!")
        logger.error("Please create a .env file with your bot token.")
        return
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token!")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()
