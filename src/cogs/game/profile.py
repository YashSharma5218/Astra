from discord import app_commands
from discord.ext import commands

from src.cogs.game._common import require_player
from src.game.items import SLOTS, build_fighter, generate_item
from src.ui.embeds import item_line, profile_embed

ACTIVE_PRESET = 1


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="start", description="Create your fighter and get starter gear")
    async def start(self, interaction):
        db, uid = self.bot.db, interaction.user.id
        async with db.transaction():
            # Checked inside the transaction so a double click cannot give two sets of gear
            exists = await db.get_player(uid) is not None
            if not exists:
                await db.ensure_player(uid)
                starter = [generate_item(slot, "common") for slot in SLOTS]
                for item in starter:
                    await db.add_item(uid, item)
                    await db.equip_item(uid, ACTIVE_PRESET, item.slot, item.id)
        # Reply after the transaction so the database lock is not held during a network call
        if exists:
            await interaction.response.send_message(
                "You already have a fighter. Try /profile.", ephemeral=True)
            return
        await interaction.response.send_message(
            "Your fighter is ready. Starter gear (already equipped):\n"
            + "\n".join(item_line(i) for i in starter) + "\n\n"
            "Use /profile to see your stats and /inventory to see your items.")

    @app_commands.command(name="profile", description="Show your resources, gear and duel stats")
    async def profile(self, interaction):
        db = self.bot.db
        player = await require_player(interaction, db)
        if player is None:
            return
        gear = await db.get_equipped(interaction.user.id, ACTIVE_PRESET)
        fighter = build_fighter(interaction.user.display_name, gear, player["level"])
        record = await db.duel_record(interaction.user.id)
        await interaction.response.send_message(
            embed=profile_embed(interaction.user, player, gear, fighter, ACTIVE_PRESET, record))


async def setup(bot):
    await bot.add_cog(Profile(bot))