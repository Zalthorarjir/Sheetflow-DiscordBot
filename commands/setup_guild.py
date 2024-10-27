import discord
from discord import app_commands
import sqlite3
import os

if not os.path.exists('databases'):
    os.makedirs('databases')

def setup(bot):
    @bot.tree.command(name="setup_guild", description="Set up the guild with necessary configurations.")
    @app_commands.default_permissions(administrator=True)
    async def setup_guild(interaction: discord.Interaction, extra_fields: str = None):
        if interaction.channel.type == discord.ChannelType.private:
            await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        db_file = f'databases/{guild_id}.db'
        conn = sqlite3.connect(db_file)
        c = conn.cursor()

        c.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            guild_id INTEGER,
            member_id INTEGER,
            character_name TEXT,
            sheet_link TEXT,
            admin_note TEXT,
            status TEXT,
            last_updated TEXT
        )
        ''')

        if extra_fields:
            fields = [field.strip() for field in extra_fields.split(',')]
            if len(fields) > 15:
                await interaction.response.send_message("You can only specify a maximum of 15 extra fields.", ephemeral=True)
                return
            
            for field in fields:
                try:
                    c.execute(f"ALTER TABLE characters ADD COLUMN {field} TEXT")
                except sqlite3.OperationalError:
                    pass

        c.execute('''
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            update_channel_id INTEGER,
            extra_fields TEXT DEFAULT ''
        )
        ''')

        default_channel_id = interaction.channel.id
        extra_fields_str = extra_fields if extra_fields else ''

        c.execute('''
        INSERT OR REPLACE INTO guild_config (guild_id, channel_id, extra_fields)
        VALUES (?, ?, ?)
        ''', (guild_id, default_channel_id, extra_fields_str))

        conn.commit()
        conn.close()

        await interaction.response.send_message("Guild setup complete! Default channel configured with extra fields.", ephemeral=True)
