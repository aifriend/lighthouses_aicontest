"""Rule-level unit tests: Game.connect, Lighthouse.attack/decay, geom.intersect,
and BotPlayer's handling of a crashing bot.

Standard library only (unittest), runnable with pytest or unittest.
"""

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import match  # noqa: E402,F401  (puts engine/ on sys.path)
from botplayer import BotPlayer  # noqa: E402
from config import CommError, GameConfig, MoveError  # noqa: E402
from game import Game  # noqa: E402
from geom import intersect  # noqa: E402

# 9x9 map, border is rock. Lighthouses at (2,2) (6,2) (4,4) (4,6); players A, B.
MAP = """\
#########
#       #
#   !   #
#       #
#  !!   #
#       #
#!  A !B#
#       #
#########
"""


# Four lighthouses at the corners of a square: (2,2) (6,2) (2,6) (6,6),
# so the diagonals (2,2)-(6,6) and (6,2)-(2,6) properly cross.
CROSS_MAP = """\
#########
#       #
# !   ! #
#       #
#  A B  #
#       #
# !   ! #
#       #
#########
"""


def make_game(text=MAP):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fd:
        fd.write(text)
    try:
        cfg = GameConfig(fd.name)
    finally:
        os.unlink(fd.name)
    return Game(cfg, 2)


class IntersectTests(unittest.TestCase):
    def test_crossing_segments_intersect(self):
        self.assertTrue(intersect(((0, 0), (2, 2)), ((2, 1), (1, 2))))

    def test_disjoint_segments_do_not_intersect(self):
        self.assertFalse(intersect(((0, 0), (2, 2)), ((4, 1), (1, 4))))

    def test_touching_endpoint_is_not_an_intersection(self):
        self.assertFalse(intersect(((0, 0), (2, 2)), ((2, 2), (4, 0))))

    def test_collinear_segments_do_not_intersect(self):
        self.assertFalse(intersect(((0, 0), (1, 1)), ((2, 2), (3, 3))))


class LighthouseTests(unittest.TestCase):
    def setUp(self):
        self.game = make_game()
        self.p0, self.p1 = self.game.players
        self.lh = next(iter(self.game.lighthouses.values()))

    def test_attack_claims_neutral_lighthouse(self):
        self.p0.energy = 30
        self.lh.attack(self.p0, 20)
        self.assertEqual((self.lh.owner, self.lh.energy), (0, 20))
        self.assertEqual(self.p0.energy, 10)

    def test_attack_is_capped_by_player_energy(self):
        self.p0.energy = 5
        self.lh.attack(self.p0, 50)
        self.assertEqual(self.lh.energy, 5)
        self.assertEqual(self.p0.energy, 0)

    def test_attack_rejects_bad_strength(self):
        with self.assertRaises(MoveError):
            self.lh.attack(self.p0, -1)
        with self.assertRaises(MoveError):
            self.lh.attack(self.p0, 1.5)

    def test_enemy_attack_reduces_then_takes_over(self):
        self.p0.energy = self.p1.energy = 100
        self.lh.attack(self.p0, 30)
        self.lh.attack(self.p1, 20)
        self.assertEqual((self.lh.owner, self.lh.energy), (0, 10))
        self.lh.attack(self.p1, 25)
        self.assertEqual((self.lh.owner, self.lh.energy), (1, 15))

    def test_decay_to_zero_clears_owner_and_connections(self):
        self.p0.energy = 10
        self.lh.attack(self.p0, 10)
        other = self.lh.pos
        self.game.conns.add(frozenset((other, (99, 99))))
        self.game.tris[(other, (98, 98), (99, 99))] = [(0, 0)]
        self.lh.decay(5)
        self.assertEqual((self.lh.owner, self.lh.energy), (0, 5))
        self.lh.decay(50)
        self.assertEqual((self.lh.owner, self.lh.energy), (None, 0))
        self.assertEqual(self.game.conns, set())
        self.assertEqual(self.game.tris, {})


