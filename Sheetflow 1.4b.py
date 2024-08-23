import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import uuid
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

def init_db():
    conn = sqlite3.connect('characters.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS characters (
        id TEXT PRIMARY KEY,
        guild_id INTEGER,
        member_id INTEGER,
        character_name TEXT,
        sheet_link TEXT,
        admin_note TEXT,
        status TEXT DEFAULT 'Under Discussion',
        last_updated TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS guild_config (
        guild_id INTEGER PRIMARY KEY,
        character_channel_id INTEGER,
        update_channel_id INTEGER
    )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized.")  # Debugging line

def get_guild_config(guild_id):
    conn = sqlite3.connect('characters.db')
    c = conn.cursor()
    c.execute('SELECT character_channel_id, update_channel_id FROM guild_config WHERE guild_id = ?', (guild_id,))
    config = c.fetchone()
    conn.close()
    print(f"Retrieved config for guild {guild_id}: {config}")  # Debugging line
    return config

def set_guild_config(guild_id, character_channel_id=None, update_channel_id=None):
    conn = sqlite3.connect('characters.db')
    c = conn.cursor()
    
    # Retrieve current config
    current_config = get_guild_config(guild_id)
    current_character_channel_id = current_config[0] if current_config else None
    current_update_channel_id = current_config[1] if current_config else None
    
    # Prepare new values
    new_character_channel_id = character_channel_id if character_channel_id is not None else current_character_channel_id
    new_update_channel_id = update_channel_id if update_channel_id is not None else current_update_channel_id
    
    # Update the configuration
    c.execute('''
    INSERT INTO guild_config (guild_id, character_channel_id, update_channel_id)
    VALUES (?, ?, ?)
    ON CONFLICT(guild_id)
    DO UPDATE SET
        character_channel_id = ?,
        update_channel_id = ?
    ''', (guild_id, new_character_channel_id, new_update_channel_id, new_character_channel_id, new_update_channel_id))
    
    conn.commit()
    conn.close()
    
    print(f"Set config for guild {guild_id}: character_channel_id={new_character_channel_id}, update_channel_id={new_update_channel_id}")  # Debugging line

@bot.event
async def on_ready():
    init_db()
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

@bot.tree.command(name="new", description="Create a new character sheet entry")
async def new(interaction: discord.Interaction, character_name: str, sheet_link: str):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    config = get_guild_config(guild_id)
    
    if not config or config[0] is None:
        await interaction.followup.send("No channel set for character sheet requests. Please contact an admin.", ephemeral=True)
        return

    channel_id = config[0]
    print(f"Using channel ID {channel_id} for guild {guild_id}")  # Debugging line

    request_id = str(uuid.uuid4())

    conn = sqlite3.connect('characters.db')
    c = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute('''
    INSERT INTO characters (id, guild_id, member_id, character_name, sheet_link, admin_note, last_updated)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (request_id, guild_id, interaction.user.id, character_name, sheet_link, "", current_time))
    conn.commit()
    conn.close()

    staff_channel = bot.get_channel(channel_id)
    if not staff_channel:
        await interaction.followup.send("Configured channel not found. Please contact an admin.", ephemeral=True)
        return

    embed = discord.Embed(title="New Character Sheet Request", color=discord.Color.blue())
    embed.add_field(name="Character", value=character_name, inline=False)
    embed.add_field(name="Member", value=interaction.user.mention, inline=False)
    embed.add_field(name="Sheet Link", value=sheet_link, inline=False)
    embed.add_field(name="Admin Note", value="", inline=False)
    embed.add_field(name="Status", value="Under Discussion", inline=False)
    embed.add_field(name="Last Update", value=current_time, inline=False)
    embed.add_field(name="Request ID", value=request_id, inline=False)
    await staff_channel.send(embed=embed)
    await interaction.followup.send("Your character sheet request has been submitted.", ephemeral=True)

@bot.tree.command(name="setchannel", description="Set the channel for /new character sheet requests")
@app_commands.checks.has_permissions(administrator=True)
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild.id
    set_guild_config(guild_id, character_channel_id=channel.id)
    await interaction.response.send_message(f"Channel for /new character sheet requests set to {channel.mention}.", ephemeral=True)

@bot.tree.command(name="setupdatechannel", description="Set the channel for /update_request notifications")
@app_commands.checks.has_permissions(administrator=True)
async def set_update_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild.id
    set_guild_config(guild_id, update_channel_id=channel.id)
    await interaction.response.send_message(f"Channel for /update_request notifications set to {channel.mention}.", ephemeral=True)

@bot.tree.command(name="update_request", description="Update a character request by ID")
@app_commands.checks.has_permissions(administrator=True)
async def update_request(interaction: discord.Interaction, request_id: str, action: str, note: str = ""):
    if action.lower() not in ["approve", "deny", "discuss"]:
        await interaction.response.send_message("Invalid action. Use 'approve', 'deny', or 'discuss'.", ephemeral=True)
        return

    conn = sqlite3.connect('characters.db')
    c = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        c.execute('SELECT member_id, character_name FROM characters WHERE id = ?', (request_id,))
        result = c.fetchone()
        if not result:
            await interaction.response.send_message("Character request not found.", ephemeral=True)
            return

        member_id, character_name = result

        # Determine the status
        status_map = {
            "approve": "Approved",
            "deny": "Denied",
            "discuss": "Under Discussion"
        }
        status = status_map.get(action.lower(), "Under Discussion")

        # Create the admin note
        admin_note = f"{status}: {note}" if note else status

        # Update the database
        c.execute('UPDATE characters SET admin_note = ?, status = ?, last_updated = ? WHERE id = ?',
                  (admin_note, status, current_time, request_id))
        conn.commit()

        # Notify the user in the update channel if configured
        update_channel_id = get_guild_config(interaction.guild.id)[1]
        if update_channel_id:
            update_channel = bot.get_channel(update_channel_id)
            if update_channel:
                await update_channel.send(f"<@{member_id}> Character request for '{character_name}' has been {status.lower()}.")

        await interaction.response.send_message(f"Character request for '{character_name}' {status.lower()}!", ephemeral=True)

    except sqlite3.Error as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
    finally:
        conn.close()

import re

@bot.tree.command(name="search", description="Search approved characters by name or member mention with pagination")
async def search(interaction: discord.Interaction, query: str, page: int = 1):
    items_per_page = 1
    offset = (page - 1) * items_per_page

    # Check if query contains a user mention
    mention_match = re.match(r'<@!?(\d+)>', query)
    if mention_match:
        member_id = int(mention_match.group(1))  # Extract member ID from mention
        search_by = "member_id"
        search_query = member_id
    else:
        # Fallback to text search
        search_by = "character_name"
        search_query = f'%{query}%'  # Use wildcards for partial matching

    conn = sqlite3.connect('characters.db')
    c = conn.cursor()

    # Construct SQL query based on search type
    if search_by == "member_id":
        c.execute('''
        SELECT * FROM characters WHERE member_id = ?
        LIMIT ? OFFSET ?
        ''', (search_query, items_per_page, offset))
    else:
        c.execute('''
        SELECT * FROM characters WHERE character_name LIKE ?
        LIMIT ? OFFSET ?
        ''', (search_query, items_per_page, offset))
        
    results = c.fetchall()

    # Get total results count
    if search_by == "member_id":
        total_results_query = c.execute('SELECT COUNT(*) FROM characters WHERE member_id = ?', (search_query,))
    else:
        total_results_query = c.execute('SELECT COUNT(*) FROM characters WHERE character_name LIKE ?', (f'%{query}%',))
        
    total_results = total_results_query.fetchone()[0]
    conn.close()

    if results:
        embed = discord.Embed(title="Character Search Results", color=discord.Color.green())
        for row in results:
            character_name = row[3]
            member_id = row[2]
            sheet_link = row[4]
            admin_note = row[5]
            status = row[6]
            last_updated = row[7]
            #request_id = row[0]
            
            member_mention = f"<@{member_id}>"

            embed.add_field(name="Character", value=character_name, inline=False)
            embed.add_field(name="Member", value=member_mention, inline=False)
            embed.add_field(name="Sheet Link", value=sheet_link, inline=False)
            embed.add_field(name="Admin Note", value=admin_note, inline=False)
            embed.add_field(name="Status", value=status, inline=False)
            embed.add_field(name="Last Update", value=last_updated, inline=False)
            #embed.add_field(name="Request ID", value=request_id, inline=False)
            embed.add_field(name="\u200b", value="\u200b", inline=False)  # Blank line between results

        embed.set_footer(text=f"Page {page} of {total_results // items_per_page + (1 if total_results % items_per_page else 0)}")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("No results found.", ephemeral=True)

bot.run(TOKEN)
