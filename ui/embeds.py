"""Embed builders: turn game data into Discord embeds. No game rules in here."""
from __future__ import annotations

import discord

from game.combat import ENERGY_CAP, MAX_ROUNDS, SKILL_COST, Fighter, format_round
from game.items import Item
from game.live_duel import LiveDuel

PAGE_SIZE = 8


def item_line(item: Item, equipped: bool = False) -> str:
    tag = " **(equipped)**" if equipped else ""
    return f"`#{item.id}` {item.describe()}{tag}"


def stats_text(f: Fighter) -> str:
    return (
        f"HP {f.max_hp} | ATK {f.attack:g} | DEF {f.defense_reduction:.0%}\n"
        f"Crit {f.crit_chance:.0%} (x{f.crit_mult:.2f}) | Armor Pen {f.armor_pen:.0%}\n"
        f"Dodge {f.dodge:.0%} | Lifesteal {f.lifesteal:.0%} | Thorns {f.thorns:.0%}\n"
        f"Element: {f.element.title()}"
    )


def profile_embed(user: discord.abc.User, player, weapon: Item | None,
                  armor: Item | None, fighter: Fighter, preset: int,
                  record: tuple[int, int, int] = (0, 0, 0)) -> discord.Embed:
    embed = discord.Embed(title=f"{user.display_name}'s fighter")
    embed.add_field(
        name="Resources",
        value=f"Gold {player['gold']} | Shards {player['shards']} | Gems {player['gems']}",
        inline=False)
    embed.add_field(name=f"Weapon (preset {preset})",
                    value=item_line(weapon) if weapon else "Nothing equipped", inline=False)
    embed.add_field(name=f"Armor (preset {preset})",
                    value=item_line(armor) if armor else "Nothing equipped", inline=False)
    embed.add_field(name="Duel stats", value=stats_text(fighter), inline=False)
    wins, losses, draws = record
    embed.add_field(name="Duel record", value=f"Wins {wins} | Losses {losses} | Draws {draws}",
                    inline=False)
    return embed


def inventory_embed(user: discord.abc.User, items: list[Item], equipped_ids: set[int],
                    page: int, pages: int, slot: str | None) -> discord.Embed:
    title = f"{user.display_name}'s inventory"
    if slot:
        title += f" ({slot})"
    embed = discord.Embed(title=title)
    if not items:
        embed.description = "Nothing here yet."
    else:
        embed.description = "\n".join(item_line(i, i.id in equipped_ids) for i in items)
    embed.set_footer(text=f"Page {page} of {pages}  |  /equip item_id to use an item")
    return embed


# ---- duels ----
END_REASONS = {
    "both_idle": "Both players stopped answering, so the duel ended in a draw.",
    "draw": "Equal HP and equal damage dealt after the last round.",
    "ko": "Knockout.",
    "hp": "Higher HP after the last round.",
    "damage": "Equal HP, so the player who dealt more damage wins.",
}


def hp_bar(hp: int, max_hp: int, width: int = 10) -> str:
    hp = max(hp, 0)
    filled = round(width * hp / max_hp) if max_hp else 0
    if hp > 0 and filled == 0:
        filled = 1
    return f"{'█' * filled}{'░' * (width - filled)} {hp}/{max_hp}"


def challenge_embed(challenger: str, opponent: str, seconds: int) -> discord.Embed:
    return discord.Embed(
        title="Duel challenge",
        description=(f"**{challenger}** challenges **{opponent}** to a duel.\n"
                     f"Up to {MAX_ROUNDS} rounds, higher HP wins. Each round you secretly pick "
                     f"Attack, Guard or Skill.\n{opponent} has {seconds} seconds to accept."))


def duel_round_embed(live: LiveDuel, deadline: int) -> discord.Embed:
    """The public message while a round is open. `deadline` is a Unix timestamp."""
    d = live.duel
    a, b = (live.fighters[u] for u in live.ids)
    embed = discord.Embed(
        title=f"{a.name} vs {b.name}",
        description=f"Round {d.round + 1} of {d.max_rounds}  |  Moves lock <t:{deadline}:R>")
    for uid in live.ids:
        f = live.fighters[uid]
        status = "Locked in" if live.is_locked(uid) else "Waiting for a move"
        embed.add_field(
            name=f.name,
            value=f"{hp_bar(f.hp, f.max_hp)}\nEnergy {f.energy}/{ENERGY_CAP} "
                  f"(Skill costs {SKILL_COST})\n{status}",
            inline=True)
    if live.last_result:
        embed.add_field(name=f"Round {live.last_result.number} result",
                        value="\n".join(live.last_result.events), inline=False)
    embed.set_footer(text="Pick a button. Only you can see which move you chose.")
    return embed


def duel_final_embed(live: LiveDuel, winner_id: int | None, record_line: str | None = None,
                     saved: bool = True) -> discord.Embed:
    d = live.duel
    reason = live.end_reason()
    if reason == "forfeit":
        loser = next(iter(live.forfeited))
        text = f"{live.name_of(loser)} stopped answering and forfeited."
    else:
        text = END_REASONS[reason]
    title = "Draw" if winner_id is None else f"{live.name_of(winner_id)} wins!"
    log = "\n\n".join(format_round(r) for r in d.history)
    embed = discord.Embed(title=title, description=f"{text}\n```\n{log[:3500]}\n```")
    for uid in live.ids:
        f = live.fighters[uid]
        embed.add_field(name=f.name, value=hp_bar(f.hp, f.max_hp), inline=True)
    footer = f"Seed {d.seed}"
    if record_line:
        footer += f"  |  {record_line}"
    if not saved:
        footer += "  |  This result could not be saved"
    embed.set_footer(text=footer)
    return embed
