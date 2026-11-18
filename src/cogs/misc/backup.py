import traceback

from discord.ext import commands, tasks

from src.config import BACKUP_DIR, BACKUP_KEEP
from src.core.backup import run_backup


class Backup(commands.Cog):
    """Backs up the database once a day. The check runs every hour and at start-up, so a bot that
    was off at the usual time still makes today's backup when it comes back."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.daily.start()

    async def cog_unload(self):
        self.daily.cancel()

    @tasks.loop(hours=1)
    async def daily(self):
        try:
            path = await run_backup(self.bot.db, BACKUP_DIR, BACKUP_KEEP)
            if path:
                print(f"Database backup saved: {path}")
        except Exception:                      # never let a failed backup stop the loop
            print("Database backup failed:")
            traceback.print_exc()

    @commands.command()
    @commands.is_owner()
    async def backup(self, ctx):
        """Owner only: make a backup right now (replaces today's file). Example: `!backup`."""
        path = await run_backup(self.bot.db, BACKUP_DIR, BACKUP_KEEP, force=True)
        await ctx.send(f"Backup saved to `{path}`.")


async def setup(bot):
    await bot.add_cog(Backup(bot))