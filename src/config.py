# Settings. The bot token comes from an environment variable, never from the code.
import os
import pathlib

# The project root is the folder that holds src/, data/ and backups/. Data paths hang off it, so
# they are the same wherever the bot is started from.
ROOT = pathlib.Path(__file__).resolve().parent.parent

TOKEN = os.getenv("TOKEN")
PREFIX = "!"
DB_PATH = os.getenv("DB_PATH", str(ROOT / "data" / "game.db"))
BACKUP_DIR = os.getenv("BACKUP_DIR", str(ROOT / "backups"))
BACKUP_KEEP = int(os.getenv("BACKUP_KEEP", "7"))      # how many daily backups to keep