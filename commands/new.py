import discord
from discord import app_commands
import sqlite3
from datetime import datetime

def setup(bot):
    if bot.tree.get_command('new'):
        bot.tree.remove_command('new')

    @bot.tree.command(name="new", description="Create a new character sheet entry")
    async def new(interaction: discord.Interaction, character_name: str, sheet_link: str, extra_fields: str = ""):
        if interaction.channel.type == discord.ChannelType.private:
            await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
            return

        await interaction.response.defer()
        guild_id = interaction.guild.id
        config = get_guild_config(guild_id)

        if config is None:
            await interaction.followup.send("No configuration found for this guild. Please run the setup command.", ephemeral=True)
            return

        channel_id = config[0]
        extra_fields_config = config[2]
        extra_fields_list = [field.strip() for field in extra_fields_config.split(',')] if extra_fields_config else []
        
        db_file = f'databases/{guild_id}.db'
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        columns = ["guild_id", "member_id", "character_name", "sheet_link", "admin_note", "status", "last_updated"]
        values = [guild_id, interaction.user.id, character_name, sheet_link, "", "Under Discussion", current_time]

        extra_field_values = extra_fields.split(',') if extra_fields else []

        for i, field in enumerate(extra_fields_list):
            if i < len(extra_field_values):
                columns.append(field)
                values.append(extra_field_values[i].strip())
            else:
                columns.append(field)
                values.append("")

        column_str = ", ".join(columns)
        placeholder_str = ", ".join(["?"] * len(values))
        query = f"INSERT INTO characters ({column_str}) VALUES ({placeholder_str})"

        c.execute(query, values)
        
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

        for i, field_name in enumerate(extra_fields_list):
            embed.add_field(name=field_name.capitalize(), value=extra_field_values[i].strip() if i < len(extra_field_values) else "[Pending]", inline=False)

        embed.add_field(name="Admin Note", value="", inline=False)
        embed.add_field(name="Status", value="Under Discussion", inline=False)
        embed.add_field(name="Last Update", value=current_time, inline=False)
        
        await staff_channel.send(embed=embed)
        await interaction.followup.send("Your character sheet request has been submitted.", ephemeral=True)

def get_guild_config(guild_id):
    db_file = f'databases/{guild_id}.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('SELECT channel_id, update_channel_id, extra_fields FROM guild_config WHERE guild_id = ?', (guild_id,))
    result = c.fetchone()
    conn.close()
    return result
