import discord
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

    @commands.command()
    @commands.is_owner()
    async def setlevel(self, ctx, member: discord.Member, level: int):
        """Owner only: set a player's level (testing, until XP exists). Example: `!setlevel @Sam 5`."""
        if level < 1:
            await ctx.send("Level must be 1 or higher.")
            return
        if await self.bot.db.get_player(member.id) is None:
            await ctx.send(f"{member.display_name} has not used /start yet.")
            return
        async with self.bot.db.transaction():
            await self.bot.db.set_level(member.id, level)
        await ctx.send(f"{member.display_name} is now level {level}.")


async def setup(bot):
    await bot.add_cog(Admin(bot))
