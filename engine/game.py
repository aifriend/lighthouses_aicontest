import math

from config import MoveError
from geom import render, distt, intersect, colinear
from island import Island
from lighthouse import Lighthouse
from player import Player


class Game(object):
    RDIST = 5
    DECAY = 10

    def __init__(self, cfg, numplayers=None):
        if numplayers is None:
            numplayers = len(cfg.players)
        assert numplayers <= len(cfg.players)
        self.island = Island(cfg.island)
        self.lighthouses = dict((x, Lighthouse(self, x)) for x in cfg.lighthouses)
        self.conns = set()
        self.tris = dict()
        self.players = [
            Player(self, c, i, pos)
            for i, (c, pos) in enumerate(cfg.players[:numplayers])
        ]

    def connect(self, player, dest_pos):
        if player.pos not in self.lighthouses:
            raise MoveError("Player must be located at the origin lighthouse")
        if dest_pos not in self.lighthouses:
            raise MoveError("Destination must be an existing lighthouse")
        orig = self.lighthouses[player.pos]
        dest = self.lighthouses[dest_pos]
        if orig.owner != player.num or dest.owner != player.num:
            raise MoveError("Both lighthouses must be player-owned")
        if dest.pos not in player.keys:
            raise MoveError("Player does not have the destination key")
        if orig is dest:
            raise MoveError("Cannot connect lighthouse to itself")
        assert orig.energy and dest.energy
        pair = frozenset((orig.pos, dest.pos))
        if pair in self.conns:
            raise MoveError("Connection already exists")
        x0, x1 = sorted((orig.pos[0], dest.pos[0]))
        y0, y1 = sorted((orig.pos[1], dest.pos[1]))
        for lh in self.lighthouses:
            if (x0 <= lh[0] <= x1 and y0 <= lh[1] <= y1 and
                    lh not in (orig.pos, dest.pos) and
                    colinear(orig.pos, dest.pos, lh)):
                raise MoveError("Connection cannot intersect a lighthouse")
        new_tris = set()
        for c in self.conns:
            if intersect(tuple(c), (orig.pos, dest.pos)):
                raise MoveError("Connection cannot intersect another connection")
            if orig.pos in c:
                third = next(l for l in c if l != orig.pos)
                if frozenset((third, dest.pos)) in self.conns:
                    new_tris.add((orig.pos, dest.pos, third))

        player.keys.remove(dest.pos)
        self.conns.add(pair)
        for i in new_tris:
            self.tris[i] = [j for j in render(i) if self.island[j]]

    def pre_round(self):
        # update board energy from lhs
        for pos in self.lighthouses:
            for y in range(pos[1] - self.RDIST + 1, pos[1] + self.RDIST):
                for x in range(pos[0] - self.RDIST + 1, pos[0] + self.RDIST):
                    dist = distt(pos, (x, y))
                    delta = int(math.floor(self.RDIST - dist))
                    if delta > 0:
                        self.island.energy[x, y] += delta

        # get lh key for each player
        player_posmap = dict()
        for player in self.players:
            if player.pos in player_posmap:
                player_posmap[player.pos].append(player)
            else:
                player_posmap[player.pos] = [player]
            if player.pos in self.lighthouses:
                player.keys.add(player.pos)

        # get energy for player
        for pos, players in player_posmap.items():
            energy = self.island.energy[pos] // len(players)
            for player in players:
                player.energy += energy
            self.island.energy[pos] = 0

        # decay lh energy (-10)
        for lh in self.lighthouses.values():
            lh.decay(self.DECAY)

    def post_round(self):
        # scores for lh owned
        for lh in self.lighthouses.values():
            if lh.owner is not None:
                self.players[lh.owner].score += 2

        # score for connections
        for pair in self.conns:
            self.players[self.lighthouses[next(iter(pair))].owner].score += 2

        # score for polygons
        for tri, cells in self.tris.items():
            self.players[self.lighthouses[tri[0]].owner].score += len(cells)