class ConnectTests(unittest.TestCase):
    def setUp(self):
        self.game = make_game()
        self.player = self.game.players[0]

    def own(self, *positions):
        for pos in positions:
            lh = self.game.lighthouses[pos]
            lh.owner = self.player.num
            lh.energy = 10

    def test_connect_requires_standing_on_origin(self):
        self.player.pos = (1, 1)
        with self.assertRaises(MoveError):
            self.game.connect(self.player, sorted(self.game.lighthouses)[1])

    def test_connect_requires_existing_destination(self):
        a = sorted(self.game.lighthouses)[0]
        self.player.pos = a
        with self.assertRaises(MoveError):
            self.game.connect(self.player, (1, 1))

    def test_connect_requires_ownership_and_key(self):
        a, b = sorted(self.game.lighthouses)[:2]
        self.player.pos = a
        with self.assertRaises(MoveError):  # neither owned
            self.game.connect(self.player, b)
        self.own(a, b)
        with self.assertRaises(MoveError):  # owned, no key
            self.game.connect(self.player, b)

    def test_connect_to_self_is_rejected(self):
        a = sorted(self.game.lighthouses)[0]
        self.player.pos = a
        self.own(a)
        self.player.keys.add(a)
        with self.assertRaises(MoveError):
            self.game.connect(self.player, a)

    def test_successful_connect_consumes_key_and_blocks_duplicates(self):
        a, b = sorted(self.game.lighthouses)[:2]
        self.player.pos = a
        self.own(a, b)
        self.player.keys.add(b)
        self.game.connect(self.player, b)
        self.assertIn(frozenset((a, b)), self.game.conns)
        self.assertNotIn(b, self.player.keys)
        self.player.keys.add(b)
        with self.assertRaises(MoveError):
            self.game.connect(self.player, b)

    def test_crossing_connection_is_rejected(self):
        game = make_game(CROSS_MAP)
        player = game.players[0]
        game.conns.add(frozenset(((6, 2), (2, 6))))
        player.pos = (2, 2)
        for pos in ((2, 2), (6, 6)):
            game.lighthouses[pos].owner = player.num
            game.lighthouses[pos].energy = 10
        player.keys.add((6, 6))
        with self.assertRaises(MoveError):
            game.connect(player, (6, 6))

    def test_connect_through_another_lighthouse_is_rejected(self):
        game = make_game(CROSS_MAP)
        player = game.players[0]
        # (2,2)-(6,6) passes through no lighthouse; add one on the line.
        from lighthouse import Lighthouse
        game.lighthouses[(4, 4)] = Lighthouse(game, (4, 4))
        player.pos = (2, 2)
        for pos in ((2, 2), (6, 6)):
            game.lighthouses[pos].owner = player.num
            game.lighthouses[pos].energy = 10
        player.keys.add((6, 6))
        with self.assertRaises(MoveError):
            game.connect(player, (6, 6))


class _Gamer(object):
    NAME = "stub"

    def __init__(self, play):
        self._play = play
        self.errors = []
        self.successes = 0

    def initialize(self, state):
        pass

    def play(self, state):
        return self._play(state)

    def success(self):
        self.successes += 1

    def error(self, err, move):
        self.errors.append(err)


class BotPlayerTests(unittest.TestCase):
    def turn(self, play):
        game = make_game()
        gamer = _Gamer(play)
        bot = BotPlayer(game, 0, gamer)
        bot.turn()
        return bot, gamer

    def test_crashing_bot_does_not_abort_the_turn(self):
        def boom(state):
            raise RuntimeError("bot bug")
        bot, gamer = self.turn(boom)
        self.assertIsNone(bot.last_move)
        self.assertIsInstance(bot.last_error, CommError)
        self.assertIn("RuntimeError", str(bot.last_error))
        self.assertEqual(gamer.successes, 0)

    def test_valid_pass_is_a_success(self):
        bot, gamer = self.turn(lambda s: {"command": "pass"})
        self.assertIsNone(bot.last_error)
        self.assertEqual(gamer.successes, 1)

    def test_illegal_move_is_reported_to_the_bot(self):
        bot, gamer = self.turn(lambda s: {"command": "move", "x": 5, "y": 5})
        self.assertIsInstance(bot.last_error, MoveError)
        self.assertEqual(len(gamer.errors), 1)

    def test_malformed_command_raises_comm_error(self):
        with self.assertRaises(CommError):
            self.turn(lambda s: "nonsense")


if __name__ == "__main__":
    unittest.main()
