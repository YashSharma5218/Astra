# Gear & Affixes Spec

Nov 14, 2026 · @Yash

## Slots and rarities

Equipment has five slots: the weapon plus four armor pieces (helmet, chestplate, leggings, boots). The weapon's ability is the Skill move, so there is no separate spell slot. All five slots are in the code. Numbers are on the hundreds scale: a level 1 fighter has 100 HP and gear provides the bulk. Each armor piece has its own base HP and defense (table below), and the affixes make each item unique. Strength joins the affix list (T1 +1 to T5 +7 points, each point adding 1% attack damage).

| Slot | Base stats | In v1? |
| --- | --- | --- |
| Weapon | Base ATK, Speed | Yes |
| Armor | Base defense and HP, different for each piece | Yes |
| Weapon ability | Skill effect, paid with mana (a basic test weapon for now) | Later |
| Relic or Pet | Passive bonus | Later |

Rarity runs Common, Rare, Epic, Legendary, Mythic. Higher rarity unlocks more affix slots on the item. Base stats are flat values set by the slot type and stay untouched by rerolling.

Base stats by piece and rarity (defense points / HP). Defense turns into damage reduction with defense / (defense + 500).

| Piece | Common | Rare | Epic |
| --- | --- | --- | --- |
| Chestplate | 24 / 140 | 32 / 170 | 40 / 200 |
| Leggings | 21 / 100 | 28 / 120 | 35 / 140 |
| Helmet | 18 / 100 | 24 / 120 | 30 / 140 |
| Boots | 12 / 60 | 16 / 70 | 20 / 80 |
| Full set | 75 / 400 (13%) | 100 / 480 (17%) | 125 / 560 (20%) |
| Weapon attack | 100 | 120 | 140 |

A full Common set with the 100 base HP gives about 500 HP and a hit of 100, the same five-hit pace the simulation was tuned on.

## Affixes and tiers

Every affix is a stat type plus a quality tier, so chasing a good roll means chasing both.

- **Stat types:** Crit Chance, Crit Multiplier, Armor Pen, Lifesteal, Dodge, Thorns or Reflect, Elemental DMG.
- **Tiers:** T1 is the lowest range and T5 the highest, each with its own value range per stat.
- **Caps:** Hard caps in duels: crit chance 70%, crit damage +100%, dodge 25%, lifesteal 25%, armor pen 50%, thorns 20%, defense reduction 70%.

### Tuned T5 values

The combat simulation tuned the top-tier value of each affix. T3 is about 58% of T5; the exact T1 to T4 steps are still open.

| Affix | T5 value |
| --- | --- |
| Strength | +7 (percent attack bonus) |
| Crit chance | +12% |
| Crit damage | +20% |
| Armor pen | +14% |
| Lifesteal | +5% |
| Thorns | +5% |
| Dodge | +8% |

The ranges are low on purpose: a full set of five items carries about 15 affix lines, so each line must be worth only a small slice of power (about 5 to 6% for a T5 line). Every affix slot is meant to be equally valuable, so no slot is a dead pick.

With these values, 15 T3 affixes in six archetype builds (Crit, Vampire, Dodger, Thorny, Bruiser, Balanced) land between 47% and 54% average win rate against each other, using the tuned combat rules from the Combat Spec.

## Rerolling

Players spend Reroll Shards to re-roll an item's open affix lines while its base stats stay intact. Locking a line you like raises the cost of the next reroll: one lock doubles it (2x) and two locks quadruple it (4x). A pity counter guarantees a T4 or T5 roll after N failed rerolls, with N still to be chosen. Lock cost and pity pull in opposite directions, so tune one as the main driver and keep the other light.

### Rerolling and salvaging as built

- **/salvage** destroys an item for shards: Common 8, Rare 24, Epic 60. Give a code (like H12) or a rarity, which takes every unequipped item of that rarity. A confirm screen shows the items and the total first. Items equipped in any of the three presets are protected.
- **/reroll code** opens a screen with one Lock button per affix line, Reroll and Done. Every unlocked line is rolled again; locked lines stay exactly as they are; a new line never repeats a stat already on the item. At least one line must stay open, so a Common item (one line) cannot lock anything.
- **Cost:** base 15 (Common), 30 (Rare) or 60 (Epic) shards, doubled for each lock: 1 lock is 2x, 2 locks 4x. Locks stay on between rerolls until you press Done.
- **Pity:** the player's counter goes up by 1 for each reroll that rolls no T4 or T5 line and resets when one appears. At 10, the next reroll guarantees a T4 or T5 on its first open line.
- Salvage and reroll each run in one database transaction, so a double click or a failed save cannot charge twice or lose an item. A salvaged item's code is never reused.
- All numbers are placeholders, to be tuned against how many shards an expedition gives (10 to 30). Selling for gold is not built yet.

## Open questions

- [ ] T5 values are tuned. What are the exact T1 to T4 values and their ranges for each stat?
- [ ] How many affix slots does each rarity get?
- [ ] Which rarities, affixes and base items are in version 1, and what is cut?
- [ ] What is the base reroll cost in shards, and what is N for the pity counter?
- [ ] Can players trade or give items to each other?
- [ ] Which base stats go on each armor piece (helmet, chestplate, leggings, boots), and do they carry different affix pools?
