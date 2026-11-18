# Astra

[![License: AGPL v3](https://img.shields.io/badge/License-AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

A micro-ARPG Discord battler built for small groups. Collect gear from timed expeditions, customize your build by rerolling affixes, and outsmart your friends in live, simultaneous-turn duels.

## Core Gameplay Loop

1. **Expeditions (`/scavenge`):** Launch 30-minute runs to gather gold, reroll shards, and gear. When a run finishes, choose to **Bank & Leave** safely or **Push Deeper** for higher-tier rewards at the risk of losing the haul.
2. **Crafting & Builds (`/reroll`, `/salvage`):** Tune your weapon and four armor slots (helmet, chestplate, leggings, boots). Lock desirable affixes to sculpt builds around Crit, Lifesteal, Dodge, Thorns, or elemental counters.
3. **Live Duels (`/duel`):** Challenge friends to simultaneous 3-to-5-round battles. Pick **Attack**, **Guard**, or **Skill** in secret each round—Attack interrupts Skill, Skill pierces Guard, and Guard blocks and counters Attack.

## Project Structure

```text
Astra/
├── .env                  # Environment variables (TOKEN, DB_PATH)
├── .gitignore
├── backups/              # Automated daily SQLite snapshots
├── cogs/                 # Discord slash commands and admin utilities
├── config.py             # Configuration constants
├── core/                 # Async SQLite connection, schema, and backups
├── data/                 # Runtime SQLite database (game.db)
├── docs/                 # Game design specs and technical architecture
├── game/                 # Pure Python combat, loot, crafting, and economy rules
├── LICENSE               # GNU Affero General Public License v3.0
├── main.py               # Bot entry point and cog loader
├── README.md
├── requirements.txt
└── ui/                   # Discord embeds and interactive button views
```

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/YashSharma5218/Astra.git
cd Astra
```

### 2. Prerequisites & Installation

Ensure you have Python 3.10+ installed, then set up a virtual environment and install dependencies:

```bash
python -m venv .venv
# Activate your virtual environment, then run:
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the root directory and add your Discord bot token:

```env
TOKEN=your_discord_bot_token_here
```

### 4. Running the Bot

Run the bot from the root `Astra/` directory:

```bash
python main.py
```

Once the bot is online in your server, run `!sync` (bot owner only) to register the slash commands, then use `/start` to create your fighter profile.

## Design & Technical Documentation

Detailed mechanics, math formulas, and implementation notes live in the `docs/` folder:

* [**How the Game Works**](docs/Micro-ARPG%20Discord%20Battler%20How%20the%20Game%20Works.md) — High-level overview of the gameplay loop, elemental counters, and fairness mechanics.
* [**Combat Spec**](docs/Combat%20Spec%20\(Draft%20v1,%20tuned%20in%20simulation\).md) — Round interactions, Guard counters, damage resolution order, stat caps, and simulation tuning results.
* [**Gear & Affixes Spec**](docs/Gear%20&%20Affixes%20Spec.md) — Equipment slots, rarity scaling, T1–T5 affix values, reroll locking costs, and pity rules.
* [**Economy & Expeditions Spec**](docs/Economy%20&%20Expeditions%20Spec.md) — Currencies, `/scavenge` risk/reward tables, XP curves, and shop pricing.
* [**Technical Plan**](docs/Technical%20Plan.md) — Architecture map, database schema overview, state management, and build status.

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)** — see the [LICENSE](LICENSE) file for details.