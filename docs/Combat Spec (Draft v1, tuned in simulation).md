# Combat Spec (Draft v1, tuned in simulation)

Nov 14, 2026 · @Yash

## Round rules

A level 1 fighter has 100 base HP and gear provides the bulk of the numbers: a full Common set gives about 500 HP and a hit of about 100, so a duel takes around five hits to knock someone out. The tuning results below were run at an earlier scale of 100 HP and a hit of 20, so multiply damage values there by 5. A duel lasts 3 to 5 rounds. Each round both players pick Attack, Guard or Skill in secret, then the moves are revealed together. Numbers marked tuned come from a simulation (see Tuning results below); real playtests still have the last word.

Energy: each player starts with 1 energy and gains 1 per round. Skill costs 2 energy. Energy is gained at the end of each round, Guarding grants 1 extra energy, and energy is capped at 3.

| Your move | vs Attack | vs Guard | vs Skill |
| --- | --- | --- | --- |
| **Attack** | Both hit for full damage | Guard blocks 70% of the hit and counters (see Guard counter) | Attack interrupts the Skill, which lands at 45% damage |
| **Guard** | Blocks 70% of the hit and counters, plus 1 extra energy | Nothing happens, both gain energy | The guard only blocks 56% of the Skill (it pierces part of the guard) |
| **Skill** | Lands at 45% damage | Blocked for only 56% | Both land in full |

The logic is a loop: Attack beats Skill, Skill beats Guard, Guard beats Attack. Gear, crits and elements bend these numbers but do not replace the rules.

Skill is the weapon's ability. Until weapons are designed, a basic test weapon gives a heavy strike worth 1.5 times the base hit that cannot be dodged. Skill costs mana, set by the weapon. The placeholder numbers copy the energy timing the simulation used: start 30, +30 each round, +30 extra for Guard, Skill costs 60, cap 100. The percentages in the table apply to that amount.

### Guard counter

If you Guard and the opponent plays Attack, you block 70% of the hit and counter for 70% of your own base hit, reduced by their defense. The counter cannot crit or be dodged. It only triggers against Attack, because a Skill pierces the guard. Without the counter, Guard was strictly worse than the other moves in the simulation.

## Damage formula

Start with the simplest version that works, and add armor pen and dodge once the base feels right.

```latex
\text{damage} = \text{attack} \times \text{element multiplier} \times (1 - \text{defense reduction})
```

Crit is both a base mechanic and a build choice: every fighter starts with a 30% crit chance and +50% crit damage, and affixes raise both. A guarded hit cannot crit. The element multiplier is 1.25 to 1.5 when the attacker's element beats the defender's, and 1 otherwise. Crit, dodge and lifesteal are capped so no single stat decides a duel.

### Order of each hit

1. **Dodge roll**, capped at 25%. A dodged hit does 0 damage and is logged. Skills cannot be dodged.
2. **Crit roll**, skipped if the defender guarded. A crit adds the crit damage bonus (+50% at base).
3. **Element multiplier.**
4. **Defense reduction**, shrunk by armor penetration: the defender's reduction is multiplied by (1 minus armor pen). Defense points become a reduction with defense / (defense + 500), so 125 defense (a full Epic set) removes about 20%.
5. **Guard block**, if the defender guarded: 70% against an Attack, 56% against a Skill.
6. **Thorns:** a percentage of the damage actually taken is reflected to the attacker. Reflected damage cannot crit, be dodged or bounce back.
7. **Lifesteal** heals the attacker for a percentage of the damage dealt, up to max HP.

### Caps

Crit chance, dodge, lifesteal, armor penetration, defense reduction and thorns all have hard caps so no single stat decides a duel. Tuned caps: crit chance 70%, crit damage +100%, dodge 25%, lifesteal 25%, armor pen 50%, defense reduction 70%, thorns 20%.

## Tuning results (simulation)

Rules chosen: Guard blocks 70% and counters for 70% of the guarder's own base hit, Skill is blocked for only 56%, Attack cuts a Skill to 45%, and guarded hits cannot crit.

Net damage per round at equal gear (row move against column move, positive means the row player gains):

| Your move | vs Attack | vs Guard | vs Skill |
| --- | --- | --- | --- |
| Attack | 0.0 | -8.0 | +7.5 |
| Guard | +8.0 | 0.0 | -13.2 |
| Skill | -7.5 | +13.2 | 0.0 |

No move is dominated, and the equilibrium mix is about 46% Attack, 26% Guard and 28% Skill. In a 5-round round robin with identical gear, spamming Attack averages 57%, random mixing 50%, Guard+Skill 42% and Attack+Skill 32%. A player who reacts to the opponent's last move (the Reader) averages 69% and beats a spammer every time, so reading the opponent pays off.

Build balance with 15 affixes at T3, random-mix play: Crit 54%, Vampire 53%, Dodger 50%, Thorny 49%, Bruiser 48%, Balanced 47%. Tuned T5 values are in the Gear & Affixes Spec.

## Levels and base stats (decided, not built)

- **Level 1 base stats:** 100 HP, 100 mana, 0 defense, 0 strength, 30% crit chance, +50% crit damage, vitality 100.
- **Per level:** +5 HP and +1 strength. On the hundreds scale, +5 HP is only about 1% of a Common set per level, so level growth is small next to gear. Whether that is right is still open.
- **Duels:** both players fight at the average of their two levels by default. A second option on /duel uses their real levels.
- **Expeditions and zones:** real levels always count.
- **Skill:** the weapon's ability, paid with mana. Energy versus mana is still open.

## Duel flow

- **Ties.** If both players are alive after round 5, the higher HP wins. An exact HP tie goes to the player who dealt more damage, otherwise it is a draw. If both reach 0 HP in the same round, the same tie-break applies.
- **Timeouts.** A player who does not answer in time plays a default Guard. Missing two rounds in a row forfeits the duel.
- **No async duels.** Dropped on 2026-11-18 as not practical and not worth the work. Duels are live only, with both players online. The disposition and move policy in the code stay unused for now (the terminal playtest uses the policy for its bot opponent).

## Open questions

- [ ] Does Skill at 1.5 times damage feel right in playtests?
- [ ] How long is the answer timer? (30 to 60 seconds)
- [x] What are the cap values for crit, lifesteal, armor pen, defense reduction and thorns?
- [ ] Does a real playtest confirm that no move always wins? (The simulation says none does.)
- [ ] How much mana does a Skill cost, and how fast does mana regenerate?
- [ ] What does vitality do? (Defense already uses defense / (defense + 500).)
- [ ] How do HP per level and strength per level get matched?
