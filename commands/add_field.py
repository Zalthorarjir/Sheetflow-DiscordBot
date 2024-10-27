import discord
from discord import app_commands
import sqlite3
import os

def setup(bot):
    @bot.tree.command(name="add_field", description="Add an extra field to the character database.")
    @app_commands.default_permissions(administrator=True)
    async def add_field(interaction: discord.Interaction, field_name: str):
        guild_id = interaction.guild.id
        db_file = f'databases/{guild_id}.db'

        if not os.path.exists(db_file):
            await interaction.response.send_message("Database not found for this guild.", ephemeral=True)
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
