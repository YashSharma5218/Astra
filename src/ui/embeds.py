"""Embed builders: turn game data into Discord embeds. No game rules in here."""
from __future__ import annotations

import discord

from src.game.combat import MAX_ROUNDS, Fighter, format_round
from src.game.crafting import LOCK_COST_MULT, reroll_cost, salvage_value
from src.game.economy import SELL_GOLD, SHOP_PRICE, sell_value
from src.game.items import PITY_THRESHOLD, SLOTS, Item
from src.game.live_duel import LiveDuel
from src.game.loot import MAX_RUNS, PUSH_CHANCE, Haul, Zone, build_item
from src.game.stats import xp_to_next

PAGE_SIZE = 8


def item_line(item: Item, equipped: bool = False) -> str:
    tag = " **(equipped)**" if equipped else ""
    return f"`{item.uid}` {item.describe()}{tag}"


def stats_text(f: Fighter) -> str:
    return (
        f"HP {f.max_hp} | Mana {f.max_mana} | ATK {f.attack:g} | STR {f.strength:g}\n"
        f"DEF {f.defense:g} ({f.defense_reduction:.0%}) | Crit {f.crit_chance:.0%} (x{f.crit_mult:.2f}) "
        f"| Armor Pen {f.armor_pen:.0%}\n"
        f"Dodge {f.dodge:.0%} | Lifesteal {f.lifesteal:.0%} | Thorns {f.thorns:.0%}\n"
        f"Element: {f.element.title()} | Skill: {f.skill_name} ({f.skill_cost} mana)"
    )


def profile_embed(user: discord.abc.User, player, gear: dict[str, Item | None],
                  fighter: Fighter, preset: int,
                  record: tuple[int, int, int] = (0, 0, 0)) -> discord.Embed:
    embed = discord.Embed(title=f"{user.display_name}'s fighter")
    embed.add_field(
        name="Level",
        value=f"Level {player['level']} | XP {player['xp']}/{xp_to_next(player['level'])}",
        inline=False)
    embed.add_field(
        name="Resources",
        value=f"Gold {player['gold']} | Shards {player['shards']} | Gems {player['gems']}",
        inline=False)
    lines = [f"**{slot.title()}:** " + (item_line(gear[slot]) if gear.get(slot) else "empty")
             for slot in SLOTS]
    embed.add_field(name=f"Gear (preset {preset})", value="\n".join(lines), inline=False)
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
    embed.set_footer(text=f"Page {page} of {pages}  |  /equip code to use an item")
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


def challenge_embed(challenger: str, opponent: str, seconds: int,
                    real_levels: bool = False) -> discord.Embed:
    levels = ("Both fight at their real levels." if real_levels
              else "Both fight at the average of their two levels.")
    return discord.Embed(
        title="Duel challenge",
        description=(f"**{challenger}** challenges **{opponent}** to a duel.\n"
                     f"Up to {MAX_ROUNDS} rounds, higher HP wins. Each round you secretly pick "
                     f"Attack, Guard or Skill. {levels}\n{opponent} has {seconds} seconds to accept."))


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
            name=f"{f.name} (Lv {f.level})",
            value=f"{hp_bar(f.hp, f.max_hp)}\nMana {f.mana}/{f.max_mana} "
                  f"({f.skill_name} costs {f.skill_cost})\n{status}",
            inline=True)
    if live.last_result:
        embed.add_field(name=f"Round {live.last_result.number} result",
                        value="\n".join(live.last_result.events), inline=False)
    embed.set_footer(text="Pick a button. Only you can see which move you chose.")
    return embed


def duel_final_embed(live: LiveDuel, winner_id: int | None, record_line: str | None = None,
                     saved: bool = True, xp_lines: list[str] | None = None) -> discord.Embed:
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
    if xp_lines:
        embed.add_field(name="Experience", value="\n".join(xp_lines), inline=False)
    footer = f"Seed {d.seed}"
    if record_line:
        footer += f"  |  {record_line}"
    if not saved:
        footer += "  |  This result could not be saved"
    embed.set_footer(text=footer)
    return embed


# ---- expeditions ----
def haul_lines(haul: Haul, items: list[Item] | None = None) -> str:
    """Gold, shards, gems and items of a haul. Pass saved `items` to show their codes."""
    lines = [f"Gold {haul.gold} | Shards {haul.shards}" + (f" | Gems {haul.gems}" if haul.gems else "")]
    if items is not None:
        lines += [item_line(i) for i in items]
    else:                                        # not saved yet, so there is no code to show
        lines += [build_item(spec).describe() for spec in haul.items]
    return "\n".join(lines)


def expedition_started_embed(zone: Zone, ends_at: int, runs_left: int | None = None) -> discord.Embed:
    text = (f"Your fighter heads out and will be back <t:{ends_at}:R>.\n"
            "Use /scavenge again when time is up to collect it. You can close Discord in the meantime.")
    if runs_left is not None:
        text += f"\nExpeditions left in this 24 hours: {runs_left} of {MAX_RUNS}."
    return discord.Embed(title=f"Expedition: {zone.name}", description=text)


