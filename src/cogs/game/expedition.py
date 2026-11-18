import secrets
import time

import discord
from discord import app_commands
from discord.ext import commands

from src.cogs.game._common import require_player
from src.game.economy import XP_EXPEDITION, XP_PUSH_BONUS
from src.game.loot import (DEFAULT_ZONE, MAX_RUNS, RUN_WINDOW, ZONES, Haul, build_item,
                       next_run_at, roll_haul, roll_push)
from src.ui.embeds import (expedition_result_embed, expedition_started_embed, xp_line,
                       expedition_waiting_embed, haul_embed)

CLAIM_VIEW_SECONDS = 300      # buttons stop working after this; run /scavenge again (the haul stays the same)


async def pay_out(db, user_id: int, haul: Haul):
    """Give a haul to a player. Call it inside a transaction. Returns the saved items."""
    await db.add_currency(user_id, gold=haul.gold, shards=haul.shards, gems=haul.gems)
    items = []
    for spec in haul.items:
        item = build_item(spec)
        await db.add_item(user_id, item)       # gives the item its code
        items.append(item)
    return items


class ClaimView(discord.ui.View):
    """Bank & Leave and Push Deeper. Built fresh by /scavenge, so it does not need to survive a restart."""

    def __init__(self, bot, interaction: discord.Interaction, expedition):
        super().__init__(timeout=CLAIM_VIEW_SECONDS)
        self.bot = bot
        self.interaction = interaction                  # the original /scavenge interaction
        self.user_id = interaction.user.id
        self.expedition_id = expedition["id"]
        self.seed = expedition["seed"]
        self.zone = ZONES[expedition["zone"]]
        self.haul = Haul.from_json(expedition["haul_json"])
        self.used = False                               # a second click while the first runs is ignored

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.user_id:
            return True
        await interaction.response.send_message("This is not your expedition.", ephemeral=True)
        return False

    async def on_timeout(self):
        if self.used:
            return
        try:
            await self.interaction.edit_original_response(
                content="These buttons expired. Use /scavenge again to choose.", view=None)
        except discord.HTTPException:
            pass

    async def finish(self, interaction: discord.Interaction, state: str, haul: Haul | None, xp: int = 0):
        """Settle the expedition in one transaction. Returns (ok, saved items, XP result or None)."""
        db = self.bot.db
        try:
            async with db.transaction():
                ok = await db.finish_expedition(self.expedition_id, state)
                items = await pay_out(db, self.user_id, haul) if ok and haul else []
                gained = await db.grant_xp(self.user_id, xp) if ok and xp else None
        except BaseException:
            self.used = False          # nothing was saved (the transaction rolled back), so let them try again
            raise
        return ok, items, gained

    @discord.ui.button(label="Bank & Leave", style=discord.ButtonStyle.success)
    async def bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.used:
            await interaction.response.send_message("You already made your choice.", ephemeral=True)
            return
        self.used = True
        ok, items, gained = await self.finish(interaction, "claimed", self.haul, XP_EXPEDITION)
        if not ok:
            await interaction.response.send_message("This expedition was already claimed.", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(
            embed=expedition_result_embed("Banked", "You took the haul and headed home.",
                                          self.haul, items, xp_line(XP_EXPEDITION, gained)), view=None)

    @discord.ui.button(label="Push Deeper", style=discord.ButtonStyle.danger)
    async def push(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.used:
            await interaction.response.send_message("You already made your choice.", ephemeral=True)
            return
        self.used = True
        result = roll_push(self.seed, self.zone, self.haul)
        xp = XP_EXPEDITION + XP_PUSH_BONUS if result.success else 0
        ok, items, gained = await self.finish(
            interaction, "claimed" if result.success else "lost", result.haul, xp)
        if not ok:
            await interaction.response.send_message("This expedition was already claimed.", ephemeral=True)
            return
        self.stop()
        if result.success:
            embed = expedition_result_embed(
                "Push Deeper: success!", "You went deeper and came back with more.", result.haul, items,
                xp_line(xp, gained))
        else:
            embed = expedition_result_embed(
                "Push Deeper: lost", "The way collapsed behind you and the whole haul was lost.")
        await interaction.response.edit_message(embed=embed, view=None)


class Expedition(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="scavenge",
        description="Start an expedition, check on it, or collect it when it is back")
    async def scavenge(self, interaction: discord.Interaction):
        """One command for the whole expedition: it starts a run when you have none, shows the
        time left while you are out, and shows the haul with Bank & Leave / Push Deeper once
        you are back."""
        db, uid = self.bot.db, interaction.user.id
        if await require_player(interaction, db) is None:
            return
        zone = ZONES[DEFAULT_ZONE]
        now = int(time.time())
        seed = secrets.randbits(62)
        haul = roll_haul(seed, zone)
        problem, running, runs_left = None, None, 0
        async with db.transaction():
            # Everything is checked and written in one transaction, so two /scavenge commands
            # sent at the same moment cannot both start a run.
            running = await db.get_running_expedition(uid)
            if running is None:
                starts = await db.expedition_starts_since(uid, now - RUN_WINDOW)
                free_at = next_run_at(starts, now)
                if free_at is not None:
                    problem = (f"You used all {MAX_RUNS} expeditions for now. "
                               f"The next one is available <t:{free_at}:R>.")
                elif zone.entry_fee and (await db.get_player(uid))["gold"] < zone.entry_fee:
                    problem = f"You need {zone.entry_fee} gold to enter {zone.name}."
                else:
                    if zone.entry_fee:
                        await db.add_currency(uid, gold=-zone.entry_fee)
                    await db.start_expedition(uid, zone.key, now, now + zone.duration, seed, haul.to_json())
                    runs_left = MAX_RUNS - len(starts) - 1
        # Reply after the transaction so the database lock is not held during a network call
        if running is not None and now >= running["ends_at"]:
            view = ClaimView(self.bot, interaction, running)          # back: choose Bank or Push
            await interaction.response.send_message(
                embed=haul_embed(ZONES[running["zone"]], view.haul), view=view)
        elif running is not None:                                      # still out
            await interaction.response.send_message(
                embed=expedition_waiting_embed(ZONES[running["zone"]].name, running["ends_at"]),
                ephemeral=True)
        elif problem:
            await interaction.response.send_message(problem, ephemeral=True)
        else:
            await interaction.response.send_message(
                embed=expedition_started_embed(zone, now + zone.duration, runs_left))


async def setup(bot):
    await bot.add_cog(Expedition(bot))