import discord
from discord import app_commands

async def setup(bot):
    if bot.tree.get_command('help'):
        bot.tree.remove_command('help')

    @bot.tree.command(name="help", description="Displays a list of commands with usage details.")
    async def help(interaction: discord.Interaction):
        anyone_embed = discord.Embed(
            title="Anyone Commands",
            description="Use the command format below to copy!",
            color=discord.Color.blue()
        )

        anyone_commands = [
            {
                "name": "/new",
                "description": "Create a new character sheet entry.",
                "params": [
                    "[character_name: `{Name of the Character}`]",
                    "[sheet_link: `{Link to Google Docs or another platform}`]",
                    "[extra_fields: `{Optionally add text to each field, separated by commas.}`]"
                ]
            },
            {
                "name": "/update_field",
                "description": "Update a specific field of an existing character.",
                "params": [
                    "[character_name: `{Name of the Character}`]",
                    "[field_name: `{Name of the field to change}`]",
                    "[new_value: `{New text, cannot be empty}`]"
                ]
            },
            {
                "name": "/delete_character",
                "description": "Delete a character sheet entry.",
                "params": [
                    "[member: `@Mention`] ",
                    "[character_name: `{Name of the Character}`]"
                ]
            },
            {
                "name": "/search",
                "description": "Search for character sheets.",
                "params": [
                    "[query: `{Partial or full character name}`]",
                    "[page: `{Optional page number for faster continued searching}`]"
                ]
            },
            {
                "name": "/combat",
                "description": "Start a combat with a character.",
                "params": [
                    "[name: `{Name of the Character}`]",
                    "[hp: `{HP of the Character}`]"
                ]
            },
            {
                "name": "/fight",
                "description": "Start a fight between two characters.",
                "params": [
                    "[name1: `{Name of the first Character}`]",
                    "[name2: `{Name of the second Character}`]"
                ]
            },
            {
                "name": "/fight_dynamic",
                "description": "Start a dynamic fight with another member.",
                "params": [
                    "[opponent: `@Mention the opponent`] "
                ]
            },
            {
                "name": "/work",
                "description": "Work to earn money.",
                "params": []
            },
            {
                "name": "/inventory",
                "description": "Show the user's inventory.",
                "params": []
            },
            {
                "name": "/shop",
                "description": "Show the list of items in the shop.",
                "params": []
            },
            {
                "name": "/shop_buy",
                "description": "Buy an item from the shop.",
                "params": [
                    "[item: `{Name of the item}`]",
                    "[quantity: `{Quantity of the item}`]"
                ]
            }
        ]

        for command in anyone_commands:
            anyone_embed.add_field(
                name=f"**{command['name']}**",
                value=f"**Description:** {command['description']}\n" + "\n".join(command['params']),
                inline=False
            )

        admin_embed = discord.Embed(
            title="Admin Only Commands",
            description="Use the command format below to copy!",
            color=discord.Color.red()
        )

        admin_commands = [
            {
                "name": "/setup_guild",
                "description": "Set up guild-specific configurations.\n**((Max total extra fields is 15!))**",
                "params": [
                    "[extra_fields: `{Optionally create additional fields to fill out.}`]"
                ]
            },
            {
                "name": "/set_channel",
                "description": "Set the channel where members will be notified.",
                "params": [
                    "[channel: `{Select the channel where members will be notified}`]"
                ]
            },
            {
                "name": "/set_update_channel",
                "description": "Set the channel for moderators to receive new posts.",
                "params": [
                    "[channel: `{Select the channel where moderators will receive new posts}`]"
                ]
            },
            {
                "name": "/update_request",
                "description": "Update a character sheet request.",
                "params": [
                    "[uid: `{UID of the character request}`]",
                    "[action: `{Approve/Deny/Discuss}`]",
                    "[note: `{Optional comment}`]"
                ]
            },
            {
                "name": "/add_field",
                "description": "Add a new field to the character sheets.\n**((Max total extra fields is 15!))**",
                "params": [
                    "[field_name: `{Name of the field to add; this will be added just above Admin Note}`]"
                ]
            },
            {
                "name": "/remove_field",
                "description": "Remove a field from the character sheets.",
                "params": [
                    "[field_name: `{Name of the field to remove}`]"
                ]
            },
            {
                "name": "/setup_currency",
                "description": "Setup the currency system.",
                "params": []
            },
            {
                "name": "/setup_work",
                "description": "Setup the work command.",
                "params": [
                    "[min_amount: `{Minimum amount of money}`]",
                    "[max_amount: `{Maximum amount of money}`]"
                ]
            },
            {
                "name": "/take_money",
                "description": "Take money from a user.",
                "params": [
                    "[user: `@Mention the user`]",
                    "[amount: `{Amount of money}`]"
                ]
            },
            {
                "name": "/give_money",
                "description": "Give money to a user.",
                "params": [
                    "[user: `@Mention the user`]",
                    "[amount: `{Amount of money}`]"
                ]
            },
            {
                "name": "/give_item",
                "description": "Give an item to a user.",
                "params": [
                    "[item: `{Name of the item}`]",
                    "[quantity: `{Quantity of the item}`]",
                    "[member: `@Mention the member`]"
                ]
            },
            {
                "name": "/take_item",
                "description": "Take an item from a user.",
                "params": [
                    "[item: `{Name of the item}`]",
                    "[quantity: `{Quantity of the item}`]",
                    "[member: `@Mention the member`]"
                ]
            },
            {
                "name": "/add_item",
                "description": "Add a new item to the inventory.",
                "params": [
                    "[item: `{Name of the item}`]",
                    "[description: `{Description of the item}`]"
                ]
            },
            {
                "name": "/remove_item",
                "description": "Remove an item from the inventory.",
                "params": [
                    "[item: `{Name of the item}`]"
                ]
            },
            {
                "name": "/trade",
                "description": "Trade an item with another user.",
                "params": [
                    "[item: `{Name of the item}`]",
                    "[price: `{Price of the item}`]",
                    "[member: `@Mention the member`]"
                ]
            },
            {
                "name": "/shop_add",
                "description": "Add a new item to the shop.",
                "params": [
                    "[item: `{Name of the item}`]",
                    "[price: `{Price of the item}`]",
                    "[description: `{Description of the item}`]"
                ]
            },
            {
                "name": "/fight_rules",
                "description": "Update the fight rules.",
                "params": [
                    "[weight1: `{Weight for outcome 1}`]",
                    "[weight2: `{Weight for outcome 2}`]",
                    "[weight3: `{Weight for outcome 3}`]",
                    "[weight4: `{Weight for outcome 4}`]"
                ]
            },
            {
                "name": "/fight_dynamic_rules",
                "description": "Update the dynamic fight rules.",
                "params": [
                    "[weight1: `{Weight for outcome 1}`]",
                    "[weight2: `{Weight for outcome 2}`]",
                    "[weight3: `{Weight for outcome 3}`]",
                    "[weight4: `{Weight for outcome 4}`]"
                ]
            }
        ]

        for command in admin_commands:
            admin_embed.add_field(
                name=f"**{command['name']}**",
                value=f"**Description:** {command['description']}\n" + "\n".join(command['params']),
                inline=False
            )

        await interaction.response.send_message(embeds=[anyone_embed, admin_embed])
