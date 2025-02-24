import discord
from discord.ext import commands
from discord import app_commands

class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.combat_data = {}  # Dictionary to store combat data
        print("Combat cog initialized.")

    @app_commands.command(name='combat', description='Start a combat with a character')
    async def combat(self, interaction: discord.Interaction, name: str, hp: int):
        embed = discord.Embed(title=name, description=f"Has {hp} HP\n{'❤️' * hp}")
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        self.combat_data[message.id] = {'name': name, 'hp': hp, 'max_hp': hp}

        await message.add_reaction('⬇️')
        await message.add_reaction('⬆️')
        await message.add_reaction('💀')

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        message_id = reaction.message.id
        if message_id not in self.combat_data:
            return

        combat_info = self.combat_data[message_id]
        if reaction.emoji == '⬇️':
            combat_info['hp'] = max(0, combat_info['hp'] - 1)
        elif reaction.emoji == '⬆️':
            combat_info['hp'] = min(combat_info['max_hp'], combat_info['hp'] + 1)
        elif reaction.emoji == '💀':
            await reaction.message.delete()
            del self.combat_data[message_id]
            return

        embed = discord.Embed(title=combat_info['name'], description=f"Has {combat_info['hp']} HP\n{'❤️' * combat_info['hp']}")
        await reaction.message.edit(embed=embed)
        await reaction.remove(user)

async def setup(bot):
    await bot.add_cog(Combat(bot))
    if not bot.tree.get_command('combat'):
        bot.tree.add_command(Combat.combat)