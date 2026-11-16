import math
from typing import Literal, Optional

from discord import app_commands
from discord.ext import commands

from cogs.game._common import require_player
from game.items import SLOTS
from ui.embeds import PAGE_SIZE, inventory_embed, item_line


class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="inventory", description="List your items")
    @app_commands.describe(slot="Only show one slot", page="Page number")
    async def inventory(self, interaction, slot: Optional[Literal["weapon", "helmet", "chestplate", "leggings", "boots"]] = None,
                        page: int = 1):
        db, uid = self.bot.db, interaction.user.id
        if await require_player(interaction, db) is None:
            return
        items = await db.list_items(uid, slot)
        pages = max(1, math.ceil(len(items) / PAGE_SIZE))
        page = min(max(page, 1), pages)
        shown = items[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]
        equipped = {i.id for i in (await db.get_equipped(uid, 1)).values() if i}
        await interaction.response.send_message(
            embed=inventory_embed(interaction.user, shown, equipped, page, pages, slot))

    @app_commands.command(name="equip", description="Equip an item into a loadout preset")
    @app_commands.describe(code="The code shown next to the item, like H12",
                           preset="Loadout preset, 1 to 3")
    async def equip(self, interaction, code: str, preset: int = 1):
        db, uid = self.bot.db, interaction.user.id
        if await require_player(interaction, db) is None:
            return
        if preset not in (1, 2, 3):
            await interaction.response.send_message("Preset must be 1, 2 or 3.", ephemeral=True)
            return
        item = await db.get_item_by_uid(code)
        if item is None or item.owner_id != uid:
            await interaction.response.send_message(
                "You do not own an item with that code.", ephemeral=True)
            return
        async with db.transaction():
            await db.equip_item(uid, preset, item.slot, item.id)
        await interaction.response.send_message(
            f"Equipped in preset {preset}:\n{item_line(item)}")


async def setup(bot):
    await bot.add_cog(Inventory(bot))
