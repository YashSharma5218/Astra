# Technical Plan

Nov 14, 2026 · @Yash

## Build status

Updated 2026-11-16. The code is written and tested with stand-in objects, since `discord.py` and `aiosqlite` were not installed where it was built, so every Discord-facing piece still needs a first real run.

| Piece | Status |
| --- | --- |
| Combat engine (`game/combat.py`) | Written and tested with the tuned rules from the Combat Spec: Guard counter, 70% block, 56% block against a Skill, Skill cut to 45% by an Attack, no crits on guarded hits, 30% base crit, new caps. Skill is now the weapon's ability and costs mana (placeholder numbers: start 30, +30 a round, +30 for Guard, Skill 60, cap 100). Strength is a percent attack bonus |
| Terminal playtest (`play_cli.py`) | Done: play against a bot, or run bot-vs-bot simulations |
| Item generation (`game/items.py`) | Done for weapon and armor, Common to Epic, T1 to T5 affixes, and every item now gets a unique public code. Affix values are the tuned T5 values (T1 is about 16% of T5). Strength and Elemental DMG are not rolled yet, and the five slots are in: weapon, helmet, chestplate, leggings, boots. Numbers are on the hundreds scale: each armor piece has its own base HP and defense (a Common set is 400 HP and 75 defense), weapons hit for 100 to 140, and the weapon carries its Skill |
| Database layer and schema (`core/`) | Written and tested against a stand-in. Now also saves duels and counts wins, losses and draws |
| `/start`, `/profile`, `/inventory`, `/equip`, `!sync` | Written. `/profile` now shows the duel record, and /equip takes the item's code. /start now gives a common weapon plus four armor pieces, and the owner-only !setlevel sets a level for testing. Need a real Discord run |
| `/duel` with hidden-move buttons | Written and tested end to end with fake Discord objects: challenge, accept or decline, hidden moves, timeouts, forfeits, saved result. Both players fight at the average of their two levels by default, and the real\_levels option uses their real levels. Needs a real Discord run with two accounts |
| Choosing a preset when a duel starts | Not started. Duels use preset 1 for now |
| Expeditions and `/scavenge` | Written and tested with fake Discord objects: one /scavenge command starts a 30 minute run, shows the time left while you are out, and shows the haul with Bank & Leave and Push Deeper once you are back, the result is fixed by a stored seed, and each claim is one transaction. Needs a real Discord run. A player can start 3 runs per rolling 24 hours (MAX\_RUNS in game/loot.py). No XP, one zone, placeholder numbers |
| Rerolling and salvaging | Written and tested with fake Discord objects: /salvage (one item, or every unequipped item of a rarity, with a confirm screen) and /reroll (lock buttons, repeat rerolls, shard cost, pity). Needs a real Discord run. Placeholder numbers, and no selling for gold yet |
| Shop, selling and XP | Written and tested with fake Discord objects: /shop, /buy slot rarity (Common 500 gold, Rare 4,000, no Epic), /sell (Common 40, Rare 150, Epic 500), XP from expeditions (30, plus 60 for a Push win) and duels (20 win, 10 otherwise, first 3 a day). Needs a real Discord run. Stingy placeholder numbers |
| Async duels, `/inspect`, a command to set a preset's disposition | Dropped on 2026-11-18: duels are live only |
| Daily database backup | Written and tested: one backup a day with the newest 7 kept, plus an owner-only !backup. Needs a real run |

## Running the bot

1. Install the packages: `pip install discord.py aiosqlite`, and add both to `requirements.txt`.
2. Set the `TOKEN` environment variable as before. `DB_PATH` is optional and defaults to `data/game.db`.
3. Start the bot from the project root with `python -m src.main`.
4. In your server, run `!sync` once (bot owner only), then wait a minute for the slash commands to appear.
5. Run `/start`, then `/profile`, `/inventory` and `/equip`.

## Project structure

Two folders are called `game`. The top-level `game/` holds the rules and never imports discord, so the same combat code runs in the bot, the terminal playtest and the 10,000-duel balance simulation. `cogs/game/` holds the Discord commands, which stay thin: they take a command, call into `game/` and `core/`, and render an embed from `ui/`.

