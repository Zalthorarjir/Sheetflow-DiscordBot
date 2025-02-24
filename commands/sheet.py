import discord
from discord import app_commands
import sqlite3
import os
import re
from datetime import datetime
import uuid

# Ensure the 'databases' directory exists
if not os.path.exists('databases'):
    os.makedirs('databases')

def get_guild_config(guild_id):
    db_file = f'databases/{guild_id}.db'
    if not os.path.isfile(db_file):
        return None
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('SELECT channel_id, update_channel_id, extra_fields FROM guild_config WHERE guild_id = ?', (guild_id,))
    result = c.fetchone()
    conn.close()
    return result

def setup(bot):
    sheet_group = app_commands.Group(name="sheet", description="Commands related to character sheets")

    @sheet_group.command(name="new", description="Create a new character sheet entry")
    async def new_command(interaction: discord.Interaction, character_name: str, sheet_link: str, extra_fields: str = ""):
        if interaction.channel.type == discord.ChannelType.private:
            await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
            return

        await interaction.response.defer()
        guild_id = interaction.guild.id
        config = get_guild_config(guild_id)

        if config is None:
            await interaction.followup.send("No configuration found for this guild. Please run the setup command.", ephemeral=True)
            return

        try:
            channel_id = int(config[0])
        except (TypeError, ValueError):
            await interaction.followup.send("Configured channel ID is invalid. Please contact an admin.", ephemeral=True)
            return
        
        extra_fields_list = [field.strip() for field in config[2].split(',')] if config[2] else []
        
        db_file = f'databases/{guild_id}.db'
        if not os.path.isfile(db_file):
            await interaction.followup.send("No configuration found for this guild. Please run the setup command.", ephemeral=True)
            return

        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        uid = str(uuid.uuid4())  # Generate a unique identifier for the sheet

        columns = ["uid", "guild_id", "member_id", "character_name", "sheet_link", "admin_note", "status", "last_updated"]
        values = [uid, guild_id, interaction.user.id, character_name, sheet_link, "", "Under Discussion", current_time]

        extra_field_values = extra_fields.split(',') if extra_fields else []

        for i, field in enumerate(extra_fields_list):
            columns.append(field)
            values.append(extra_field_values[i].strip() if i < len(extra_field_values) else "")

        query = f"INSERT INTO characters ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(values))})"
        c.execute(query, values)
        
        conn.commit()
        conn.close()

        staff_channel = bot.get_channel(channel_id)
        if not staff_channel:
            await interaction.followup.send("Configured channel not found. Please contact an admin.", ephemeral=True)
            return

        embed = discord.Embed(title="New Character Sheet Request", color=discord.Color.blue())
        embed.add_field(name="UID", value=uid, inline=False)  # Add UID to the embed
        embed.add_field(name="Character", value=character_name, inline=False)
        embed.add_field(name="Member", value=interaction.user.mention, inline=False)
        embed.add_field(name="Sheet Link", value=sheet_link, inline=False)

        for i, field_name in enumerate(extra_fields_list):
            embed.add_field(name=field_name.capitalize(), value=extra_field_values[i].strip() if i < len(extra_field_values) else "[Pending]", inline=False)

        embed.add_field(name="Admin Note", value="", inline=False)
        embed.add_field(name="Status", value="Under Discussion", inline=False)
        embed.add_field(name="Last Update", value=current_time, inline=False)
        
        await staff_channel.send(embed=embed)
        await interaction.followup.send("Your character sheet request has been submitted.", ephemeral=True)

    @sheet_group.command(name="remove", description="Delete a character from the database.")
    @app_commands.describe(member="Mention the character owner", character_name="Name of the character to delete")
    async def delete_character_command(interaction: discord.Interaction, member: discord.Member, character_name: str):
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
            await interaction.response.send_message("Guild configuration not found. Please ask an admin to run /setup guild first.", ephemeral=True)
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

    @sheet_group.command(name="find", description="Search approved characters by name or member mention with pagination")
    async def search_command(interaction: discord.Interaction, query: str, page: int = 1):
        if interaction.channel.type == discord.ChannelType.private:
            await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
            return

        items_per_page = 1
        offset = (page - 1) * items_per_page

        mention_match = re.match(r'<@!?(\d+)>', query)
        if mention_match:
            member_id = int(mention_match.group(1))
            search_by = "member_id"
            search_query = member_id
        else:
            search_by = "character_name"
            search_query = f'%{query}%'

        guild_id = interaction.guild.id
        db_file = f'databases/{guild_id}.db'
        if not os.path.isfile(db_file):
            await interaction.response.send_message("Database not found. Please ask an admin to set up the database.", ephemeral=True)
            return

        conn = sqlite3.connect(db_file)
        c = conn.cursor()

        if search_by == "member_id":
            c.execute('''SELECT * FROM characters WHERE member_id = ? LIMIT ? OFFSET ?''', (search_query, items_per_page, offset))
        else:
            c.execute('''SELECT * FROM characters WHERE character_name LIKE ? LIMIT ? OFFSET ?''', (search_query, items_per_page, offset))

        results = c.fetchall()

        c.execute('SELECT extra_fields FROM guild_config WHERE guild_id = ?', (guild_id,))
        extra_fields_str = c.fetchone()[0]
        extra_fields = extra_fields_str.split(',') if extra_fields_str else []

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
                admin_note = row[5] if row[5] else ""
                status = row[6]
                last_updated = row[7]
                member_mention = f"<@{member_id}>"

                embed.add_field(name="Character", value=character_name, inline=False)
                embed.add_field(name="Member", value=member_mention, inline=False)
                embed.add_field(name="Sheet Link", value=sheet_link, inline=False)

                for field in extra_fields:
                    field_value = row[8 + extra_fields.index(field)] if len(row) > 8 + extra_fields.index(field) else "N/A"
                    embed.add_field(name=field.strip(), value=field_value if field_value else "No value", inline=False)

                embed.add_field(name="Admin Note", value=admin_note if admin_note else "No note", inline=False)
                embed.add_field(name="Status", value=status, inline=False)
                embed.add_field(name="Last Update", value=last_updated, inline=False)

            total_pages = (total_results // items_per_page) + (1 if total_results % items_per_page else 0)
            embed.set_footer(text=f"Page {page} of {total_pages}")

            view = discord.ui.View()
            prev_button = discord.ui.Button(label="Previous", style=discord.ButtonStyle.primary, custom_id="prev")

            async def prev_button_callback(interaction: discord.Interaction):
                nonlocal page
                if page > 1:
                    page -= 1
                    await update_embed(interaction, query, page, extra_fields)
                else:
                    await interaction.response.send_message("You are already on the first page.", ephemeral=True)

            prev_button.callback = prev_button_callback
            view.add_item(prev_button)

            next_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.primary, custom_id="next")

            async def next_button_callback(interaction: discord.Interaction):
                nonlocal page
                if page < total_pages:
                    page += 1
                    await update_embed(interaction, query, page, extra_fields)
                else:
                    await interaction.response.send_message("You are already on the last page.", ephemeral=True)

            next_button.callback = next_button_callback
            view.add_item(next_button)

            await interaction.response.send_message(embed=embed, view=view)
        else:
            await interaction.response.send_message("No results found.", ephemeral=False)

    async def update_embed(interaction, query, page, extra_fields):
        items_per_page = 1
        offset = (page - 1) * items_per_page

        guild_id = interaction.guild.id
        db_file = f'databases/{guild_id}.db'
        if not os.path.isfile(db_file):
            await interaction.response.send_message("Database not found. Please ask an admin to set up the database.", ephemeral=True)
            return

        conn = sqlite3.connect(db_file)
        c = conn.cursor()

        mention_match = re.match(r'<@!?(\d+)>', query)
        if mention_match:
            member_id = int(mention_match.group(1))
            search_by = "member_id"
            search_query = member_id
        else:
            search_by = "character_name"
            search_query = f'%{query}%'

        if search_by == "member_id":
            c.execute('''SELECT * FROM characters WHERE member_id = ? LIMIT ? OFFSET ?''', (search_query, items_per_page, offset))
        else:
            c.execute('''SELECT * FROM characters WHERE character_name LIKE ? LIMIT ? OFFSET ?''', (search_query, items_per_page, offset))

        results = c.fetchall()

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
                admin_note = row[5] if row[5] else ""
                status = row[6]
                last_updated = row[7]
                member_mention = f"<@{member_id}>"

                embed.add_field(name="Character", value=character_name, inline=False)
                embed.add_field(name="Member", value=member_mention, inline=False)
                embed.add_field(name="Sheet Link", value=sheet_link, inline=False)

                for field in extra_fields:
                    field_value = row[8 + extra_fields.index(field)] if len(row) > 8 + extra_fields.index(field) else "N/A"
                    embed.add_field(name=field.strip(), value=field_value if field_value else "No value", inline=False)

                embed.add_field(name="Admin Note", value=admin_note if admin_note else "No note", inline=False)
                embed.add_field(name="Status", value=status, inline=False)
                embed.add_field(name="Last Update", value=last_updated, inline=False)

            total_pages = (total_results // items_per_page) + (1 if total_results % items_per_page else 0)
            embed.set_footer(text=f"Page {page} of {total_pages}")

            await interaction.response.edit_message(embed=embed)
        else:
            await interaction.response.send_message("No results found.", ephemeral=False)

    if not bot.tree.get_command("sheet"):
        bot.tree.add_command(sheet_group)
