import discord
from discord import app_commands
import sqlite3
import os

def setup(bot):
    @bot.tree.command(name="remove_field", description="Remove an extra field from the character database.")
    @app_commands.default_permissions(administrator=True)
    async def remove_field(interaction: discord.Interaction, field_name: str):
        guild_id = interaction.guild.id
        db_file = f'databases/{guild_id}.db'

        if not os.path.exists(db_file):
            await interaction.response.send_message("Database not found for this guild.", ephemeral=True)
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
