from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from cogs.game._common import OwnerView, choose_items, require_player
from game.economy import sell_value, shop_price
from game.items import generate_item
from ui.embeds import item_line, sell_confirm_embed, sell_result_embed, shop_embed


class SellView(OwnerView):
    def __init__(self, bot, interaction, items):
        super().__init__(bot, interaction)
        self.items = items
        self.used = False

    @discord.ui.button(label="Sell", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        if self.used:
            await interaction.response.send_message("Already done.", ephemeral=True)
            return
        self.used = True
        db, uid = self.bot.db, self.user_id
        count = gold = 0
        try:
            async with db.transaction():
                equipped = await db.equipped_item_ids(uid)       # may have changed since the screen opened
                for item in self.items:
                    if item.id not in equipped and await db.delete_item(item.id, uid):
                        count += 1
                        gold += sell_value(item)
                if gold:
                    await db.add_currency(uid, gold=gold)
                total = (await db.get_player(uid))["gold"]
        except BaseException:
            self.used = False
            raise
        self.stop()
        await interaction.response.edit_message(embed=sell_result_embed(count, gold, total), view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        self.used = True
        self.stop()
        await interaction.response.edit_message(content="Cancelled. Nothing was sold.", embed=None, view=None)


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shop", description="See what the shop sells and what selling pays")
    async def shop(self, interaction: discord.Interaction):
        player = await require_player(interaction, self.bot.db)
        if player is None:
            return
        await interaction.response.send_message(embed=shop_embed(player["gold"]), ephemeral=True)

    @app_commands.command(name="buy", description="Buy a random item of the slot and rarity you choose")
    @app_commands.describe(slot="Which piece of gear", rarity="Common or Rare (Epic is not for sale)")
    async def buy(self, interaction: discord.Interaction,
                  slot: Literal["weapon", "helmet", "chestplate", "leggings", "boots"],
                  rarity: Literal["common", "rare"]):
        db, uid = self.bot.db, interaction.user.id
        if await require_player(interaction, db) is None:
            return
        price = shop_price(rarity)
        if price is None:                                   # also guards against a hand-made request
            await interaction.response.send_message("The shop does not sell that rarity.", ephemeral=True)
            return
        item = generate_item(slot, rarity)
        async with db.transaction():
            paid = await db.spend_gold(uid, price)
            if paid:
                await db.add_item(uid, item)                # gives the item its code
            gold = (await db.get_player(uid))["gold"]
        if not paid:
            await interaction.response.send_message(
                f"A {rarity} {slot} costs {price} gold and you have {gold}.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"Bought for {price} gold ({gold} left):\n{item_line(item)}")

    @app_commands.command(name="sell", description="Sell items for gold")
    @app_commands.describe(code="One item, by its code like H12",
                           rarity="Or every item of this rarity that you have not equipped")
    async def sell(self, interaction: discord.Interaction, code: Optional[str] = None,
                   rarity: Optional[Literal["common", "rare", "epic"]] = None):
        db = self.bot.db
        if await require_player(interaction, db) is None:
            return
        items = await choose_items(interaction, db, code, rarity, "sell")
        if items is None:
            return
        view = SellView(self.bot, interaction, items)
        await interaction.response.send_message(embed=sell_confirm_embed(items), view=view)


async def setup(bot):
    await bot.add_cog(Shop(bot))
