"""Terminal playtest for the duel engine.

    python -m src.play_cli          # you vs a bot (pick moves with a / g / s)
    python -m src.play_cli --sim 5000   # bot vs bot, prints win rates

The bot uses the same async defender policy the Discord bot will use.
"""
from __future__ import annotations

import argparse
import random

from src.game.combat import (DISPOSITIONS, Duel, Fighter, Move, format_round,
                         policy_move)

KEYS = {"a": Move.ATTACK, "g": Move.GUARD, "s": Move.SKILL}


def ask_move(me: Fighter) -> Move:
    legal = Duel.legal_moves(me)
    options = "/".join(m.value[0] for m in legal)
    while True:
        raw = input(f"Your move [{options}] (mana {me.mana}/{me.max_mana}, {me.skill_name} costs {me.skill_cost}): ").strip().lower()
        move = KEYS.get(raw[:1])
        if move in legal:
            return move
        print("  Not available, try again.")


def play(disposition: str) -> None:
    you = Fighter("You")
    bot = Fighter("Bot", disposition=disposition)
    duel = Duel(you, bot)
    rng = random.Random()
    print(f"Duel start (seed {duel.seed}). Bot is {disposition}. 100 HP each.\n")
    while not duel.over:
        mine = ask_move(you)
        theirs = policy_move(bot, you, rng)
        print(format_round(duel.play_round(mine, theirs)) + "\n")
    w = duel.winner()
    print("Draw." if w is None else f"{w.name} wins!")


def simulate(n: int) -> None:
    rng = random.Random(1)
    results = {}
    for a_disp in DISPOSITIONS:
        for b_disp in DISPOSITIONS:
            wins = [0, 0, 0]
            for i in range(n):
                a = Fighter("A", disposition=a_disp)
                b = Fighter("B", disposition=b_disp)
                d = Duel(a, b, seed=rng.randrange(2**32))
                while not d.over:
                    d.play_round(policy_move(a, b, rng), policy_move(b, a, rng))
                w = d.winner()
                wins[0 if w is a else 1 if w is b else 2] += 1
            results[(a_disp, b_disp)] = wins
            print(f"{a_disp:>10} vs {b_disp:<10} "
                  f"A {wins[0]/n:5.1%}  B {wins[1]/n:5.1%}  draw {wins[2]/n:5.1%}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sim", type=int, help="simulate N duels per matchup")
    p.add_argument("--bot", choices=list(DISPOSITIONS), default="balanced")
    args = p.parse_args()
    simulate(args.sim) if args.sim else play(args.bot)
