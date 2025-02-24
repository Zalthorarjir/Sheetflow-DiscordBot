import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging
import time
from colorama import init, Fore, Style
import sqlite3

init(autoreset=True)

logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

from commands.sheet import setup as setup_sheet
from commands.field import setup as setup_field
from commands.server_setup import setup as setup_server_setup
from commands.help import setup as setup_help_command
from commands.update import setup as setup_update
from commands.combat import setup as setup_combat
from commands.fight import setup as setup_fight
from commands.fight_dynamic import setup as setup_fight_dynamic
from commands.currency import setup as setup_currency
from commands.currency import setup_work as setup_work_command
from commands.currency import take_money as take_money_command
from commands.currency import give_money as give_money_command
from commands.currency import work as work_command
from commands.inventory import setup_inventory as setup_inventory_command
from commands.inventory import give_item as give_item_command
from commands.inventory import take_item as take_item_command
from commands.inventory import add_item as add_item_command
from commands.inventory import trade as trade_command
from commands.inventory import remove_item as remove_item_command
from commands.shop import setup as setup_shop

def initialize_databases():
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS shop (item TEXT PRIMARY KEY, price INTEGER, description TEXT)''')
    conn.commit()
    conn.close()

    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (user_id INTEGER, item TEXT, quantity INTEGER, UNIQUE(user_id, item))''')
    conn.commit()
    conn.close()

    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS currency (user_id INTEGER PRIMARY KEY, amount INTEGER)''')
    conn.commit()
    conn.close()

@bot.event
async def on_ready():
    initialize_databases()
    print(f'Logged in as {bot.user}')
    await setup_commands(bot)
    await bot.tree.sync()
    print("Commands have been synced.")

    for command in bot.tree.get_commands():
        print(f"Command: {command.name}")

async def setup_commands(bot):
    start_time = time.time()
    
    command_names = [
        'sheet remove',
        'setup_guild',
        'sheet new',
        'setup admin_channel',
        'setup member_channel',
        'sheet update',
        'field update',
        'field remove',
        'field add',
        'help_command',
        'combat',
        'fight',
        'fight_dynamic',
        'setup',
        'add_item',
        'remove_item',
        'take_money',
        'take_item',
        'give_money',
        'give_item',
        'name',
        'setup_currency',
        'setup_work',
        'take_money',
        'give_money',
        'work',
        'trade'
    ]

    for command_name in command_names:
        if not bot.tree.get_command('sheet'):
            setup_sheet(bot)
        if not bot.tree.get_command('field'):
            setup_field(bot)
        if not bot.tree.get_command('server_setup'):
            await setup_server_setup(bot)
        if not bot.tree.get_command('update'):
            setup_update(bot)
        if not bot.tree.get_command('fight'):
            await setup_fight(bot)
        if not bot.tree.get_command('combat'):
            await setup_combat(bot)
        if not bot.tree.get_command('help_command'):
            await setup_help_command(bot)
        if not bot.tree.get_command('fight_dynamic'):
            await setup_fight_dynamic(bot)
        if not bot.tree.get_command('setup_currency'):
            setup_currency(bot)
        if not bot.tree.get_command('setup_work'):
            setup_work_command(bot)
        if not bot.tree.get_command('take_money'):
            take_money_command(bot)
        if not bot.tree.get_command('give_money'):
            give_money_command(bot)
        if not bot.tree.get_command('work'):
            work_command(bot)
        if not bot.tree.get_command('setup_inventory'):
            await setup_inventory_command(bot)
        if not bot.tree.get_command('give_item'):
            await give_item_command(bot)
        if not bot.tree.get_command('take_item'):
            await take_item_command(bot)
        if not bot.tree.get_command('add_item'):
            await add_item_command(bot)
        if not bot.tree.get_command('trade'):
            await trade_command(bot)
        if not bot.tree.get_command('remove_item'):
            await remove_item_command(bot)
        if not bot.tree.get_command('shop_add'):
            setup_shop(bot)
        if not bot.tree.get_command('shop'):
            setup_shop(bot)
        if not bot.tree.get_command('inventory'):
            setup_shop(bot)
        await bot.tree.sync()
        print(f"{Fore.GREEN}Commands have been synced.{Style.RESET_ALL}")
    
    end_time = time.time()
    logging.info(f"Setup commands took {end_time - start_time:.2f} seconds")

bot.run(TOKEN)
