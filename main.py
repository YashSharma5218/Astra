import os
import discord
from discord.ext import commands
import pathlib
from config import TOKEN

class CaseInsensitiveDict(dict):
    """A case-insensitive dictionary."""

    def __getitem__(self, key):
        if isinstance(key, str):
            key = key.lower()
        return super().__getitem__(key)

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=discord.Intents.all(), 
            case_insensitive=True
        )
        self.bot_commands = CaseInsensitiveDict()

    async def setup_hook(self):
        """Recursively loads all Python cogs from ./cogs and subdirectories using pathlib."""
        # rglob('*.py') finds all .py files in ./cogs and any nested subdirectories
        for path in pathlib.Path('./cogs').rglob('*.py'):
            # Convert file path parts into a dot-notation module path (e.g. 'cogs.misc.test')
            module_path = '.'.join(path.with_suffix('').parts)
            
            try:
                await self.load_extension(module_path)
                print(f'Loaded cog: {module_path}')
            except Exception as e:
                print(f'Failed to load cog {module_path}: {e}')

    async def on_ready(self):
        print(f'Logged in as {self.user.name} ({self.user.id})')
        print('-------------------------')
        await self.change_presence(activity=discord.Game(name="!help for commands"))

    async def on_command_error(self, ctx, exception):
        # Silently ignore CommandNotFound errors
        if isinstance(exception, commands.CommandNotFound):
            return
        # Let other errors print normally for debugging
        raise exception

client = MyBot()
client.run(TOKEN)