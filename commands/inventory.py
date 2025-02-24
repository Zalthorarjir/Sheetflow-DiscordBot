import discord
from discord.ext import commands
import sqlite3
import asyncio

# Connect to the database
conn = sqlite3.connect('inventory.db')
c = conn.cursor()

# Create table if it doesn't exist with a unique constraint on (user_id, item)
c.execute('''CREATE TABLE IF NOT EXISTS inventory
             (user_id INTEGER, item TEXT, quantity INTEGER, description TEXT, 
             UNIQUE(user_id, item))''')
conn.commit()

async def setup_inventory(bot):
    @bot.tree.command(name="setup_inventory")
    async def setup_inventory_command(interaction: discord.Interaction):
        await inventory(interaction, bot)

async def inventory(interaction: discord.Interaction, bot):
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

async def give_item(bot):
    @bot.tree.command(name="give_item")
    async def give_item_command(interaction: discord.Interaction, item: str, quantity: int, member: discord.Member):
        # Check if the item exists in the database
        c.execute("SELECT description FROM inventory WHERE user_id = 0 AND item = ?", (item,))
        result = c.fetchone()
        if result is None:
            await interaction.response.send_message(f"Item {item} does not exist in the inventory.")
            return
        description = result[0]
        
        # Check if the user already has the item
        c.execute("SELECT * FROM inventory WHERE user_id = ? AND item = ?", (member.id, item))
        if c.fetchone() is None:
            # If the user does not have the item, insert it
            c.execute("INSERT INTO inventory (user_id, item, quantity, description) VALUES (?, ?, ?, ?)", (member.id, item, quantity, description))
        else:
            # If the user already has the item, update the quantity
            c.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item = ?", (quantity, member.id, item))
        
        conn.commit()
        await interaction.response.send_message(f"Gave {quantity} {item}(s) to {member.mention}.")

async def take_item(bot):
    @bot.tree.command(name="take_item")
    async def take_item_command(interaction: discord.Interaction, item: str, quantity: int, member: discord.Member):
        c.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item = ?", (quantity, member.id, item))
        conn.commit()
        await interaction.response.send_message(f"Took {quantity} {item}(s) from {member.mention}.")

async def add_item(bot):
    @bot.tree.command(name="add_item")
    async def add_item_command(interaction: discord.Interaction, item: str, description: str = None):
        # Check if the item already exists
        c.execute("SELECT * FROM inventory WHERE user_id = 0 AND item = ?", (item,))
        if c.fetchone() is None:
            # If the item does not exist, insert it
            c.execute("INSERT INTO inventory (user_id, item, quantity, description) VALUES (?, ?, ?, ?)", (0, item, 0, description))
            await interaction.response.send_message(f"Added {item} to the list of available items with description '{description}'.")
        else:
            await interaction.response.send_message(f"Item {item} already exists in the list of available items.")
        conn.commit()

async def remove_item(bot):
    @bot.tree.command(name="remove_item")
    async def remove_item_command(interaction: discord.Interaction, item: str):
        c.execute("DELETE FROM inventory WHERE item = ?", (item,))
        conn.commit()
        await interaction.response.send_message(f"Removed all entries of {item} from the inventory.")

async def trade(bot):
    @bot.tree.command(name="trade")
    async def trade_command(interaction: discord.Interaction, item: str, price: int, member: discord.Member):
        # Check if the item exists in the user's inventory
        c.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item = ?", (interaction.user.id, item))
        result = c.fetchone()
        if result is None or result[0] < 1:
            await interaction.response.send_message(f"You do not have enough {item}(s) to trade.")
            return
        
        # Create a trade offer
        await interaction.response.send_message(f"{interaction.user.mention} is offering {item} for {price} to {member.mention}.")
        trade_message = await interaction.followup.send(f"{member.mention}, react with ✅ to accept or ❌ to decline.")
        await trade_message.add_reaction("✅")
        await trade_message.add_reaction("❌")
        
        # Wait for the member to react
        def check(reaction, user):
            return user == member and str(reaction.emoji) in ["✅", "❌"]
        
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send(f"{member.mention} did not respond in time. Trade cancelled.")
            return
        
        if str(reaction.emoji) == "❌":
            await interaction.followup.send(f"{member.mention} declined the trade.")
            return
        
        # Check if the member has enough money
        currency_conn = sqlite3.connect('currency.db')
        currency_c = currency_conn.cursor()
        currency_c.execute("CREATE TABLE IF NOT EXISTS currency (user_id INTEGER PRIMARY KEY, amount INTEGER)")
        currency_c.execute("SELECT amount FROM currency WHERE user_id = ?", (member.id,))
        result = currency_c.fetchone()
        if result is None or result[0] < price:
            await interaction.followup.send(f"{member.mention} does not have enough money to complete the trade.")
            currency_conn.close()
            return
        
        # Fetch the description of the item
        c.execute("SELECT description FROM inventory WHERE user_id = 0 AND item = ?", (item,))
        result = c.fetchone()
        if result is None:
            await interaction.followup.send(f"Item {item} does not exist in the inventory.")
            return
        description = result[0]

        # Complete the trade
        c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item = ?", (interaction.user.id, item))
        try:
            c.execute("INSERT INTO inventory (user_id, item, quantity, description) VALUES (?, ?, 1, ?) ON CONFLICT(user_id, item) DO UPDATE SET quantity = quantity + 1", (member.id, item, description))
        except sqlite3.IntegrityError:
            c.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item = ?", (member.id, item))
        
        # Remove the item from the user's inventory if the quantity is 0
        c.execute("DELETE FROM inventory WHERE user_id = ? AND item = ? AND quantity = 0", (interaction.user.id, item))
        
        # Update currency for both users
        currency_c.execute("UPDATE currency SET amount = amount - ? WHERE user_id = ?", (price, member.id))
        
        # Ensure the user who initiated the trade exists in the currency table
        currency_c.execute("SELECT amount FROM currency WHERE user_id = ?", (interaction.user.id,))
        if currency_c.fetchone() is None:
            currency_c.execute("INSERT INTO currency (user_id, amount) VALUES (?, ?)", (interaction.user.id, 0))
        
        # Add the currency to the user who initiated the trade
        currency_c.execute("UPDATE currency SET amount = amount + ? WHERE user_id = ?", (price, interaction.user.id))
        
        conn.commit()
        currency_conn.commit()
        currency_conn.close()
        
        await interaction.followup.send(f"Trade completed: {interaction.user.mention} traded {item} to {member.mention} for {price} money.")
