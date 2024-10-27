import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

from commands.delete_character import setup as setup_delete_character
from commands.setup_guild import setup as setup_setup_guild
from commands.new import setup as setup_new
from commands.set_channel import setup as setup_set_channel
from commands.set_update_channel import setup as setup_set_update_channel
from commands.update_request import setup as setup_update_request
from commands.search import setup as setup_search
from commands.update_field import setup as setup_update_field
from commands.remove_field import setup as setup_remove_field
from commands.add_field import setup as setup_add_field
from commands.help_command import setup as setup_help_command

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await setup_commands(bot)
    await bot.tree.sync()
    print("Commands have been synced.")

    for command in bot.tree.get_commands():
        print(f"Command: {command.name}")

async def setup_commands(bot):
    command_names = [
        'delete_character',
        'setup_guild',
        'new',
        'set_channel',
        'set_update_channel',
        'update_request',
        'search',
        'update_field',
        'remove_field',
        'add_field',
        'help_command'
    ]

    for command_name in command_names:
        if bot.tree.get_command(command_name):
            bot.tree.remove_command(command_name)

    if bot.tree.get_command('help'):
        bot.tree.remove_command('help')

    setup_delete_character(bot)
    setup_setup_guild(bot)
    setup_new(bot)
    setup_set_channel(bot)
    setup_set_update_channel(bot)
    setup_update_request(bot)
    setup_search(bot)
    setup_update_field(bot)
    setup_remove_field(bot)
    setup_add_field(bot)

    await setup_help_command(bot)

bot.run(TOKEN)
