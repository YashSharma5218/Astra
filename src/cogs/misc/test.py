import discord
from discord.ext import commands

class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        await ctx.send("Test command executed!")


# setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(TestCog(bot))