Use `aiosqlite` so database calls do not block the event loop, and attach the connection to the bot in `setup_hook`.

## File map

The tree shows every file and where it lives, starting from the project root. All the code is inside `src/`, which keeps it apart from `data/`, `backups/` and the project files. A comment says what each file does, and `planned` marks files that are not written yet. It is updated whenever a file is added or changes purpose.

```text
project/                    # the project root
├── README.md               # yours
├── requirements.txt        # yours: discord.py and aiosqlite
├── .gitignore              # yours: add data/ and backups/
├── data/
│   └── game.db             # made by the bot on first start, not pushed to git
├── backups/                # made by the bot: one copy of game.db a day, newest 7 kept
└── src/                    # all the code, a package; start the bot with: python -m src.main
    ├── main.py             # starts the bot, opens the database, loads every cog
    ├── config.py           # TOKEN, PREFIX, DB_PATH, BACKUP_DIR, BACKUP_KEEP
    ├── play_cli.py         # terminal playtest and bot-vs-bot simulation
    ├── core/               # database access
    │   ├── __init__.py
    │   ├── database.py     # connection, transactions, players, items, loadouts, duels
    │   ├── backup.py       # daily database snapshot and pruning of old ones
    │   └── schema.sql      # table definitions, run every time the bot starts
    ├── game/               # the rules: pure Python, never imports discord
    │   ├── __init__.py
    │   ├── combat.py       # duel engine: moves, mana, damage order, Guard counter, caps
    │   ├── items.py        # five gear slots, affix tiers, item codes, gear + level into a fighter
    │   ├── live_duel.py    # one live duel: locked moves, timeouts, forfeits, winner
    │   ├── stats.py        # base stats, per-level growth, XP curve, duel level rules
    │   ├── loot.py         # expedition rules: zones, seeded haul, Push Deeper, run limit
    │   ├── crafting.py     # salvage values, reroll cost, locks, pity
    │   ├── economy.py      # shop and sell prices, XP amounts, level-up rule
    │   └── balance_sim.py  # planned: the 10,000-duel balance script
    ├── ui/                 # embeds shown to players
    │   ├── __init__.py
    │   └── embeds.py       # profile, inventory, duel, expedition, crafting and shop embeds
    └── cogs/               # the Discord commands: thin, they call into game/ and core/
        ├── misc/
        │   ├── test.py     # yours: !test
        │   ├── admin.py    # owner-only !sync and !setlevel
        │   └── backup.py   # daily backup loop, owner-only !backup
        └── game/           # not the same folder as src/game/
            ├── _common.py  # shared checks and screen base class, skipped by the loader
            ├── profile.py  # /start, /profile
            ├── inventory.py # /inventory, /equip
            ├── duel.py     # /duel with hidden-move buttons
            ├── expedition.py # /scavenge: start, check and collect
            ├── crafting.py # /reroll, /salvage
            └── shop.py     # /shop, /buy, /sell
```

## Database

`core/schema.sql` is the source of truth for the tables, and it runs every time the bot starts (every statement uses `IF NOT EXISTS`). Affixes are stored as JSON so item generation stays flexible while the design is still changing, and can move to their own table later.

| Table | Holds |
| --- | --- |
| `players` | Level and XP, gold, shards, gems (never below zero) and the pity counter |
| `items` | Public code (uid), owner, slot, rarity, element, base stats and affixes as JSON |
| `loadouts` | Three presets per player with five slots (weapon, helmet, chestplate, leggings, boots), plus the async disposition |
| `expeditions` | Zone, start and end time, state (running, claimed or lost), seed, haul. "Ready" is not stored: a running expedition is ready once its end time has passed |
| `duels` | Mode (live or async), both players, winner (empty for a draw), rounds, seed, combat log |

All commands share one database connection, so every write goes inside `async with db.transaction():`. A lock makes overlapping commands take turns, and an error rolls the whole transaction back, so a crash cannot duplicate or delete gear.

