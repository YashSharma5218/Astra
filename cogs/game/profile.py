from discord import app_commands
from discord.ext import commands

from cogs.game._common import require_player
from game.items import build_fighter, generate_item
from ui.embeds import item_line, profile_embed

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
                weapon = generate_item("weapon", "common")
                armor = generate_item("armor", "common")
                await db.add_item(uid, weapon)
                await db.add_item(uid, armor)
                await db.equip_item(uid, ACTIVE_PRESET, "weapon", weapon.id)
                await db.equip_item(uid, ACTIVE_PRESET, "armor", armor.id)
        # Reply after the transaction so the database lock is not held during a network call
        if exists:
            await interaction.response.send_message(
                "You already have a fighter. Try /profile.", ephemeral=True)
            return
        await interaction.response.send_message(
            "Your fighter is ready. Starter gear (already equipped):\n"
            f"{item_line(weapon)}\n{item_line(armor)}\n\n"
            "Use /profile to see your stats and /inventory to see your items.")

    @app_commands.command(name="profile", description="Show your resources, gear and duel stats")
    async def profile(self, interaction):
        db = self.bot.db
        player = await require_player(interaction, db)
        if player is None:
            return
        weapon, armor = await db.get_equipped(interaction.user.id, ACTIVE_PRESET)
        fighter = build_fighter(interaction.user.display_name, weapon, armor)
        record = await db.duel_record(interaction.user.id)
        await interaction.response.send_message(
            embed=profile_embed(interaction.user, player, weapon, armor, fighter,
                                ACTIVE_PRESET, record))


async def setup(bot):
    await bot.add_cog(Profile(bot))
