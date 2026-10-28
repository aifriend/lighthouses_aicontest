class MoveError(Exception):
    pass


class GameError(Exception):
    pass


class CommError(Exception):
    pass


class GameConfig(object):
    def __init__(self, mapfile):
        with open(mapfile, "r") as fd:
            lines = [l.replace("\n", "") for l in fd.readlines()]
        self.lighthouses = []
        players = []
        self.island = []
        for y, line in enumerate(lines[::-1]):
            row = []
            for x, c in enumerate(line):
                if c == "#":
                    row.append(0)
                elif c == "!":
                    row.append(1)
                    self.lighthouses.append((x, y))
                elif c == " ":
                    row.append(1)
                else:
                    row.append(1)
                    players.append((c, (x, y)))
            self.island.append(row)
        self.players = [(c, pos) for c, pos in sorted(players)]
        w = len(self.island[0])
        h = len(self.island)
        if not all(len(l) == w for l in self.island):
            raise GameError("All map rows must have the same width")
        if (not all(not i for i in self.island[0]) or
                not all(not i for i in self.island[-1]) or
                not all(not (i[0] or i[-1]) for i in self.island)):
            raise GameError("Map border must not be part of island")
