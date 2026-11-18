import random
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from cogs.game._common import OwnerView, choose_items, require_player
from game.crafting import CraftingError, check_locks, reroll_affixes, reroll_cost, salvage_value
from ui.embeds import reroll_embed, salvage_confirm_embed, salvage_result_embed


class RerollView(OwnerView):
    """Lock lines, reroll as often as you like, press Done. Locks last until Done."""

    def __init__(self, bot, interaction, item, shards: int, pity: int):
        super().__init__(bot, interaction)
        self.item, self.shards, self.pity = item, shards, pity
        self.locked: set[int] = set()
        for n, button in enumerate((self.lock1, self.lock2, self.lock3)):
            button.disabled = n >= len(item.affixes)          # a Common item has one line, Epic has three
            button.label = f"Lock {n + 1}"

    def embed(self, note=None, before=None):
        return reroll_embed(self.item, self.locked, self.shards, self.pity, note, before)

    async def toggle(self, interaction, index: int):
        wanted = self.locked ^ {index}
        try:
            check_locks(self.item, wanted)
        except CraftingError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        self.locked = wanted
        for n, button in enumerate((self.lock1, self.lock2, self.lock3)):
            button.style = discord.ButtonStyle.primary if n in self.locked else discord.ButtonStyle.secondary
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Lock 1", style=discord.ButtonStyle.secondary)
    async def lock1(self, interaction, button):
        await self.toggle(interaction, 0)

    @discord.ui.button(label="Lock 2", style=discord.ButtonStyle.secondary)
    async def lock2(self, interaction, button):
        await self.toggle(interaction, 1)

    @discord.ui.button(label="Lock 3", style=discord.ButtonStyle.secondary)
    async def lock3(self, interaction, button):
        await self.toggle(interaction, 2)

    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.success)
    async def reroll(self, interaction, button):
        if self.busy:
            return
        self.busy = True
        db, uid = self.bot.db, self.user_id
        problem = None
        try:
            async with db.transaction():
                # Everything is checked against the database inside the transaction, so a salvage
                # or another reroll sent at the same moment cannot cause a double charge.
                item = await db.get_item(self.item.id)
                player = await db.get_player(uid)
                if item is None or item.owner_id != uid:
                    problem = "That item no longer exists."
                    self.stop()
                else:
                    self.item, self.shards, self.pity = item, player["shards"], player["pity"]
                    cost = reroll_cost(item.rarity, len(self.locked))
                    if player["shards"] < cost:
                        problem = f"You need {cost} shards for this reroll and have {player['shards']}."
                    else:
                        before = [a.describe() for a in item.affixes]
                        result = reroll_affixes(item, self.locked, player["pity"], random.Random())
                        await db.spend_shards(uid, cost)
                        item.affixes = result.affixes
                        await db.save_affixes(item)
                        await db.set_pity(uid, result.pity)
        finally:
            self.busy = False
        if problem:
            await interaction.response.send_message(problem, ephemeral=True)
            return
        self.item, self.shards, self.pity = item, player["shards"] - cost, result.pity
        note = f"Rerolled for {cost} shards."
        if result.forced:
            note += " Pity guarantee used: a T4 or T5 line is in there."
        await interaction.response.edit_message(embed=self.embed(note, before), view=self)

    @discord.ui.button(label="Done", style=discord.ButtonStyle.danger)
    async def done(self, interaction, button):
        self.stop()
        await interaction.response.edit_message(embed=self.embed("Done."), view=None)


class SalvageView(OwnerView):
    def __init__(self, bot, interaction, items):
        super().__init__(bot, interaction)
        self.items = items
        self.used = False

    @discord.ui.button(label="Salvage", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        if self.used:
            await interaction.response.send_message("Already done.", ephemeral=True)
            return
        self.used = True
        db, uid = self.bot.db, self.user_id
        count = shards = 0
        try:
            async with db.transaction():
                equipped = await db.equipped_item_ids(uid)       # may have changed since the screen opened
                for item in self.items:
                    if item.id not in equipped and await db.delete_item(item.id, uid):
                        count += 1
                        shards += salvage_value(item)
                if shards:
                    await db.add_currency(uid, shards=shards)
                total = (await db.get_player(uid))["shards"]
        except BaseException:
            self.used = False
            raise
        self.stop()
        await interaction.response.edit_message(embed=salvage_result_embed(count, shards, total), view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        self.used = True
        self.stop()
        await interaction.response.edit_message(content="Cancelled. Nothing was destroyed.", embed=None, view=None)


class Crafting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reroll", description="Spend Reroll Shards to re-roll an item's affix lines")
    @app_commands.describe(code="The code shown next to the item, like H12")
    async def reroll(self, interaction: discord.Interaction, code: str):
        db, uid = self.bot.db, interaction.user.id
        player = await require_player(interaction, db)
        if player is None:
            return
        item = await db.get_item_by_uid(code)
        if item is None or item.owner_id != uid:
            await interaction.response.send_message("You do not own an item with that code.", ephemeral=True)
            return
        if not item.affixes:
            await interaction.response.send_message("That item has no affix lines to reroll.", ephemeral=True)
            return
        view = RerollView(self.bot, interaction, item, player["shards"], player["pity"])
        await interaction.response.send_message(embed=view.embed(), view=view)

    @app_commands.command(name="salvage", description="Break items down into Reroll Shards")
    @app_commands.describe(code="One item, by its code like H12",
                           rarity="Or every item of this rarity that you have not equipped")
    async def salvage(self, interaction: discord.Interaction, code: Optional[str] = None,
                      rarity: Optional[Literal["common", "rare", "epic"]] = None):
        db = self.bot.db
        if await require_player(interaction, db) is None:
            return
        items = await choose_items(interaction, db, code, rarity, "salvage")
        if items is None:
            return
        view = SalvageView(self.bot, interaction, items)
        await interaction.response.send_message(embed=salvage_confirm_embed(items), view=view)


async def setup(bot):
    await bot.add_cog(Crafting(bot))
