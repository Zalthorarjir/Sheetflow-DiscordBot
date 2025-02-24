import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
from datetime import datetime

async def update_character_fields(guild_id, character_name, field_name, new_value):
    db_file = f"databases/{guild_id}.db"
    if not os.path.isfile(db_file):
        return
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
        UPDATE characters
        SET {field_name} = ?, last_updated = ?
        WHERE character_name = ?
        """, (new_value, datetime.now().strftime("%Y-%m-%d %H:%M"), character_name))
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()

async def send_updated_embed(channel, character_data):
    embed = discord.Embed(title="Updated Character Sheet", color=discord.Color.blue())
    for field, value in character_data.items():
        embed.add_field(name=field.capitalize(), value=value if value else "[Pending]", inline=False)
    await channel.send(embed=embed)

async def update_field(interaction: discord.Interaction, character_name: str, field_name: str, new_value: str):
    guild_id = interaction.guild.id
    db_file = f"databases/{guild_id}.db"
    if not os.path.isfile(db_file):
        await interaction.response.send_message("Database not found. Please ask an admin to set up the database.", ephemeral=True)
        return
    config = get_guild_config(guild_id)
    if not config:
        await interaction.response.send_message("Guild configuration not found. Please ask an admin to run /setup guild first.", ephemeral=True)
        return

    non_editable_fields = ['status', 'last_updated', 'member', 'admin_note']
    is_admin = interaction.user.guild_permissions.administrator
    is_owner = await check_character_owner(guild_id, character_name, interaction.user.id)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(characters)")
        columns = [info[1] for info in cursor.fetchall()]
    except sqlite3.OperationalError:
        await interaction.response.send_message("Characters table not found. Please ask an admin to set up the database.", ephemeral=True)
        conn.close()
        return
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
    if not os.path.isfile(db_file):
        return False
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT member_id FROM characters WHERE character_name = ?", (character_name,))
    owner_id = cursor.fetchone()
    conn.close()
    return owner_id is not None and owner_id[0] == str(user_id)

def get_guild_config(guild_id):
    db_file = f"databases/{guild_id}.db"
    if not os.path.isfile(db_file):
        return None
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Ensure the guild_config table exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS guild_config (
        guild_id TEXT PRIMARY KEY,
        channel_id TEXT,
        update_channel_id TEXT,
        extra_fields TEXT DEFAULT ''
    )
    ''')

    try:
        cursor.execute("SELECT channel_id, update_channel_id, extra_fields FROM guild_config WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
    except sqlite3.OperationalError:
        result = None
    conn.close()
    return result

def setup(bot):
    field_group = app_commands.Group(name="field", description="Commands related to fields")

    @field_group.command(name="add", description="Add an extra field to the character database.")
    @app_commands.default_permissions(administrator=True)
    async def add_field_command(interaction: discord.Interaction, field_name: str):
        guild_id = interaction.guild.id
        db_file = f'databases/{guild_id}.db'

        if not os.path.isfile(db_file):
            await interaction.response.send_message("Guild configuration not found. Please ask an admin to run /setup guild first.", ephemeral=True)
            return

        conn = sqlite3.connect(db_file)
        c = conn.cursor()

        # Get current columns in the characters table
        c.execute("PRAGMA table_info(characters)")
        columns = [column[1] for column in c.fetchall()]

        if field_name in columns:
            await interaction.response.send_message(f"The field '{field_name}' already exists.", ephemeral=True)
            conn.close()
            return

        # Get the current extra fields from guild_config
        c.execute("SELECT extra_fields FROM guild_config WHERE guild_id = ?", (guild_id,))
        original_extra_fields = c.fetchone()
        
        current_extra_fields = original_extra_fields[0].split(',') if original_extra_fields and original_extra_fields[0] else []
        current_extra_fields = [field.strip() for field in current_extra_fields if field.strip()]

        # Check the total number of extra fields (current + new)
        if len(current_extra_fields) >= 15:
            await interaction.response.send_message("Cannot add more than 15 extra fields total.", ephemeral=True)
            conn.close()
            return
        
        try:
            # Proceed to add the new field
            columns.append(field_name)
            columns_definition = ', '.join(f"{col} TEXT" for col in columns)
            c.execute(f"CREATE TABLE IF NOT EXISTS new_characters ({columns_definition})")

            placeholders = ', '.join('?' for _ in columns)

            selection = ', '.join(columns[:-1]) + ', NULL AS ' + field_name
            c.execute(f"INSERT INTO new_characters ({', '.join(columns)}) SELECT {selection} FROM characters")

            c.execute("DROP TABLE characters")
            c.execute("ALTER TABLE new_characters RENAME TO characters")

            # Update the extra fields list
            current_extra_fields.append(field_name)
            new_extra_fields_str = ','.join(set(current_extra_fields))

            c.execute("UPDATE guild_config SET extra_fields = ? WHERE guild_id = ?", (new_extra_fields_str, guild_id))

            conn.commit()
            await interaction.response.send_message(f"Field '{field_name}' has been added successfully.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @field_group.command(name="remove", description="Remove an extra field from the character database.")
    @app_commands.default_permissions(administrator=True)
    async def remove_field_command(interaction: discord.Interaction, field_name: str):
        guild_id = interaction.guild.id
        db_file = f'databases/{guild_id}.db'

        if not os.path.isfile(db_file):
            await interaction.response.send_message("Guild configuration not found. Please ask an admin to run /setup guild first.", ephemeral=True)
            return

        conn = sqlite3.connect(db_file)
        c = conn.cursor()

        c.execute("PRAGMA table_info(characters)")
        columns = [column[1] for column in c.fetchall()]

        if field_name not in columns:
            await interaction.response.send_message(f"The field '{field_name}' does not exist.", ephemeral=True)
            conn.close()
            return

        try:
            columns.remove(field_name)
            columns_definition = ', '.join(f"{col} TEXT" for col in columns)
            c.execute(f"CREATE TABLE IF NOT EXISTS new_characters ({columns_definition})")

            placeholders = ', '.join('?' for _ in columns)
            c.execute(f"INSERT INTO new_characters ({', '.join(columns)}) SELECT {', '.join(columns)} FROM characters")

            c.execute("DROP TABLE characters")
            c.execute("ALTER TABLE new_characters RENAME TO characters")

            c.execute("SELECT extra_fields FROM guild_config WHERE guild_id = ?", (guild_id,))
            original_extra_fields = c.fetchone()[0]
            new_extra_fields = [f for f in original_extra_fields.split(',') if f.strip() != field_name]
            new_extra_fields_str = ','.join(new_extra_fields)

            c.execute("UPDATE guild_config SET extra_fields = ? WHERE guild_id = ?", (new_extra_fields_str, guild_id))

            conn.commit()
            await interaction.response.send_message(f"Field '{field_name}' has been removed successfully.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @field_group.command(name="update", description="Update a specific field of a character.")
    async def update_field_command(interaction: discord.Interaction, character_name: str, field_name: str, new_value: str):
        await update_field(interaction, character_name, field_name, new_value)

    if not bot.tree.get_command("field"):
        bot.tree.add_command(field_group)
