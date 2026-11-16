import asyncio
import time
import traceback

import discord
from discord import app_commands
from discord.ext import commands

from cogs.game._common import require_player
from game.combat import Move
from game.items import build_fighter
from game.live_duel import LiveDuel, Submit
from game.stats import duel_levels
from ui.embeds import challenge_embed, duel_final_embed, duel_round_embed

ACTIVE_PRESET = 1
ROUND_SECONDS = 45          # time to lock in a move; tune in playtests
CHALLENGE_SECONDS = 60      # time for the opponent to accept
MAX_NAME = 20

SUBMIT_MESSAGES = {
    Submit.NOT_PLAYER: "This is not your duel.",
    Submit.LOCKED: "You already locked in a move this round. It is final.",
    Submit.NO_MANA: "Not enough mana for your Skill. Pick Attack or Guard.",
    Submit.OVER: "This duel is over.",
}


class ChallengeView(discord.ui.View):
    """Accept and Decline buttons shown to the challenged player."""

    def __init__(self, challenger_id: int, opponent_id: int):
        super().__init__(timeout=CHALLENGE_SECONDS)
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.accepted = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in (self.challenger_id, self.opponent_id):
            return True
        await interaction.response.send_message("This challenge is not for you.", ephemeral=True)
        return False

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message(
                "Only the challenged player can accept.", ephemeral=True)
            return
        self.accepted = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()      # either player can end the challenge
        self.stop()


class RoundView(discord.ui.View):
    """The three move buttons. Clicks are answered privately, so moves stay hidden."""

    def __init__(self, runner: "DuelRunner"):
        super().__init__(timeout=None)          # the round timer lives in DuelRunner.run()
        self.runner = runner

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in self.runner.live.fighters:
            return True
        await interaction.response.send_message("This is not your duel.", ephemeral=True)
        return False

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger)
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.runner.submit(interaction, Move.ATTACK)

    @discord.ui.button(label="Guard", style=discord.ButtonStyle.primary)
    async def guard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.runner.submit(interaction, Move.GUARD)

    @discord.ui.button(label="Skill", style=discord.ButtonStyle.success)
    async def skill(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.runner.submit(interaction, Move.SKILL)


class DuelRunner:
    """Runs one accepted duel round by round, editing a single public message."""

    def __init__(self, bot, interaction: discord.Interaction, live: LiveDuel):
        self.bot = bot
        self.interaction = interaction          # the original /duel interaction
        self.live = live
        self.round_done = asyncio.Event()       # set when both players have locked in
        self.deadline = 0
        self.edit_lock = asyncio.Lock()

    async def edit(self, **kwargs):
        async with self.edit_lock:
            await self.interaction.edit_original_response(content=None, **kwargs)

    async def submit(self, interaction: discord.Interaction, move: Move):
        round_no = self.live.duel.round
        status = self.live.submit(interaction.user.id, move)
        if status is not Submit.OK:
            await interaction.response.send_message(SUBMIT_MESSAGES[status], ephemeral=True)
            return
        # The reply is private (ephemeral), so the opponent never sees the move
        await interaction.response.send_message(
            f"You chose {move.value.title()}. It is final.", ephemeral=True)
        if self.live.ready:
            self.round_done.set()               # run() resolves the round and edits the message
            return
        async with self.edit_lock:
            # Skip if the round moved on while we waited for the lock
            if self.live.duel.round == round_no and not self.live.ready:
                await self.interaction.edit_original_response(
                    content=None, embed=duel_round_embed(self.live, self.deadline))

    async def run(self):
        live = self.live
        while not live.finished:
            self.round_done.clear()
            self.deadline = int(time.time()) + ROUND_SECONDS
            view = RoundView(self)
            await self.edit(embed=duel_round_embed(live, self.deadline), view=view)
            try:
                await asyncio.wait_for(self.round_done.wait(), ROUND_SECONDS)
            except asyncio.TimeoutError:
                pass                            # missing players play a default Guard
            view.stop()
            live.resolve()
        await self.finish()

    async def finish(self):
        live, db = self.live, self.bot.db
        a, b = live.ids
        winner_id = live.winner_id()
        saved, record_line = True, None
        try:
            async with db.transaction():
                await db.add_duel("live", a, b, winner_id, live.duel.round,
                                  live.duel.seed, live.log_json())
            wins, losses, draws = await db.duel_record(a, opponent_id=b)
            record_line = f"{live.name_of(a)} {wins} - {losses} {live.name_of(b)}"
            if draws:
                record_line += f" ({draws} draws)"
        except Exception:
            saved = False                       # still show the result to the players
            traceback.print_exc()
        await self.edit(embed=duel_final_embed(live, winner_id, record_line, saved), view=None)


class Duel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.busy: set[int] = set()             # players in a challenge or a duel

    @app_commands.command(name="duel", description="Challenge another player to a duel")
    @app_commands.describe(
        opponent="The player to fight",
        real_levels="Fight at your real levels instead of the average of both")
    @app_commands.guild_only()
    async def duel(self, interaction: discord.Interaction, opponent: discord.Member,
                   real_levels: bool = False):
        db, me = self.bot.db, interaction.user
        if await require_player(interaction, db) is None:
            return
        problem = None
        if opponent.bot:
            problem = "You cannot duel a bot."
        elif opponent.id == me.id:
            problem = "You cannot duel yourself."
        elif await db.get_player(opponent.id) is None:
            problem = f"{opponent.display_name} has not started yet. They need to use /start."
        elif me.id in self.busy or opponent.id in self.busy:
            problem = "One of you is already in a duel or has a challenge open."
        if problem:
            await interaction.response.send_message(problem, ephemeral=True)
            return
        # No await between the busy check above and this line, so two commands cannot both pass
        self.busy.update((me.id, opponent.id))
        try:
            await self.run_challenge(interaction, me, opponent, real_levels)
        finally:
            self.busy.discard(me.id)
            self.busy.discard(opponent.id)

    async def run_challenge(self, interaction, me, opponent, real_levels=False):
        view = ChallengeView(me.id, opponent.id)
        await interaction.response.send_message(
            content=opponent.mention,
            embed=challenge_embed(me.display_name, opponent.display_name, CHALLENGE_SECONDS,
                                   real_levels),
            view=view)
        timed_out = await view.wait()
        if not view.accepted:
            text = "The challenge expired." if timed_out else "The challenge was declined."
            await interaction.edit_original_response(content=text, embed=None, view=None)
            return
        rows = [await self.bot.db.get_player(u.id) for u in (me, opponent)]
        levels = duel_levels(rows[0]["level"], rows[1]["level"], real_levels)
        fighters = []
        for user, level in zip((me, opponent), levels):
            gear = await self.bot.db.get_equipped(user.id, ACTIVE_PRESET)
            fighters.append(build_fighter(user.display_name[:MAX_NAME], gear, level))
        live = LiveDuel(me.id, fighters[0], opponent.id, fighters[1])
        await DuelRunner(self.bot, interaction, live).run()


async def setup(bot):
    await bot.add_cog(Duel(bot))
