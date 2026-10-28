"""Smoke tests for the game engine and the headless match runner.

Standard library only (unittest), mirroring match.py's no-dependency design.
Run with:  python -m unittest discover -s tests -v
"""

import glob
import os
import random
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import match  # noqa: E402  (also puts engine/ on sys.path)

MAPS = sorted(glob.glob(os.path.join(ROOT, "maps", "*.txt")))


def seeded_game(map_file, bot_names, rounds, seed):
    random.seed(seed)
    classes = [match.load_bot_class(name) for name in bot_names]
    return match.play_game(map_file, classes, rounds)


class EngineSmokeTests(unittest.TestCase):
    def test_maps_are_present(self):
        self.assertGreater(len(MAPS), 0, "no maps found under maps/")

    def test_every_map_plays_a_duel(self):
        for map_file in MAPS:
            with self.subTest(map=os.path.basename(map_file)):
                scores = seeded_game(map_file, ["greedy", "random"], 30, seed=0)
                self.assertEqual(len(scores), 2)
                for score in scores:
                    self.assertIsInstance(score, int)
                    self.assertGreaterEqual(score, 0)

    def test_four_player_melee(self):
        island = os.path.join(ROOT, "maps", "island.txt")
        scores = seeded_game(island, ["greedy", "random", "greedy", "random"], 30, seed=1)
        self.assertEqual(len(scores), 4)

    def test_seeded_games_are_deterministic(self):
        island = os.path.join(ROOT, "maps", "island.txt")
        first = seeded_game(island, ["greedy", "random"], 50, seed=42)
        second = seeded_game(island, ["greedy", "random"], 50, seed=42)
        self.assertEqual(first, second)

    def test_greedy_outscores_random_on_island(self):
        # Behavioral baseline (see stats/duel_island.txt): the greedy
        # example bot should beat the random bot over a few seeded games.
        island = os.path.join(ROOT, "maps", "island.txt")
        greedy_wins = 0
        for seed in range(5):
            greedy, rand = seeded_game(island, ["greedy", "random"], 100, seed=seed)
            greedy_wins += greedy > rand
        self.assertGreaterEqual(greedy_wins, 3)

    def test_unknown_bot_is_rejected(self):
        with self.assertRaises(SystemExit):
            match.load_bot_class("does-not-exist")


class MatchCliTests(unittest.TestCase):
    def test_cli_runs_end_to_end(self):
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "match.py"),
             "--bots", "greedy,random", "--games", "2", "--rounds", "20", "--rotate"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("draws=", result.stdout)
        self.assertIn("greedy", result.stdout)


if __name__ == "__main__":
    unittest.main()
