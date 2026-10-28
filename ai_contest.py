#!/usr/bin/env python3
"""Live pygame viewer for lighthouse bot matches.

Usage:
    python3 ai_contest.py                                   # greedy vs random
    python3 ai_contest.py --bots greedy,random,random
    python3 ai_contest.py --bots greedy,random --rounds 200 --delay 300
    python3 ai_contest.py --presentation --screenshot out.png

Available bots: see match.py BOT_REGISTRY.
"""

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

from pygame.time import delay

from botplayer import BotPlayer
from config import GameConfig
from game import Game
from view import GameView
from match import load_bot_class


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bots", default="random,greedy",
                        help="comma-separated bot names, e.g. greedy,random")
    parser.add_argument("--map", default="maps/island.txt", dest="map_file")
    parser.add_argument("--rounds", type=int, default=0,
                        help="round cap (0 = play until window is closed)")
    parser.add_argument("--delay", type=int, default=500,
                        help="milliseconds between rounds")
    parser.add_argument("--scale", type=int, default=2,
                        help="display scale (2 = default, 1 = half size)")
    parser.add_argument("--presentation", action="store_true",
                        help="1280x720 broadcast-style view instead of the "
                             "engineering viewer")
    parser.add_argument("--title", default=None,
                        help="presentation title "
                             "(default: AI CONTEST - LIGHTHOUSE AI)")
    parser.add_argument("--screenshot", default=None, metavar="PATH",
                        help="save the final frame to this PNG file")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.seed is not None:
        import random
        random.seed(args.seed)

    bot_names = [b.strip() for b in args.bots.split(",")]
    bot_classes = [load_bot_class(name) for name in bot_names]

    config = GameConfig(args.map_file)
    game = Game(config, len(bot_classes))

    actors = [
        BotPlayer(game, i, cls(), debug=args.debug)
        for i, cls in enumerate(bot_classes)
    ]
    for actor in actors:
        actor.initialize()

    if args.presentation:
        from presentation import PresentationView
        view = PresentationView(game, player_names=bot_names,
                                title=args.title
                                or "AI CONTEST - LIGHTHOUSE AI",
                                total_rounds=args.rounds)
    else:
        view = GameView(game, player_names=bot_names, scale=args.scale)

    round_num = 0
    cur_delay = args.delay
    while True:
        events = view.handle_events()
        if events['quit'] or view.close_event():
            break
        if events['speed'] is not None:
            cur_delay = max(10, int(args.delay / events['speed']))
        if events['screenshot']:
            print("screenshot saved to %s" % events['screenshot'])

        view.round_num = round_num

        if view.paused:
            view.update()
            delay(50)
            continue

        game.pre_round()
        view.update()
        for gamer in actors:
            gamer.turn()
            view.update()
        game.post_round()
        score = "  ".join("%s(P%d): %d" % (bot_names[i], i, game.players[i].score)
                          for i in range(len(bot_names)))
        print("########### ROUND %d SCORE: %s" % (round_num, score))
        round_num += 1
        if args.rounds and round_num >= args.rounds:
            print("=== FINAL: %s ===" % score)
            break
        delay(cur_delay)

    view.update()
    if args.screenshot:
        path = view.save_screenshot(args.screenshot)
        print("screenshot saved to %s" % path)


if __name__ == "__main__":
    main()
