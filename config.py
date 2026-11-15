# Settings. The bot token comes from an environment variable, never from the code.
import os

TOKEN = os.getenv("TOKEN")
PREFIX = "!"
DB_PATH = os.getenv("DB_PATH", "data/game.db")
