"""Async SQLite access for the game (aiosqlite).

    db = Database("data/game.db")
    await db.connect()          # in the bot's setup_hook; then use self.db in cogs
    async with db.transaction():
        ...                     # everything in here commits together or not at all
"""
from __future__ import annotations

import asyncio
import pathlib
import sqlite3
from contextlib import asynccontextmanager

import aiosqlite

from game.items import SLOTS, Item, make_uid, normalize_uid

SCHEMA_PATH = pathlib.Path(__file__).with_name("schema.sql")
EQUIP_COLUMNS = {slot: f"{slot}_id" for slot in SLOTS}     # whitelist of loadout columns


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
    async def next_seq(self, name: str) -> int:
        """Next number of a named counter (1, 2, 3 ...). Call it inside a transaction."""
        await self.conn.execute(
            "INSERT INTO counters (name, value) VALUES (?, 1) "
            "ON CONFLICT(name) DO UPDATE SET value = value + 1", (name,))
        cur = await self.conn.execute("SELECT value FROM counters WHERE name = ?", (name,))
        return (await cur.fetchone())[0]

    async def add_item(self, owner_id: int, item: Item) -> int:
        """Save a new item. It gets the next code of its slot, like H12 (counted per slot)."""
        item.uid = make_uid(item.slot, await self.next_seq(f"item_{item.slot}"))
        cur = await self.conn.execute(
            "INSERT INTO items (uid, owner_id, slot, rarity, element, base_json, affix_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (item.uid, owner_id, item.slot, item.rarity, item.element,
             item.base_json(), item.affix_json()))
        item.id, item.owner_id = cur.lastrowid, owner_id
        return item.id

    async def get_item_by_uid(self, uid: str) -> Item | None:
        cur = await self.conn.execute("SELECT * FROM items WHERE uid = ?", (normalize_uid(uid),))
        row = await cur.fetchone()
        return Item.from_row(row) if row else None

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

    async def delete_item(self, item_id: int, owner_id: int) -> bool:
        """Delete an item the player owns. False if it was already gone. Equipped items must be
        checked by the caller first (see equipped_item_ids), because loadouts point at them."""
        cur = await self.conn.execute("DELETE FROM items WHERE id = ? AND owner_id = ?", (item_id, owner_id))
        return cur.rowcount == 1

    async def spend_shards(self, user_id: int, amount: int) -> bool:
        """Take shards if the player has enough. False (and nothing changes) otherwise."""
        cur = await self.conn.execute(
            "UPDATE players SET shards = shards - ? WHERE user_id = ? AND shards >= ?",
            (amount, user_id, amount))
        return cur.rowcount == 1

    async def set_pity(self, user_id: int, pity: int) -> None:
        await self.conn.execute("UPDATE players SET pity = ? WHERE user_id = ?", (pity, user_id))

    # ---- loadouts ----
    async def equipped_item_ids(self, user_id: int) -> set[int]:
        """Ids of every item the player has in any of their presets."""
        cols = ", ".join(EQUIP_COLUMNS[slot] for slot in SLOTS)
        cur = await self.conn.execute(f"SELECT {cols} FROM loadouts WHERE user_id = ?", (user_id,))
        return {v for row in await cur.fetchall() for v in tuple(row) if v}

    async def set_loadout(self, user_id: int, preset: int, item_ids: dict[str, int | None] | None = None,
                          disposition: str = "balanced") -> None:
        """Replace a whole preset. `item_ids` maps slot -> item id; missing slots become empty."""
        item_ids = item_ids or {}
        cols = ", ".join(EQUIP_COLUMNS[slot] for slot in SLOTS)
        marks = ", ".join("?" for _ in SLOTS)
        sets = ", ".join(f"{EQUIP_COLUMNS[slot]} = excluded.{EQUIP_COLUMNS[slot]}" for slot in SLOTS)
        await self.conn.execute(
            f"INSERT INTO loadouts (user_id, preset, {cols}, disposition) "
            f"VALUES (?, ?, {marks}, ?) ON CONFLICT(user_id, preset) DO UPDATE SET "
            f"{sets}, disposition = excluded.disposition",
            (user_id, preset, *(item_ids.get(slot) for slot in SLOTS), disposition))

    async def equip_item(self, user_id: int, preset: int, slot: str, item_id: int) -> None:
        """Put one item into a preset's slot without touching the other slots."""
        column = EQUIP_COLUMNS[slot]      # KeyError for an unknown slot
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

    async def get_equipped(self, user_id: int, preset: int = 1) -> dict[str, Item | None]:
        """Return {slot: Item or None} for every slot of a preset."""
        lo = await self.get_loadout(user_id, preset)
        gear: dict[str, Item | None] = {}
        for slot in SLOTS:
            item_id = lo[EQUIP_COLUMNS[slot]] if lo else None
            gear[slot] = await self.get_item(item_id) if item_id else None
        return gear

    # ---- expeditions ----
    async def start_expedition(self, user_id: int, zone: str, started_at: int, ends_at: int,
                               seed: int, haul_json: str) -> int | None:
        """Start a run. Returns its id, or None if the player already has an unclaimed one."""
        try:
            cur = await self.conn.execute(
                "INSERT INTO expeditions (user_id, zone, started_at, ends_at, seed, haul_json) "
                "VALUES (?, ?, ?, ?, ?, ?)", (user_id, zone, started_at, ends_at, seed, haul_json))
        except sqlite3.IntegrityError:
            return None
        return cur.lastrowid

    async def expedition_starts_since(self, user_id: int, since: int) -> list[int]:
        """Start times (oldest first) of all the player's expeditions that started after `since`,
        whatever happened to them. Used for the runs-per-day limit."""
        cur = await self.conn.execute(
            "SELECT started_at FROM expeditions WHERE user_id = ? AND started_at > ? ORDER BY started_at",
            (user_id, since))
        return [r[0] for r in await cur.fetchall()]

    async def get_running_expedition(self, user_id: int):
        """The player's unclaimed expedition (running or ready), or None."""
        cur = await self.conn.execute(
            "SELECT * FROM expeditions WHERE user_id = ? AND state = 'running'", (user_id,))
        return await cur.fetchone()

    async def finish_expedition(self, expedition_id: int, state: str) -> bool:
        """Mark a running expedition 'claimed' or 'lost'. False if it was already finished,
        which is what stops a double click from paying out twice."""
        cur = await self.conn.execute(
            "UPDATE expeditions SET state = ? WHERE id = ? AND state = 'running'",
            (state, expedition_id))
        return cur.rowcount == 1

    # ---- levels ----
    async def set_level(self, user_id: int, level: int, xp: int = 0) -> None:
        await self.conn.execute("UPDATE players SET level = ?, xp = ? WHERE user_id = ?",
                                (level, xp, user_id))
