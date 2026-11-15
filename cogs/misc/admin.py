from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx):
        """Owner only: publish slash commands to Discord. Run `!sync` after adding commands."""
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} slash commands. They can take a minute to appear.")


async def setup(bot):
    await bot.add_cog(Admin(bot))
