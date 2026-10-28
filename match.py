#!/usr/bin/env python3
"""Headless match runner for lighthouse bots.

Runs N games between bots on a map with a round cap and seeded RNG,
then prints win-rate and score statistics. No pygame/view needed.

Usage:
    python3 match.py --bots greedy,random --map maps/island.txt \
        --games 10 --rounds 200 --seed 42

Available bots: greedy, random
Bots are loaded with per-bot sys.path isolation: each bot package uses
top-level imports (e.g. `import interface`) that would collide if loaded
together, so previously loaded bot modules are evicted from sys.modules
before importing the next one.
"""

import argparse
import contextlib
import io
import os
import random
import statistics
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from botplayer import BotPlayer  # noqa: E402
from config import GameConfig  # noqa: E402
from game import Game  # noqa: E402

BOT_REGISTRY = {
    # name: (examples/<subdir>, module, class)
    "random": ("RandBot", "randbot", "RandBot"),
    "greedy": ("GreedyBot", "greedybot", "GreedyBot"),
}


def load_bot_class(name):
    """Import a bot class with isolation from previously loaded bots."""
    if name not in BOT_REGISTRY:
        raise SystemExit("Unknown bot %r. Available: %s"
                         % (name, ", ".join(sorted(BOT_REGISTRY))))
    # Evict modules loaded for previous bots to avoid top-level name
    # collisions (every bot package has e.g. its own interface.py).
    for mod_name, mod in list(sys.modules.items()):
        mod_file = getattr(mod, "__file__", None)
        if mod_file and os.path.join(ROOT, "examples") in mod_file:
            del sys.modules[mod_name]
    subdir, module_name, class_name = BOT_REGISTRY[name]
    sys.path.insert(0, os.path.join(ROOT, "examples", subdir))
    try:
        module = __import__(module_name)
    finally:
        sys.path.pop(0)
    return getattr(module, class_name)


def play_game(map_file, bot_classes, rounds, verbose=False):
    """Play one game; return list of scores per player index."""
    config = GameConfig(map_file)
    game = Game(config, len(bot_classes))
    actors = [
        BotPlayer(game, i, cls(), debug=False)
        for i, cls in enumerate(bot_classes)
    ]
    ctx = contextlib.nullcontext() if verbose \
        else contextlib.redirect_stderr(io.StringIO())
    with ctx:
        for actor in actors:
            actor.initialize()
        for round_num in range(rounds):
            game.pre_round()
            for actor in actors:
                actor.turn()
            game.post_round()
    return [player.score for player in game.players]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bots", required=True,
                        help="comma-separated bot names, e.g. greedy,random")
    parser.add_argument("--map", default="maps/island.txt", dest="map_file")
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--rounds", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rotate", action="store_true",
                        help="rotate seat assignment each game (fairness)")
    parser.add_argument("--verbose", action="store_true",
                        help="show bot stderr logs")
    args = parser.parse_args()

    bot_names = [b.strip() for b in args.bots.split(",")]
    bot_classes = [load_bot_class(name) for name in bot_names]

    wins = [0] * len(bot_names)
    draws = 0
    all_scores = [[] for _ in bot_names]

    for game_num in range(args.games):
        random.seed(args.seed + game_num)
        if args.rotate:
            k = game_num % len(bot_classes)
            order = list(range(k, len(bot_classes))) + list(range(k))
        else:
            order = list(range(len(bot_classes)))
        seat_classes = [bot_classes[i] for i in order]
        seat_scores = play_game(args.map_file, seat_classes, args.rounds,
                                verbose=args.verbose)
        # map seat scores back to original bot indices
        scores = [0] * len(bot_classes)
        for seat, orig in enumerate(order):
            scores[orig] = seat_scores[seat]
        best = max(scores)
        if scores.count(best) > 1:
            draws += 1
        else:
            wins[scores.index(best)] += 1
        for i, score in enumerate(scores):
            all_scores[i].append(score)
        print("game %2d: %s" % (game_num, "  ".join(
            "%s=%d" % (bot_names[i], s) for i, s in enumerate(scores))))

    print("\n=== %d games | map=%s | rounds=%d | seed=%d ==="
          % (args.games, args.map_file, args.rounds, args.seed))
    for i, name in enumerate(bot_names):
        scores = all_scores[i]
        print("%-10s wins=%-3d mean=%-8.1f std=%-6.1f min=%-4d max=%-4d"
              % (name, wins[i], statistics.mean(scores),
                 statistics.pstdev(scores) if len(scores) > 1 else 0.0,
                 min(scores), max(scores)))
    print("draws=%d" % draws)


if __name__ == "__main__":
    main()
