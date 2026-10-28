import sys

from config import MoveError


class Lighthouse(object):
    def __init__(self, game, pos):
        self.game = game
        self.pos = pos
        self.owner = None
        self.energy = 0

    def attack(self, player, strength):
        if not isinstance(strength, int):
            raise MoveError("Strength must be an int")
        if strength < 0:
            raise MoveError("Strength must be positive")
        if strength > player.energy:
            strength = player.energy
        player.energy -= strength
        if self.owner is not None and self.owner != player.num:
            d = min(self.energy, strength)
            self.decay(d)
            strength -= d
        if strength:
            self.owner = player.num
            self.energy += strength

    def owned(self, player):
        self.owner = player.num
        self.energy += sys.maxsize

    def decay(self, by):
        self.energy -= by
        if self.energy <= 0:
            self.energy = 0
            self.owner = None
            self.game.conns = set(i for i in self.game.conns if self.pos not in i)
            self.game.tris = dict(i for i in self.game.tris.items() if self.pos not in i[0])
