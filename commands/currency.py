import discord
from discord.ext import commands
import sqlite3
import random  # Add missing import

DATABASE = 'currency.db'

def setup(bot):
    @bot.tree.command(name="setup_currency", description="Setup the currency system")
    @commands.has_permissions(administrator=True)
    async def setup_currency(interaction: discord.Interaction):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS currency (user_id INTEGER PRIMARY KEY, amount INTEGER)''')
        conn.commit()
        conn.close()
        await interaction.response.send_message("Currency system has been set up.")

def setup_work(bot):
    @bot.tree.command(name="setup_work", description="Setup the work command")
    @commands.has_permissions(administrator=True)
    async def setup_work(interaction: discord.Interaction, min_amount: int, max_amount: int):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS work (min_amount INTEGER, max_amount INTEGER)''')
        c.execute('''DELETE FROM work''')
        c.execute('''INSERT INTO work (min_amount, max_amount) VALUES (?, ?)''', (min_amount, max_amount))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Work command has been set up with range {min_amount} to {max_amount}.")

def take_money(bot):
    @bot.tree.command(name="take_money", description="Take money from a user")
    @commands.has_permissions(administrator=True)
    async def take_money(interaction: discord.Interaction, user: discord.User, amount: int):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''UPDATE currency SET amount = amount - ? WHERE user_id = ?''', (amount, user.id))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Took {amount} money from {user.mention}.")

def give_money(bot):
    @bot.tree.command(name="give_money", description="Give money to a user")
    @commands.has_permissions(administrator=True)
    async def give_money(interaction: discord.Interaction, user: discord.User, amount: int):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''INSERT INTO currency (user_id, amount) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET amount = amount + ?''', (user.id, amount, amount))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Gave {amount} money to {user.mention}.")

def work(bot):
    @bot.tree.command(name="work", description="Work to earn money")
    async def work(interaction: discord.Interaction):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''SELECT min_amount, max_amount FROM work''')
        row = c.fetchone()
        if row:
            min_amount, max_amount = row
            amount = random.randint(min_amount, max_amount)
            c.execute('''INSERT INTO currency (user_id, amount) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET amount = amount + ?''', (interaction.user.id, amount, amount))
            conn.commit()
            await interaction.response.send_message(f"You worked and earned {amount} money.")
        else:
            await interaction.response.send_message("Work command is not set up.")
        conn.close()
