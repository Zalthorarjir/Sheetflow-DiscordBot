import discord
from discord import app_commands
from discord.ext import commands
import random

weights = [0.25, 0.25, 0.25, 0.25]  # Default weights

class FightDynamic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fight_data = {}  # Dictionary to store fight data

    @app_commands.command(name='fight_dynamic')
    async def fight_dynamic(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent == interaction.user:
            await interaction.response.send_message("You cannot fight yourself!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"{interaction.user.display_name} vs {opponent.display_name}",
            description="A fight has started! React with 🗡️ to attack.",
            color=discord.Color.red()
        )
        embed.add_field(name=interaction.user.display_name, value="Health: 20", inline=True)
        embed.add_field(name=opponent.display_name, value="Health: 20", inline=True)

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await message.add_reaction("🗡️")

        self.fight_data[message.id] = {
            "challenger": interaction.user,
            "opponent": opponent,
            "challenger_health": 20,
            "opponent_health": 20,
            "turn": interaction.user,
            "interaction": interaction  # Store the interaction object
        }

    @app_commands.command(name='fight_dynamic_rules')
    @commands.has_permissions(administrator=True)
    async def fight_dynamic_rules(self, interaction: discord.Interaction, weight1: float, weight2: float, weight3: float, weight4: float):
        global weights
        weights = [weight1, weight2, weight3, weight4]
        await interaction.response.send_message(f"Fight dynamic rules updated: {weights}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        message_id = reaction.message.id
        if message_id not in self.fight_data:
            return

        fight = self.fight_data[message_id]
        if reaction.emoji != "🗡️":
            return

        if user != fight["turn"]:
            interaction = fight["interaction"]
            await interaction.followup.send(f"{user.mention}, it is not your turn yet!", ephemeral=True)
            await reaction.remove(user)  # Remove the user's reaction
            return

        outcomes = [
            f"**{user.display_name}** landed a solid hit!",
            f"**{user.display_name}** barely scratched their opponent. Better luck next time!",
            f"**{user.display_name}** missed completely. What a blunder!",
            f"**{user.display_name}** missed and ended up hitting themselves. Ouch!"
        ]
        outcome = random.choices(outcomes, weights=weights, k=1)[0]

        if user == fight["challenger"]:
            if outcome == outcomes[0]:
                fight["opponent_health"] -= 2
            elif outcome == outcomes[1]:
                fight["opponent_health"] -= 1
            elif outcome == outcomes[3]:
                fight["challenger_health"] -= 1
            fight["turn"] = fight["opponent"]
        else:
            if outcome == outcomes[0]:
                fight["challenger_health"] -= 2
            elif outcome == outcomes[1]:
                fight["challenger_health"] -= 1
            elif outcome == outcomes[3]:
                fight["opponent_health"] -= 1
            fight["turn"] = fight["challenger"]

        embed = reaction.message.embeds[0]
        embed.set_field_at(0, name=fight["challenger"].display_name, value=f"Health: {fight['challenger_health']}", inline=True)
        embed.set_field_at(1, name=fight["opponent"].display_name, value=f"Health: {fight['opponent_health']}", inline=True)
        embed.description = outcome

        await reaction.message.edit(embed=embed)
        await reaction.message.clear_reactions()  # Remove all reactions except the bot's own reaction
        await reaction.message.add_reaction("🗡️")

        if fight["challenger_health"] <= 0 or fight["opponent_health"] <= 0:
            winner = fight["challenger"] if fight["challenger_health"] > 0 else fight["opponent"]
            await reaction.message.channel.send(f"{winner.mention} wins the fight!")
            del self.fight_data[message_id]

async def setup(bot):
    await bot.add_cog(FightDynamic(bot))
    print("FightDynamic cog setup complete.")