## Hosting

During development the bot runs on your own PC, and a real host is chosen when version 1 is ready. Expedition end times are stored as timestamps, so a run keeps counting while the bot is off and shows as ready when the bot comes back.

## What is saved to the database

| Data | Where it lives | Why |
| --- | --- | --- |
| Players, items, loadouts | Database, always | Gear must never be lost |
| Expeditions | Database: zone, start time, end time, state, seed, haul | Runs survive restarts; the state goes running, then claimed or lost (a run counts as ready once its end time has passed) |
| Finished duels | Database: players, mode, winner, rounds, seed, combat log | Stats, rivalry records and replays |
| Live duel in progress | Memory only: HP, mana, locked moves | A duel lasts about 2 minutes, and hidden moves stay out of the database |

If the bot restarts mid-duel, that duel is cancelled with no penalty. Claiming an expedition changes its state from running to claimed inside one database transaction, so a double click cannot pay out twice.

## Secret moves

A button click in Discord is private by default: other players cannot see who clicked what. The bot's reply to a click can also be ephemeral, which means only the person who clicked sees it. The duel uses both facts.

1. The bot posts one public message for the round with the buttons Attack, Guard and Skill, a countdown, and both player names with a waiting mark.
2. When a duelist clicks, the bot records the move in memory and replies privately ("You chose Attack"). The public message then shows that player as locked in, without the move.
3. A click from someone outside the duel gets a private "this is not your duel" reply. Clicking Skill without enough mana gets a private "not enough mana" reply, and the player can pick again.
4. A choice is final once locked in.
5. When both players are locked in, or the timer ends (a missing player plays Guard), the bot resolves the round and edits the public message with the result, HP and energy.
6. After the last round the bot posts the combat log and saves the finished duel.

The Bank & Leave and Push Deeper buttons do not need to survive a restart: a `/scavenge` command builds them fresh from the database each time.

## Duel flow as built

- **Challenge.** `/duel @user` posts a challenge with Accept and Decline buttons, and the challenged player has 60 seconds. Both players are marked busy, so nobody can be in two duels at once, and two commands sent at the same moment cannot both go through.
- **One message.** The bot edits a single public message each round instead of posting a new one. It shows HP bars, mana, who has locked in, and the previous round's result.
- **Hidden moves.** Each click gets a private reply, and the public message only shows that a player has locked in, never which move.
- **Timer and forfeits.** Each round lasts 45 seconds. A player who does not answer plays Guard. Missing two rounds in a row forfeits the duel, and if both players go idle the duel is a draw.
- **Presets.** Duels use each player's preset 1 for now. Choosing a preset at the start of a duel is not built yet.
- **Result.** The finished duel is saved with its mode, players, winner, rounds, seed and combat log. The final message shows the log, the seed and the head-to-head record. If saving fails, the players still see the result.
- **Limits.** The message is edited through the original command, which Discord allows for 15 minutes. A duel lasts under 6 minutes, so this is safe. If the bot restarts mid-duel, the buttons stop working and the duel is dropped, as planned.

## Other decisions

