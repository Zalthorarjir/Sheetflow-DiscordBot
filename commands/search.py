import discord
from discord import app_commands
import sqlite3
import re

def setup(bot):
    @bot.tree.command(name="search", description="Search approved characters by name or member mention with pagination")
    async def search(interaction: discord.Interaction, query: str, page: int = 1):
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
