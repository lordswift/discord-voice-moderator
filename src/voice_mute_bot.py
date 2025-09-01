import discord
from discord.ext import commands
import json
import os
import asyncio
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

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
            with open('config/bot_config.json', 'r') as f:
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
        
        # Sync commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
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
            "`/unmuteall` - Unmute all members in your voice channel"
        ),
        inline=False
    )
    
    embed.add_field(
        name="👤 Individual Commands",
        value=(
            "`/mute <user>` - Mute a specific user in your voice channel\n"
            "`/unmute <user>` - Unmute a specific user in your voice channel"
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
