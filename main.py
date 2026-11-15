import pathlib
import traceback

import discord
from discord import app_commands
from discord.ext import commands

from config import DB_PATH, PREFIX, TOKEN
from core.database import Database


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True      # needed for "!" prefix commands
        super().__init__(command_prefix=PREFIX, intents=intents, case_insensitive=True)
        self.db = Database(DB_PATH)
        self.tree.on_error = self.on_tree_error

    async def setup_hook(self):
        """Open the database, then load every cog in ./cogs and its subfolders."""
        await self.db.connect()
        # rglob('*.py') finds all .py files in ./cogs and any nested subdirectories
        for path in sorted(pathlib.Path("cogs").rglob("*.py")):
            if path.name.startswith("_"):   # helper files without a setup() are skipped
                continue
            # Convert the file path into a module path (e.g. 'cogs.misc.test')
            module_path = ".".join(path.with_suffix("").parts)
            try:
                await self.load_extension(module_path)
                print(f"Loaded cog: {module_path}")
            except Exception:
                print(f"Failed to load cog {module_path}:")
                traceback.print_exc()

    async def close(self):
        await self.db.close()
        await super().close()

    async def on_ready(self):
        print(f"Logged in as {self.user.name} ({self.user.id})")
        print("-------------------------")
        await self.change_presence(activity=discord.Game(name="/start to begin"))

    async def on_command_error(self, ctx, exception):
        # Silently ignore CommandNotFound errors
        if isinstance(exception, commands.CommandNotFound):
            return
        if isinstance(exception, commands.NotOwner):
            await ctx.send("Only the bot owner can do that.")
            return
        traceback.print_exception(type(exception), exception, exception.__traceback__)

    async def on_tree_error(self, interaction: discord.Interaction,
                            error: app_commands.AppCommandError):
        """Log slash command errors and tell the player something went wrong."""
        traceback.print_exception(type(error), error, error.__traceback__)
        message = "Something went wrong. Please try again."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


if __name__ == "__main__":
    MyBot().run(TOKEN)
    