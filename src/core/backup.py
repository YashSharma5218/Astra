"""Daily database backups: one file per day in the backups folder, newest few kept.

    path = await run_backup(db, "backups", keep=7)      # None when today's backup already exists

A backup is a consistent snapshot made with SQLite's VACUUM INTO, so it includes recent writes
that still sit in the WAL file (copying game.db by hand would miss them). It runs while holding
the database lock, so it never sees half of a transaction. To restore: stop the bot and copy a
backup over data/game.db.
"""
from __future__ import annotations

import os
import pathlib
import re
from datetime import date

NAME_RE = re.compile(r"^game-(\d{4}-\d{2}-\d{2})\.db$")


def backup_path(directory: str | os.PathLike, day: date) -> pathlib.Path:
    return pathlib.Path(directory) / f"game-{day:%Y-%m-%d}.db"


def prune_backups(directory: str | os.PathLike, keep: int) -> list[pathlib.Path]:
    """Delete the oldest backups so only `keep` remain. Files with other names are never touched."""
    files = sorted(p for p in pathlib.Path(directory).glob("game-*.db") if NAME_RE.match(p.name))
    removed = files[:-keep] if keep > 0 else []
    for p in removed:
        p.unlink()
    return removed


async def run_backup(db, directory: str | os.PathLike, keep: int = 7, day: date | None = None,
                     force: bool = False) -> pathlib.Path | None:
    """Make today's backup unless it exists already (force=True replaces it). Returns the file
    path, or None when nothing was done. Old backups beyond `keep` are deleted afterwards."""
    final = backup_path(directory, day or date.today())
    if final.exists() and not force:
        return None
    final.parent.mkdir(parents=True, exist_ok=True)
    temp = final.with_name(final.name + ".tmp")        # a crash mid-write never leaves a broken "today" file
    temp.unlink(missing_ok=True)
    await db.backup_to(str(temp))
    os.replace(temp, final)
    prune_backups(directory, keep)
    return final