- The answer timer starts at 45 seconds and is tuned in playtests.
- Code layout (2026-11-18): `src/` is a Python package and every import is counted from the project root, such as `from src.game.items import ...` (the repository root is the editor workspace). Start the bot with `python -m src.main` from the root; `python src/main.py` and an editor run button also work, because `main.py` puts the project root on the import path. Cogs are loaded as `src.cogs...`, and the terminal playtest runs with `python -m src.play_cli`. `config.py` builds the default `DB_PATH` and `BACKUP_DIR` from the project root, so `data/` and `backups/` stay at the root wherever the bot is started from. `src/`, `src/cogs/`, `src/cogs/game/` and `src/cogs/misc/` each have an empty `__init__.py`, and the cog loader skips them because their names start with an underscore.
- Async duels were dropped (2026-11-18): not practical and not worth the work, so duels are live only. The disposition column, the async move policy in game/combat.py and the duels mode value async stay in the code unused; the terminal playtest still uses the policy for its bot opponent.
- Expeditions: a player can have only one unclaimed run (running or ready), enforced by a partial unique index in the database. The haul is rolled from the stored seed when /scavenge runs and saved in `haul_json`; Push Deeper is also decided by that seed, so retrying or restarting changes nothing. Banking or losing flips the state from running inside one transaction, so a double click or a stale button cannot pay twice. The collect buttons last 5 minutes and are rebuilt by running /scavenge again. A finished run never expires.
- Number scale (decided: hundreds): defense is in points, and `defense_to_reduction` in `game/stats.py` turns it into damage reduction with defense / (defense + 500). The full per-piece values are in the Gear & Affixes Spec. A fighter without a weapon hits for 20.
- Levels live in `game/stats.py`: level 1 base stats are 100 HP, 100 mana, 0 defense, 0 strength, 30% crit chance, +50% crit damage and 100 vitality (vitality does nothing yet), and each level adds 5 HP and 1 strength. The XP curve is shaped like SkyBlock skills: level 1 to 2 costs 150 XP and each level up to 15 costs 20% more than the last, then each level costs 300 XP more than the one before (constants in game/stats.py, placeholders). Total XP to reach level 5 is 805, level 10 is 3,119, level 15 is 8,879 and level 20 is 21,509. XP comes from expeditions and duels (see the Economy Spec). Duels use the average of both players' levels unless `/duel` is run with `real_levels`.
- Skill mana numbers are placeholders that copy the old energy timing: start 30, +30 each round, +30 extra for Guard, Skill costs 60 (set per weapon), cap is the fighter's max mana (100). The schema changed again (levels, five loadout slots), so delete `data/game.db` once more.
- Every item has a short public code: one letter for the slot (W weapon, H helmet, C chestplate, L leggings, B boots) plus the item's creation number in that slot, written with the digits 1 to 9 and the letters A to Z and no dash, such as `W1`, `H9`, `HA`, `HZ`, `H11`. The number counts up in the order items are generated, so a higher number is a newer item, and a code is never reused even after an item is deleted. The counters live in a `counters` table, bumped inside the same transaction that saves the item. `/equip` takes the code (any case, dashes and spaces ignored), and the internal number stays the primary key that loadouts point to. The codes are sequential, so they are easy to guess, but `/equip` only accepts items you own. Because `schema.sql` only creates missing tables, the changed tables need `data/game.db` deleted once (only test data exists).
- The cog loader skips files whose names start with `_`, so helper files do not print load errors.
- Gameplay uses slash commands. `!` stays for owner-only commands such as `!sync`, which publishes the slash commands and is run again whenever commands are added or changed.
- The bot uses default intents plus message content, instead of all intents.
- Slash command errors are logged with a traceback and the player sees a short "something went wrong" message.
- You are working solo for now: one repo, small commits, and the schema is agreed before the cogs are written.
- Backups are built: the bot copies `data/game.db` into a `backups/` folder once a day and keeps the last 7 (BACKUP\_DIR and BACKUP\_KEEP in config.py). It checks every hour and at start-up, so a bot that was off still makes today's copy when it returns. Each copy is a SQLite snapshot (VACUUM INTO) taken while holding the database lock, so it includes recent writes and never holds half of a transaction; the owner-only !backup makes one right away. To restore, stop the bot and copy a backup over data/game.db. Add `data/` and `backups/` to `.gitignore` so they are never pushed.

## Still open

- [ ] Where will version 1 be hosted? This is decided when version 1 is ready.
- [ ] Is a 45 second answer timer right? Tune it in playtests.
- [ ] Do the first real run of `/start`, `/profile`, `/inventory`, `/equip` and `/duel` against Discord, with the packages installed. `/duel` needs two accounts.
- [ ] Let players secretly choose a preset when a duel starts.
- [ ] Playtest the mana placeholders and decide the real Skill cost and regeneration, what vitality does, and the XP curve.
- [ ] After pulling this change, delete `data/game.db`, restart the bot and run `!sync`, because `/equip` now takes a code instead of a number.
