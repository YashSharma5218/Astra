"""Async SQLite access for the game (aiosqlite).

    db = Database("data/game.db")
    await db.connect()          # in the bot's setup_hook; then use self.db in cogs
    async with db.transaction():
        ...                     # everything in here commits together or not at all
"""
from __future__ import annotations

import asyncio
import pathlib
from contextlib import asynccontextmanager

import aiosqlite

from game.items import Item

SCHEMA_PATH = pathlib.Path(__file__).with_name("schema.sql")
EQUIP_COLUMNS = {"weapon": "weapon_id", "armor": "armor_id"}   # whitelist: spell, relic later


class Database:
    def __init__(self, path: str = "data/game.db"):
        self.path = path
        self.conn: aiosqlite.Connection | None = None
        # One connection is shared by every command, so transactions must not overlap.
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        pathlib.Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: we control BEGIN/COMMIT ourselves in transaction()
        self.conn = await aiosqlite.connect(self.path, isolation_level=None)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.execute("PRAGMA journal_mode = WAL")
        await self.conn.executescript(SCHEMA_PATH.read_text())

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()
            self.conn = None

    @asynccontextmanager
    async def transaction(self):
        """Commit on success, roll back on any error.

        Put every WRITE inside one of these (rerolls, claims, wagers, starter gear).
        A lock makes concurrent commands take turns, so two players using commands
        at the same moment cannot interleave inside each other's transaction.
        """
        async with self._lock:
            await self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield self.conn
            except BaseException:
                await self.conn.execute("ROLLBACK")
                raise
            else:
                await self.conn.execute("COMMIT")

    # ---- players ----
    async def ensure_player(self, user_id: int):
        await self.conn.execute("INSERT OR IGNORE INTO players (user_id) VALUES (?)", (user_id,))
        return await self.get_player(user_id)

    async def get_player(self, user_id: int):
        cur = await self.conn.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
        return await cur.fetchone()

    async def add_currency(self, user_id: int, gold: int = 0, shards: int = 0, gems: int = 0) -> None:
        """Add (or subtract) currency. The CHECK constraints make overspending raise an error."""
        await self.conn.execute(
            "UPDATE players SET gold = gold + ?, shards = shards + ?, gems = gems + ? "
            "WHERE user_id = ?", (gold, shards, gems, user_id))

    # ---- items ----
    async def add_item(self, owner_id: int, item: Item) -> int:
        cur = await self.conn.execute(
            "INSERT INTO items (owner_id, slot, rarity, element, base_json, affix_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (owner_id, item.slot, item.rarity, item.element, item.base_json(), item.affix_json()))
        item.id, item.owner_id = cur.lastrowid, owner_id
        return item.id

    async def get_item(self, item_id: int) -> Item | None:
        cur = await self.conn.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        row = await cur.fetchone()
        return Item.from_row(row) if row else None

    async def list_items(self, owner_id: int, slot: str | None = None) -> list[Item]:
        sql, args = "SELECT * FROM items WHERE owner_id = ?", [owner_id]
        if slot:
            sql, args = sql + " AND slot = ?", args + [slot]
        cur = await self.conn.execute(sql + " ORDER BY id", args)
        return [Item.from_row(r) for r in await cur.fetchall()]

    async def save_affixes(self, item: Item) -> None:
        await self.conn.execute("UPDATE items SET affix_json = ? WHERE id = ?",
                                (item.affix_json(), item.id))

    # ---- loadouts ----
    async def set_loadout(self, user_id: int, preset: int, weapon_id: int | None = None,
                          armor_id: int | None = None, disposition: str = "balanced") -> None:
        await self.conn.execute(
            "INSERT INTO loadouts (user_id, preset, weapon_id, armor_id, disposition) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id, preset) DO UPDATE SET "
            "weapon_id = excluded.weapon_id, armor_id = excluded.armor_id, "
            "disposition = excluded.disposition",
            (user_id, preset, weapon_id, armor_id, disposition))

    async def equip_item(self, user_id: int, preset: int, slot: str, item_id: int) -> None:
        """Put one item into a preset's slot without touching the other slots."""
        column = EQUIP_COLUMNS[slot]      # KeyError for slots that are not in version 1
        await self.conn.execute(
            "INSERT OR IGNORE INTO loadouts (user_id, preset) VALUES (?, ?)", (user_id, preset))
        await self.conn.execute(
            f"UPDATE loadouts SET {column} = ? WHERE user_id = ? AND preset = ?",
            (item_id, user_id, preset))

    async def get_loadout(self, user_id: int, preset: int):
        cur = await self.conn.execute(
            "SELECT * FROM loadouts WHERE user_id = ? AND preset = ?", (user_id, preset))
        return await cur.fetchone()

    # ---- duels ----
    async def add_duel(self, mode: str, player_a: int, player_b: int, winner_id: int | None,
                       rounds: int, seed: int, log_json: str) -> int:
        cur = await self.conn.execute(
            "INSERT INTO duels (mode, player_a, player_b, winner_id, rounds, seed, log_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (mode, player_a, player_b, winner_id, rounds, seed, log_json))
        return cur.lastrowid

    async def duel_record(self, user_id: int, opponent_id: int | None = None,
                          mode: str = "live") -> tuple[int, int, int]:
        """Return (wins, losses, draws) of a player, optionally against one opponent."""
        sql = ("SELECT COALESCE(SUM(winner_id = ?), 0), "
               "COALESCE(SUM(winner_id IS NOT NULL AND winner_id != ?), 0), "
               "COALESCE(SUM(winner_id IS NULL), 0) FROM duels WHERE mode = ?")
        args: list = [user_id, user_id, mode]
        if opponent_id is None:
            sql += " AND (player_a = ? OR player_b = ?)"
            args += [user_id, user_id]
        else:
            sql += " AND ((player_a = ? AND player_b = ?) OR (player_a = ? AND player_b = ?))"
            args += [user_id, opponent_id, opponent_id, user_id]
        cur = await self.conn.execute(sql, args)
        wins, losses, draws = await cur.fetchone()
        return wins, losses, draws

    async def get_equipped(self, user_id: int, preset: int = 1) -> tuple[Item | None, Item | None]:
        """Return (weapon, armor) of a preset; either can be None if the slot is empty."""
        lo = await self.get_loadout(user_id, preset)
        if lo is None:
            return None, None
        weapon = await self.get_item(lo["weapon_id"]) if lo["weapon_id"] else None
        armor = await self.get_item(lo["armor_id"]) if lo["armor_id"] else None
        return weapon, armor
