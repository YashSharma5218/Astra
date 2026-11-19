# Economy & Expeditions Spec

Nov 14, 2026 · @Yash

## Currencies and sinks

Three currencies, each with its own job and its own sink, keep a 2 to 3 player economy from inflating.

| Currency | Used for |
| --- | --- |
| Gold | Shop gear, zone entry fees, inventory and preset slots, duel buy-backs |
| Reroll Shards | Rerolling affixes and paying escalating lock costs |
| Socket Gems | Unlocking socket slots and adding elements to gear |

The rule behind all of it: every currency exists to fuel gear progression, customization or dueling. There is no daily or work command, and no passive coin stealing.

## Expeditions

Farming is a timed run, not a cooldown command. A player launches an expedition (about 30 minutes), leaves, and comes back to a result embed.

1. **Choose a zone.** Each zone drops gear of its own element and affixes that counter other elements, for example the Inferno Cavern drops Fire gear and Ice-countering affixes.
2. **Claim with a gamble.** On completion the player picks **Bank & Leave** to keep the loot, or **Push Deeper** for higher-tier drops at the risk of losing the haul.
3. **Raids.** `/raid` lets 2 to 3 players team up against a scaled boss, planned for the last phase of development.

## Version 1 rules

- **Gold** comes from expeditions and from selling unwanted items.
- **Reroll Shards** come mainly from salvaging unwanted items, plus a small amount from expeditions. Every junk drop becomes useful.
- **Socket Gems** are rare and come from Push Deeper wins and bosses. In version 1 they only set an item's element; sockets are left out.
- **Levels get XP (placeholders).** XP: an expedition gives 30, and a successful Push Deeper adds 60 more (a lost Push gives nothing). A duel gives 20 for a win and 10 for a loss or draw, but only the first 3 duels in any rolling 24 hours count, so two friends cannot farm each other. Levels add only +5 HP and +1 strength, so power still comes from gear; levels mostly mark progress and gate /dungeon in v2. The curve starts at 150 XP for level 1 to 2, grows 20% per level up to level 15, then adds a fixed 300 XP per level (like SkyBlock skills). At about 200 XP a day that is level 5 in about 4 days, level 10 in about 2 weeks, level 15 in about 6 weeks and level 20 in about 3 to 4 months.
- **One zone,** with a single Bank & Leave or Push Deeper choice at the end of the run. More checkpoints can come later.
- **No trading** between players.

## Expedition as built

- **/scavenge** is the only expedition command. With no run it starts a 30 minute run in Mossy Ruins (neutral gear); while you are out it shows the time left; once you are back it shows the claim screen. A player has one unclaimed run at a time. The haul is rolled from a stored seed at launch, so nothing can be rerolled.
- **Claim screen** shows the haul once time is up: gold, shards and one item, shown exactly as it will be saved. Bank & Leave keeps it. Push Deeper succeeds 55% of the time (double gold and shards, you keep every item you were shown, plus one bonus item from the better table and a 30% chance of a Gem, so a win is never worse than banking), otherwise the whole haul is lost.
- **Rarity tables:** a normal haul is 70% Common, 25% Rare, 5% Epic. The bonus item after a successful Push uses 35%, 45% and 20%. The item slot is random across the five slots.
- **Safe by design:** banking or losing happens in one database transaction, so a double click cannot pay out twice. A finished run never expires, and the claim buttons last 5 minutes before /scavenge has to be run again.
- **Design rule: stingy on purpose.** Rewards are kept low so that getting gear feels like an achievement. Epic gear can only be earned from expeditions, never bought.
- **Run limit:** a player can start 3 expeditions in any rolling 24 hours. Each run (banked or lost) uses a charge, and the charge comes back 24 hours after that run started, so there is no daily reset time and skipping a day loses nothing. When all 3 are used, /scavenge shows when the next one is available. Placeholder: the number is MAX\_RUNS in game/loot.py, to be tuned in playtests. This is a charge system, not a daily command, so it fits the rule of no daily or work command.

## Shop and selling (placeholders, stingy on purpose)

- **/shop** shows the prices and your gold. **/buy slot rarity** gives one random item of the slot and rarity you choose, with random affixes. Common costs 500 gold and Rare costs 4,000. **Epic is never sold**: it can only be earned from expeditions. Full expedition income is about 1,800 gold a day, so a Rare is a couple of days of saving.
- **/sell** breaks an item down for gold instead of shards: Common 40, Rare 150, Epic 500. Give a code, or a rarity to sell every unequipped item of that rarity, with a confirm screen. Items equipped in any preset are protected. Selling is a small trickle, not a way to fund the shop.
- Not in version 1: preset slot prices and zone entry fees (the entry fee is 0 and there is one zone). They come back with more zones and /dungeon in v2.

## Open numbers

- [ ] What is the target pace? (for example, one decent upgrade per evening, a tuned build in about two weeks)
- [ ] How much does one expedition drop? Placeholder: 400 to 800 Gold, 10 to 30 Shards, one item and no Gems from a normal run.
- [ ] How many Shards does salvaging give per rarity, and what does selling an item pay?
- [ ] Is Push Deeper tuned right? Placeholder: 55% to succeed, then gold and shards double, the original items are kept, one bonus item rolls on the better table, and there is a 30% chance of a Gem. Since a win can no longer be worse than banking, check whether 55% is too generous.
- [ ] What is the entry fee for the zone? Placeholder: none.
