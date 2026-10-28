from config import MoveError


class Player(object):
    def __init__(self, game, letter, num, pos):
        self.num = num
        self.letter = letter
        self.name = "Player %d" % num
        self.game = game
        self.pos = pos
        self.score = 0
        self.energy = 0
        self.keys = set()

    def move(self, delta):
        dx, dy = delta
        if dx not in (0, 1, -1) or dy not in (0, 1, -1):
            raise MoveError("Delta must be 1 cell away")
        new_pos = self.pos[0] + dx, self.pos[1] + dy
        if not self.game.island[new_pos]:
            raise MoveError("Target pos is not in island")
        self.pos = new_pos
