import discord
from discord import app_commands
import sqlite3
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def get_guild_config(guild_id):
    db_file = f'databases/{guild_id}.db'
    if not os.path.exists(db_file):
        return None
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('SELECT update_channel_id FROM guild_config WHERE guild_id = ?', (guild_id,))
    config = c.fetchone()
    conn.close()
    return config

async def not_in_dms(interaction: discord.Interaction):
    if interaction.guild is None:
        raise app_commands.CheckFailure("This command cannot be used in DMs.")
    return True

def setup(bot):
    @bot.tree.command(name="update", description="Update a character request by UID")
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(not_in_dms)
    async def update_request_command(
        interaction: discord.Interaction, 
        uid: str,
        action: str,
        note: str = ""
    ):
        guild_id = interaction.guild.id
        db_file = f'databases/{guild_id}.db'
        
        if not os.path.exists(db_file):
            await interaction.response.send_message("Guild configuration not found. Please ask an admin to run /setup guild first.", ephemeral=True)
            return
        
        try:
            conn = sqlite3.connect(db_file)
            c = conn.cursor()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

            c.execute('SELECT uid, status FROM characters WHERE uid = ?', (uid,))
            result = c.fetchone()
            if not result:
                await interaction.response.send_message("Character request not found for this UID.", ephemeral=True)
                return

            request_id, current_status = result

            status_map = {
                "approve": "Approved",
                "deny": "Denied",
                "discuss": "Under Discussion"
            }

            status = status_map.get(action.lower())
            if not status:
                await interaction.response.send_message("Invalid action. Use 'approve', 'deny', or 'discuss'.", ephemeral=True)
                return

            admin_note = note if note else ""

            c.execute('UPDATE characters SET admin_note = ?, status = ?, last_updated = ? WHERE uid = ?',
                      (admin_note, status, current_time, request_id))
            conn.commit()

            config = get_guild_config(guild_id)
            if config is None:
                await interaction.response.send_message("Guild configuration not found. Please ensure it's set up.", ephemeral=True)
                return
            
            # Convert update_channel_id to integer if possible
            try:
                update_channel_id = int(config[0])
            except (TypeError, ValueError):
                await interaction.response.send_message("Configured channel ID is invalid. Please contact an admin.", ephemeral=True)
                return

            update_channel = bot.get_channel(update_channel_id)
            if update_channel is None:
                await interaction.response.send_message("Update channel not found. Please check the channel ID.", ephemeral=True)
                return

            if not update_channel.permissions_for(interaction.guild.me).send_messages:
                await interaction.response.send_message("Bot does not have permission to send messages in the update channel.", ephemeral=True)
                return

            await update_channel.send(f"Character request with UID '{uid}' has been {status.lower()}.")
            await interaction.response.send_message(f"Character request with UID '{uid}' {status.lower()}!", ephemeral=True)

        except sqlite3.Error as e:
            logging.error(f"SQLite error: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
        except discord.errors.HTTPException as e:
            logging.error(f"Discord HTTP error: {e}")
            if e.code == 50035:  # Unknown Integration error code
                await interaction.response.send_message("Unknown Integration. Please ensure the bot is added to the guild and has the necessary permissions.", ephemeral=True)
            else:
                await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
        finally:
            conn.close()

    @update_request_command.autocomplete('action')
    async def action_autocomplete(
        interaction: discord.Interaction, 
        current: str
    ):
        choices = [
            app_commands.Choice(name="Approve", value="approve"),
            app_commands.Choice(name="Deny", value="deny"),
            app_commands.Choice(name="Discuss", value="discuss")
        ]
        return [choice for choice in choices if current.lower() in choice.name.lower()]

    @update_request_command.error
    async def update_request_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
        elif isinstance(error, app_commands.MissingRequiredArgument):
            await interaction.response.send_message("UID is a mandatory input.", ephemeral=True)
