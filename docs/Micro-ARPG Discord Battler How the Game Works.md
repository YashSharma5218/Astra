# Micro-ARPG Discord Battler: How the Game Works

Nov 14, 2026 · @Yash

## The core idea

Each player is a fighter with a set of gear. You collect loot, improve it into the build you want, and use that build in duels against your friends. The whole game is one loop: **farm, upgrade gear, duel, then farm again for what you are missing.**

## A typical session

A session runs in five steps, from sending out a run to fighting a friend.

1. **Send out an expedition.** You pick a zone, for example the Inferno Cavern, and launch a run of about 30 minutes. You can leave while it runs. Each zone drops gear of its own element (Inferno drops Fire items) and affixes that counter other elements, so choosing a zone is really choosing what you are building toward.
2. **Claim the loot, and gamble.** When the run finishes you see what you found, then decide with a button: **Bank & Leave** with what you have, or **Push Deeper** for better drops at the risk of losing the whole haul.
3. **Improve your gear.** Every item has fixed base stats (a weapon's attack, an armor's defense) plus random bonus lines called affixes, such as Crit Chance, Dodge or Lifesteal. Each affix has a quality from T1 (weak) to T5 (great). You spend Reroll Shards to re-roll those lines until they are good. You can lock lines you like, but each lock raises the next reroll's cost (2x with one lock, 4x with two), so perfection cannot be brute-forced. A pity counter guarantees a top roll after enough bad luck.
4. **Set up your loadouts.** You save two or three gear presets, for example one tanky and one built around crits. You pick between them in secret when a duel starts.
5. **Duel.** You challenge a friend with `/duel`. Both loadouts are hidden, and others can only `/inspect` part of one (weapon and armor, not relic or spell). The fight lasts 3 to 5 rounds. Each round both players secretly choose **Attack, Guard or Skill** at the same time, then the choices are revealed. If you think they will attack, Guard; if you think they will Guard, use a Skill. A combat log is shown at the end.

## How the build choices work

There is no single best build: elements and stats both counter each other, and the bonuses are kept small so raw stats still matter. **Fire beats Ice, Ice beats Lightning, Lightning beats Water, and Water beats Fire**, each worth a 1.25x to 1.5x multiplier. A Neutral element exists too, and gear element is separate from spell element so hybrid builds are possible.

| Build | Countered by |
| --- | --- |
| High defense | Magic and elemental attacks |
| High dodge or speed | Attacks that cannot be avoided |
| Heavy crit | Thorns or reflect gear |

If your friend always runs a crit build, you counter it with thorns, and then they adapt. That back-and-forth is meant to be the main fun.

## Keeping it fair

With only 2 or 3 players, one person pulling far ahead would end the fun, so the design guards against it.

- **Normalized duels.** Levels are normalized, and crit, dodge and lifesteal are capped, so good gear choices beat pure grinding time.
- **Safe wagers.** Wagers are optional. In pink-slip mode you can bet gear, but both players must agree, the heirloom item cannot be taken, and the loser can buy their item back with gold.

## Currencies

Three currencies, each with its own job, keep the economy tight.

| Currency | Used for |
| --- | --- |
| Gold | Shop gear, zone entry, extra slots, duel buy-backs |
| Reroll Shards | Rerolling affixes and paying lock costs |
| Socket Gems | Unlocking sockets and adding elements to gear |

## Co-op and the short version

When you are not fighting each other, you can team up for `/raid` against a boss, which keeps the group working together between rivalries.

In one sentence: it is a small-group loot-and-build game where progress happens through gear, and the payoff is outsmarting your friends in duels.
