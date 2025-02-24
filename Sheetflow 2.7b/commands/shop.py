import discord
from discord.ext import commands
import sqlite3
import asyncio

DATABASE = 'shop.db'

def initialize_shop_database():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS shop (item TEXT PRIMARY KEY, price INTEGER, description TEXT)''')
    conn.commit()
    conn.close()

def setup(bot):
    initialize_shop_database()
    @bot.tree.command(name="shop_add", description="Add a new item to the shop")
    @commands.has_permissions(administrator=True)
    async def shop_add(interaction: discord.Interaction, item: str, price: int, description: str = None):
        # Check if the item exists in the inventory database
        conn = sqlite3.connect('inventory.db')
        c = conn.cursor()
        c.execute('''SELECT description FROM inventory WHERE item = ?''', (item,))
        result = c.fetchone()
        if result is None:
            await interaction.response.send_message(f"Item {item} does not exist in the inventory database.")
            conn.close()
            return
        if description is None:
            description = result[0]
        conn.close()

        # Add the item to the shop database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS shop (item TEXT PRIMARY KEY, price INTEGER, description TEXT)''')
        c.execute('''INSERT OR REPLACE INTO shop (item, price, description) VALUES (?, ?, ?)''', (item, price, description))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Added {item} to the shop with price {price} and description '{description}'.")

    @bot.tree.command(name="shop", description="Show the list of items in the shop")
    async def shop(interaction: discord.Interaction):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''SELECT item, price, description FROM shop''')
        items = c.fetchall()
        conn.close()

        if not items:
            await interaction.response.send_message("The shop is empty.")
            return

        embeds = []
        for i in range(0, len(items), 5):
            embed = discord.Embed(title="Shop Items", color=discord.Color.blue())
            for item, price, description in items[i:i+5]:
                if description is None:
                    # Check if the description exists in the inventory database
                    inventory_conn = sqlite3.connect('inventory.db')
                    inventory_c = inventory_conn.cursor()
                    inventory_c.execute('''SELECT description FROM inventory WHERE item = ?''', (item,))
                    inventory_result = inventory_c.fetchone()
                    if inventory_result:
                        description = inventory_result[0]
                    inventory_conn.close()
                embed.add_field(name=item, value=f"Price: {price}\nDescription: {description}", inline=False)
            embeds.append(embed)

        await interaction.response.send_message(embed=embeds[0])
        if len(embeds) > 1:
            message = await interaction.followup.send(embed=embeds[0])
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

            def check(reaction, user):
                return user == interaction.user and str(reaction.emoji) in ["⬅️", "➡️"]

            index = 0
            while True:
                try:
                    reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                    if str(reaction.emoji) == "⬅️" and index > 0:
                        index -= 1
                        await message.edit(embed=embeds[index])
                    elif str(reaction.emoji) == "➡️" and index < len(embeds) - 1:
                        index += 1
                        await message.edit(embed=embeds[index])
                    await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    break

    @bot.tree.command(name="shop_buy", description="Buy an item from the shop")
    async def shop_buy(interaction: discord.Interaction, item: str, quantity: int):
        # Check if the item exists in the shop database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''SELECT price, description FROM shop WHERE item = ?''', (item,))
        result = c.fetchone()
        if result is None:
            await interaction.response.send_message(f"Item {item} is not available in the shop.")
            conn.close()
            return
        price, description = result
        total_cost = price * quantity
        conn.close()

        # Check if the user has enough money
        currency_conn = sqlite3.connect('currency.db')
        currency_c = currency_conn.cursor()
        currency_c.execute('''SELECT amount FROM currency WHERE user_id = ?''', (interaction.user.id,))
        result = currency_c.fetchone()
        if result is None or result[0] < total_cost:
            await interaction.response.send_message(f"You do not have enough money to buy {quantity} {item}(s).")
            currency_conn.close()
            return

        # Deduct the money from the user's account
        currency_c.execute('''UPDATE currency SET amount = amount - ? WHERE user_id = ?''', (total_cost, interaction.user.id))
        currency_conn.commit()
        currency_conn.close()

        # Add the item to the user's inventory
        inventory_conn = sqlite3.connect('inventory.db')
        inventory_c = inventory_conn.cursor()
        inventory_c.execute('''INSERT INTO inventory (user_id, item, quantity, description) VALUES (?, ?, ?, ?) ON CONFLICT(user_id, item) DO UPDATE SET quantity = quantity + ?''', (interaction.user.id, item, quantity, description, quantity))
        inventory_conn.commit()
        inventory_conn.close()

        await interaction.response.send_message(f"You bought {quantity} {item}(s) for {total_cost} money.")

    @bot.tree.command(name="inventory", description="Show the user's inventory")
    async def inventory(interaction: discord.Interaction):
        conn = sqlite3.connect('inventory.db')
        c = conn.cursor()
        c.execute('''SELECT item, quantity, description FROM inventory WHERE user_id = ?''', (interaction.user.id,))
        items = c.fetchall()
        conn.close()

        if not items:
            await interaction.response.send_message("Your inventory is empty.")
            return

        embeds = []
        for i in range(0, len(items), 5):
            embed = discord.Embed(title="Your Inventory", color=discord.Color.green())
            for item, quantity, description in items[i:i+5]:
                embed.add_field(name=item, value=f"Quantity: {quantity}\nDescription: {description}", inline=False)
            embeds.append(embed)

        await interaction.response.send_message(embed=embeds[0])
        if len(embeds) > 1:
            message = await interaction.followup.send(embed=embeds[0])
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

            def check(reaction, user):
                return user == interaction.user and str(reaction.emoji) in ["⬅️", "➡️"]

            index = 0
            while True:
                try:
                    reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                    if str(reaction.emoji) == "⬅️" and index > 0:
                        index -= 1
                        await message.edit(embed=embeds[index])
                    elif str(reaction.emoji) == "➡️" and index < len(embeds) - 1:
                        index += 1
                        await message.edit(embed=embeds[index])
                    await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    break
