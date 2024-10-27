import discord
from discord import app_commands
import sqlite3
import os

def setup(bot):
    @bot.tree.command(name="delete_character", description="Delete a character from the database.")
    @app_commands.describe(member="Mention the character owner", character_name="Name of the character to delete")
    async def delete_character(interaction: discord.Interaction, member: discord.Member, character_name: str):
        if interaction.channel.type == discord.ChannelType.private:
            await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id
        member_id = member.id

        if not (interaction.user.guild_permissions.administrator or user_id == member_id):
            await interaction.response.send_message("You do not have permission to delete this character.", ephemeral=True)
            return

        db_file = f'databases/{guild_id}.db'
        if not os.path.isfile(db_file):
            await interaction.response.send_message("No database found for this guild.", ephemeral=True)
            return

        conn = sqlite3.connect(db_file)
        c = conn.cursor()

        c.execute("SELECT * FROM characters WHERE member_id = ? AND character_name = ?", (member_id, character_name))
        character = c.fetchone()

        if character is None:
            await interaction.response.send_message("Character not found.", ephemeral=True)
            conn.close()
            return

        c.execute("DELETE FROM characters WHERE member_id = ? AND character_name = ?", (member_id, character_name))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Character '{character_name}' has been successfully deleted.", ephemeral=True)
