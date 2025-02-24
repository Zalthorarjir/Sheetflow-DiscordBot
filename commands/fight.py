import discord
from discord import app_commands
from discord.ext import commands
import random

weights = [0.25, 0.25, 0.25, 0.25]  # Default weights

class Fight(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='fight')
    async def fight(self, interaction: discord.Interaction, name1: str, name2: str):
        outcomes = [
            f"**{name1}** landed a solid hit on **{name2}**!",
            f"**{name1}** barely scratched **{name2}**. Better luck next time!",
            f"**{name1}** missed **{name2}** completely. What a blunder!",
            f"**{name1}** missed and ended up hitting themselves. Ouch!"
        ]
        outcome = random.choices(outcomes, weights=weights, k=1)[0]
        embed = discord.Embed(title=f":crossed_swords: Fight {name1} vs {name2} :crossed_swords:", description=outcome, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='fight_rules')
    @commands.has_permissions(administrator=True)
    async def fight_rules(self, interaction: discord.Interaction, weight1: float, weight2: float, weight3: float, weight4: float):
        global weights
        weights = [weight1, weight2, weight3, weight4]
        await interaction.response.send_message(f"Fight rules updated: {weights}")

async def setup(bot):
    await bot.add_cog(Fight(bot))
    print("Fight cog setup complete.")