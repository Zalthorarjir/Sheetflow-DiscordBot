import discord
from discord import app_commands
import sqlite3
from datetime import datetime

def get_guild_config(guild_id):
    db_file = f'databases/{guild_id}.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('SELECT channel_id FROM guild_config WHERE guild_id = ?', (guild_id,))
    config = c.fetchone()
    conn.close()
    return config

async def not_in_dms(interaction: discord.Interaction):
    if interaction.guild is None:
        raise app_commands.CheckFailure("This command cannot be used in DMs.")
    return True

def setup(bot):
    @bot.tree.command(name="update_request", description="Update a character request by Member and Character")
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(not_in_dms)
    async def update_request_command(
        interaction: discord.Interaction, 
        member: discord.Member,
        character_name: str,
        action: str,
        note: str = ""
    ):
        guild_id = interaction.guild.id
        db_file = f'databases/{guild_id}.db'
        
        try:
            conn = sqlite3.connect(db_file)
            c = conn.cursor()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

            c.execute('SELECT id, status FROM characters WHERE member_id = ? AND character_name = ?',
                      (member.id, character_name))
            result = c.fetchone()
            if not result:
                await interaction.response.send_message("Character request not found for this member.", ephemeral=True)
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

            c.execute('UPDATE characters SET admin_note = ?, status = ?, last_updated = ? WHERE id = ?',
                      (admin_note, status, current_time, request_id))
            conn.commit()

            config = get_guild_config(guild_id)
            if config is None:
                await interaction.response.send_message("Guild configuration not found. Please ensure it's set up.", ephemeral=True)
                return
            
            update_channel_id = config[0]
            if update_channel_id:
                update_channel = bot.get_channel(update_channel_id)
                if update_channel:
                    await update_channel.send(f"<@{member.id}> Character request for '{character_name}' has been {status.lower()}.")

            await interaction.response.send_message(f"Character request for '{character_name}' {status.lower()}!", ephemeral=True)

        except sqlite3.Error as e:
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
