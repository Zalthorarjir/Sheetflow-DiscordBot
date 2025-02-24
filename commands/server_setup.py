import discord
from discord import app_commands
import sqlite3
import os

# Ensure the 'databases' directory exists
if not os.path.exists('databases'):
    os.makedirs('databases')

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

def get_guild_config(guild_id):
    db_file = f'databases/{guild_id}.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    # Ensure the guild_config table exists
    c.execute('''
    CREATE TABLE IF NOT EXISTS guild_config (
        guild_id TEXT PRIMARY KEY,
        channel_id TEXT,
        update_channel_id TEXT,
        extra_fields TEXT DEFAULT ''
    )
    ''')

    c.execute('SELECT * FROM guild_config WHERE guild_id = ?', (guild_id,))
    config = c.fetchone()
    conn.close()
    return config

async def setup(bot):  # Changed to async
    setup_group = app_commands.Group(name="server_setup", description="Setup commands")

    @setup_group.command(name="guild", description="Set up the guild with necessary configurations.")
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
            uid TEXT PRIMARY KEY,
            guild_id TEXT,
            member_id TEXT,
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
            guild_id TEXT PRIMARY KEY,
            channel_id TEXT,
            update_channel_id TEXT,
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

    @setup_group.command(name="admin_channel", description="Set the channel for notifications")
    @app_commands.default_permissions(administrator=True)
    async def set_channel_command(interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            if interaction.channel.type == discord.ChannelType.private:
                await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
                return

            guild_id = interaction.guild.id
            db_file = f'databases/{guild_id}.db'
            if not os.path.isfile(db_file):
                await interaction.response.send_message("Database not found. Please ask an admin to set up the database.", ephemeral=True)
                return

            config = get_guild_config(guild_id)
            if config is None:
                await interaction.response.send_message("Guild configuration not found. Please ask an admin to run /setup guild first.", ephemeral=True)
                return

            set_guild_config(guild_id, channel_id=channel.id)
            await interaction.response.send_message(f"Channel for notifications set to {channel.mention}.", ephemeral=True)
        except discord.errors.NotFound:
            await interaction.followup.send("Interaction has expired or is invalid. Please try again.", ephemeral=True)

    @setup_group.command(name="member_channel", description="Set the channel for /update_request notifications")
    @app_commands.default_permissions(administrator=True)
    async def set_update_channel_command(interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            if interaction.channel.type == discord.ChannelType.private:
                await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
                return

            guild_id = interaction.guild.id
            db_file = f'databases/{guild_id}.db'
            if not os.path.isfile(db_file):
                await interaction.response.send_message("Database not found. Please ask an admin to set up the database.", ephemeral=True)
                return

            config = get_guild_config(guild_id)
            if config is None:
                await interaction.response.send_message("Guild configuration not found. Please ask an admin to run /setup guild first.", ephemeral=True)
                return

            set_guild_config(guild_id, update_channel_id=channel.id)
            await interaction.response.send_message(f"Channel for /update_request notifications set to {channel.mention}.", ephemeral=True)
        except discord.errors.NotFound:
            await interaction.followup.send("Interaction has expired or is invalid. Please try again.", ephemeral=True)

    if not bot.tree.get_command("server_setup"):
        bot.tree.add_command(setup_group)
