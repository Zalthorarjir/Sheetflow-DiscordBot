import discord
from discord import app_commands
import sqlite3

def setup(bot):
    @bot.tree.command(name="set_channel", description="Set the channel for notifications")
    @app_commands.default_permissions(administrator=True)
    async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
        if interaction.channel.type == discord.ChannelType.private:
            await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        channel_id = channel.id
        set_guild_config(guild_id, channel_id=channel_id)

        await interaction.response.send_message(f"Channel for notifications set to {channel.mention}.", ephemeral=True)

def set_guild_config(guild_id: int, channel_id: int = None, update_channel_id: int = None):
    db_file = f'databases/{guild_id}.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    c.execute(''' 
    INSERT INTO guild_config (guild_id, channel_id, update_channel_id) 
    VALUES (?, ?, ?) 
    ON CONFLICT(guild_id) DO UPDATE SET 
        channel_id = COALESCE(?, channel_id),
        update_channel_id = COALESCE(?, update_channel_id)
    ''', (guild_id, channel_id, update_channel_id, channel_id, update_channel_id))

    conn.commit()
    conn.close()
