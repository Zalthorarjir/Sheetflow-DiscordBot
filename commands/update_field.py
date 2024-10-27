import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime

async def update_character_fields(guild_id, character_name, field_name, new_value):
    db_file = f"databases/{guild_id}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute(f"""
    UPDATE characters
    SET {field_name} = ?, last_updated = ?
    WHERE character_name = ?
    """, (new_value, datetime.now().strftime("%Y-%m-%d %H:%M"), character_name))
    conn.commit()
    conn.close()

async def send_updated_embed(channel, character_data):
    embed = discord.Embed(title="Updated Character Sheet", color=discord.Color.blue())
    for field, value in character_data.items():
        embed.add_field(name=field.capitalize(), value=value if value else "[Pending]", inline=False)
    await channel.send(embed=embed)

async def update_field(interaction: discord.Interaction, character_name: str, field_name: str, new_value: str):
    guild_id = interaction.guild.id
    db_file = f"databases/{guild_id}.db"
    config = get_guild_config(guild_id)
    if not config:
        await interaction.response.send_message("Guild configuration not found. Please run setup first.", ephemeral=True)
        return

    non_editable_fields = ['status', 'last_updated', 'member', 'admin_note']
    is_admin = interaction.user.guild_permissions.administrator
    is_owner = await check_character_owner(guild_id, character_name, interaction.user.id)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(characters)")
    columns = [info[1] for info in cursor.fetchall()]
    conn.close()

    field_name_lower = field_name.strip().lower()
    if field_name_lower not in [col.lower() for col in columns]:
        await interaction.response.send_message("This field does not exist!", ephemeral=True)
        return

    if field_name_lower in [nf.lower() for nf in non_editable_fields] and not is_admin:
        await interaction.response.send_message("You cannot edit this field!", ephemeral=True)
        return

    if is_admin and field_name_lower == 'admin_note':
        await update_character_fields(guild_id, character_name, field_name, new_value)
    elif is_owner:
        await update_character_fields(guild_id, character_name, field_name, new_value)
    else:
        await interaction.response.send_message("You cannot edit this field!", ephemeral=True)
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM characters WHERE character_name = ?", (character_name,))
    character_data = cursor.fetchone()
    conn.close()

    if character_data:
        character_dict = {columns[i]: character_data[i] for i in range(len(columns))}
        update_channel = discord.utils.get(interaction.guild.channels, name='update-channel-name')
        if update_channel:
            await send_updated_embed(update_channel, character_dict)

    await interaction.response.send_message("Field updated successfully!", ephemeral=True)

async def check_character_owner(guild_id, character_name, user_id):
    db_file = f"databases/{guild_id}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT member_id FROM characters WHERE character_name = ?", (character_name,))
    owner_id = cursor.fetchone()
    conn.close()
    return owner_id is not None and owner_id[0] == str(user_id)

def get_guild_config(guild_id):
    db_file = f"databases/{guild_id}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, update_channel_id, extra_fields FROM guild_config WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def setup(bot):
    @bot.tree.command(name="update_field", description="Update a specific field of a character.")
    async def update_field_command(interaction: discord.Interaction, character_name: str, field_name: str, new_value: str):
        await update_field(interaction, character_name, field_name, new_value)