def expedition_waiting_embed(zone_name: str, ends_at: int) -> discord.Embed:
    return discord.Embed(
        title=f"Expedition: {zone_name}",
        description=f"Your expedition is still out and will be back <t:{ends_at}:R>.")


def haul_embed(zone: Zone, haul: Haul) -> discord.Embed:
    """What the expedition found, shown before the player chooses Bank or Push."""
    embed = discord.Embed(
        title=f"Expedition back: {zone.name}",
        description=("**Bank & Leave** keeps this haul.\n"
                     f"**Push Deeper** is a gamble: {PUSH_CHANCE:.0%} to double the gold and shards, "
                     f"keep all your items, and add a bonus item from a better table plus a chance "
                     f"at a Socket Gem. Otherwise you lose everything."))
    embed.add_field(name="Your haul", value=haul_lines(haul), inline=False)
    return embed


def xp_line(gain: int, result: tuple[int, int, int] | None) -> str | None:
    """'+30 XP' plus a level-up note. `result` is what db.grant_xp returned."""
    if not gain or result is None:
        return None
    level, _, levels_gained = result
    line = f"+{gain} XP"
    if levels_gained:
        line += f" | Level up! You are now level {level}."
    return line


def expedition_result_embed(title: str, text: str, haul: Haul | None = None,
                            items: list[Item] | None = None, xp_note: str | None = None) -> discord.Embed:
    embed = discord.Embed(title=title, description=text)
    if haul is not None:
        embed.add_field(name="Added to your account", value=haul_lines(haul, items), inline=False)
    if xp_note:
        embed.add_field(name="Experience", value=xp_note, inline=False)
    return embed


# ---- crafting ----
def reroll_embed(item: Item, locked: set[int], shards: int, pity: int,
                 note: str | None = None, before: list[str] | None = None) -> discord.Embed:
    """The reroll screen: base line, numbered affix lines with locks, cost, shards and pity."""
    head = item.describe().split(" | ")[0]
    embed = discord.Embed(
        title=f"Reroll {item.uid}",
        description=note or ("Lock the lines you want to keep, then press Reroll. "
                             f"Each lock multiplies the cost by {LOCK_COST_MULT}."))
    embed.add_field(name=head, value="\n".join(
        f"{n}. {a.describe()}" + (" (locked)" if n - 1 in locked else "")
        for n, a in enumerate(item.affixes, 1)), inline=False)
    if before:
        embed.add_field(name="Before", value="\n".join(before), inline=False)
    embed.add_field(name="Next reroll", value=f"{reroll_cost(item.rarity, len(locked))} shards (you have {shards})")
    embed.set_footer(text=f"Pity {pity}/{PITY_THRESHOLD}: after {PITY_THRESHOLD} rerolls without a T4 or T5 line, "
                     "the next reroll is guaranteed one.")
    return embed


def salvage_confirm_embed(items: list[Item]) -> discord.Embed:
    total = sum(salvage_value(i) for i in items)
    shown = [item_line(i) for i in items[:10]]
    if len(items) > 10:
        shown.append(f"... and {len(items) - 10} more")
    embed = discord.Embed(
        title=f"Salvage {len(items)} item{'s' if len(items) != 1 else ''}?",
        description=f"They are destroyed for good and give **{total} shards**.")
    embed.add_field(name="Items", value="\n".join(shown), inline=False)
    return embed


def salvage_result_embed(count: int, shards: int, total_shards: int) -> discord.Embed:
    return discord.Embed(
        title="Salvaged",
        description=f"Destroyed {count} item{'s' if count != 1 else ''} for **{shards} shards**. "
                    f"You now have {total_shards} shards.")


# ---- shop ----
def shop_embed(gold: int) -> discord.Embed:
    embed = discord.Embed(
        title="Shop",
        description=f"You have **{gold} gold**. `/buy slot rarity` gives one random item of that slot, "
                    "with random affixes.")
    embed.add_field(name="For sale", value="\n".join(
        [f"{r.title()}: {p} gold" for r, p in SHOP_PRICE.items()]
        + ["Epic: not for sale, you have to earn it on expeditions"]), inline=False)
    embed.add_field(name="`/sell` pays", value="\n".join(
        f"{r.title()}: {g} gold" for r, g in SELL_GOLD.items()), inline=False)
    return embed


def sell_confirm_embed(items: list[Item]) -> discord.Embed:
    total = sum(sell_value(i) for i in items)
    shown = [item_line(i) for i in items[:10]]
    if len(items) > 10:
        shown.append(f"... and {len(items) - 10} more")
    embed = discord.Embed(
        title=f"Sell {len(items)} item{'s' if len(items) != 1 else ''}?",
        description=f"They are gone for good and pay **{total} gold**.")
    embed.add_field(name="Items", value="\n".join(shown), inline=False)
    return embed


def sell_result_embed(count: int, gold: int, total_gold: int) -> discord.Embed:
    return discord.Embed(
        title="Sold",
        description=f"Sold {count} item{'s' if count != 1 else ''} for **{gold} gold**. "
                    f"You now have {total_gold} gold.")