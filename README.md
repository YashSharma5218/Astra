# Astra

A Discord bot game about gear, expeditions and duels. Build a fighter from rerollable equipment, send it out to scavenge for loot, and challenge other players to hidden-move duels.

Built with [discord.py](https://discordpy.readthedocs.io/) and SQLite. Astra is in active development, so numbers and features change often.

## Features

- **Gear with rolled affixes.** Five slots: weapon, helmet, chestplate, leggings and boots. Items come in Common, Rare and Epic, and each has affix lines (crit chance, crit damage, armor penetration, lifesteal, thorns, dodge, strength) rolled at a tier from T1 to T5. Every item has a short code, such as `H12`, that you use to equip or craft it.
- **Hidden-move duels.** Both players secretly pick Attack, Guard or Skill each round, then the moves are revealed together. Attack beats Skill, Skill beats Guard, and Guard beats Attack, with a counter-hit for a well-timed Guard. Your weapon decides your Skill, and Skill costs mana.
- **Timed expeditions.** Send your fighter out, close Discord, and come back to collect. When it returns you can bank the haul or push deeper for more at the risk of losing everything. Expeditions keep counting while the bot is offline.
- **Crafting.** Salvage items into Reroll Shards, then spend shards to reroll an item's affixes. Lock the lines you like to keep them, at a higher cost, and a pity counter guarantees a good roll after enough bad ones.
- **Economy and levels.** Earn gold and XP from expeditions and duels, buy gear from the shop, and sell what you don't need. Levels add to your base stats, and duels are fought at the average of both players' levels unless you choose real levels.
- **Daily backups.** The database is backed up once a day and the newest copies are kept.

## Commands

| Command | What it does |
| --- | --- |
| `/start` | Create your fighter and get your first set of gear |
| `/profile` | Show your level, gear, stats and duel record |
| `/inventory` | List your items, optionally filtered by slot |
| `/equip code` | Equip an item by its code |
| `/duel @player` | Challenge a player to a live duel |
| `/scavenge` | Start an expedition, check on it, or collect it when it is back |
| `/reroll code` | Reroll an item's affix lines, with lock buttons |
| `/salvage` | Break an item, or every unequipped item of a rarity, into Reroll Shards |
| `/shop` | See the shop's prices and what selling pays |
| `/buy slot rarity` | Buy a random item of the slot and rarity you choose |
| `/sell` | Sell an item, or every unequipped item of a rarity, for gold |

Owner-only text commands (the account that owns the bot application):

| Command | What it does |
| --- | --- |
| `!sync` | Publish the slash commands to Discord. Run it after adding or changing commands |
| `!setlevel @user level` | Set a player's level, for testing |
| `!backup` | Make a database backup right now |

## Getting started

### Requirements

- Python 3.10 or newer
- A Discord bot application and its token

### Create the bot

1. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications) and add a bot to it.
2. Under **Bot**, turn on the **Message Content Intent**. It is needed for the `!` owner commands.
3. Invite the bot to your server with the `bot` and `applications.commands` scopes.

### Install

```bash
git clone https://github.com/YashSharma5218/Astra.git
cd Astra
python -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate
pip install discord.py aiosqlite
```

### Configure

The bot reads its settings from environment variables:

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `TOKEN` | yes | none | Your bot token. Never commit it |
| `DB_PATH` | no | `data/game.db` | Where the SQLite database is stored |
| `BACKUP_DIR` | no | `backups` | Where daily backups are written |
| `BACKUP_KEEP` | no | `7` | How many daily backups to keep |

For example, on Linux or macOS:

```bash
export TOKEN="your-bot-token"
```

On Windows PowerShell:

```powershell
$env:TOKEN = "your-bot-token"
```

### Run

From the project root:

```bash
python -m src.main
```

The first time, run `!sync` in your server (as the bot owner) and wait a minute for the slash commands to appear. Then use `/start` to create your fighter.

The database and the `backups/` folder are created automatically. Add `data/` and `backups/` to your `.gitignore` so they are never pushed.

## Terminal playtest

The duel engine has no Discord code in it, so you can try it in the terminal:

```bash
python -m src.play_cli              # play a duel against a bot
python -m src.play_cli --sim 5000   # bot vs bot, prints win rates
```

## Project structure

All code lives in the `src` package, and imports are counted from the project root (for example `from src.game.items import ...`).

```text
src/
├── main.py        # starts the bot, opens the database, loads every cog
├── config.py      # settings read from environment variables
├── play_cli.py    # terminal playtest and simulation
├── core/          # database access, schema and backups
├── game/          # the rules: combat, items, loot, crafting, economy. Pure Python, no discord imports
├── ui/            # the embeds shown to players
└── cogs/          # the Discord commands, kept thin: they call into game/ and core/
    ├── game/      # /start, /profile, /inventory, /equip, /duel, /scavenge, /reroll, /salvage, /shop, /buy, /sell
    └── misc/      # owner commands and the backup task
```

The rules in `src/game/` never touch Discord or the database, so they can be tested and tuned on their own.

## Notes

- All database writes happen inside transactions, so a crash or a double click cannot duplicate or lose items or currency.
- While the game is still taking shape, a change to the database tables may require deleting `data/game.db` once. Delete it only on a test server, because it removes all progress.
- To restore a backup, stop the bot and copy a file from `backups/` over `data/game.db`.

## License

Astra is licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0). If you modify Astra and run it as a service that other people use over a network, such as a public Discord bot, you must make the source code of your modified version available to those users under the same license.
