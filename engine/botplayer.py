from config import CommError, MoveError
from process import Process


class BotPlayer(object):
    INIT_TIMEOUT = 2.0
    MOVE_TIMEOUT = 0.1
    MOVE_HARDTIMEOUT = 0.5

    def __init__(self, game, playernum, gamer, debug=False):
        self.alive = True
        self.game = game
        self.player = game.players[playernum]
        self.gamer = gamer
        self.debug = debug
        # Telemetry: last command issued by the bot and the error (if any)
        # it produced. Updated on every turn, success or MoveError.
        self.last_move = None
        self.last_error = None

    def initialize(self):
        if not self.alive:
            return
        state = {
            "player_num": self.player.num,
            "player_count": len(self.game.players),
            "position": self.player.pos,
            "map": self.game.island.map,
            "lighthouses": list(self.game.lighthouses.keys()),
        }
        self.gamer.initialize(state)
        self.player.name = self.gamer.NAME

    def get_state(self):
        if not self.alive:
            return
        lighthouses = []
        for lh in self.game.lighthouses.values():
            connections = [next(l for l in c if l is not lh.pos)
                           for c in self.game.conns if lh.pos in c]
            lighthouses.append({
                "position": lh.pos,
                "owner": lh.owner,
                "energy": lh.energy,
                "connections": connections,
                "have_key": lh.pos in self.player.keys,
            })
        state = {
            "position": self.player.pos,
            "score": self.player.score,
            "energy": self.player.energy,
            "view": self.game.island.get_view(self.player.pos),
            "lighthouses": lighthouses,
        }
        return state

    def turn(self):
        if not self.alive:
            return
        lighthouses = []
        for lh in self.game.lighthouses.values():
            connections = [next(l for l in c if l is not lh.pos)
                           for c in self.game.conns if lh.pos in c]
            lighthouses.append({
                "position": lh.pos,
                "owner": lh.owner,
                "energy": lh.energy,
                "connections": connections,
                "have_key": lh.pos in self.player.keys,
            })
        state = {
            "position": self.player.pos,
            "score": self.player.score,
            "energy": self.player.energy,
            "view": self.game.island.get_view(self.player.pos),
            "lighthouses": lighthouses,
        }
        move = self.gamer.play(Process.fake_link(state))
        self.last_move = move
        if not isinstance(move, dict) or "command" not in move:
            raise CommError("Invalid command structure")
        try:
            if move["command"] == "pass":
                pass
            elif move["command"] == "move":
                if "x" not in move or "y" not in move:
                    raise MoveError("Move command requires x, y")
                self.player.move((move["x"], move["y"]))
            elif move["command"] == "attack":
                if "energy" not in move or not isinstance(move["energy"], int):
                    raise MoveError("Attack command requires integer energy")
                if self.player.pos not in self.game.lighthouses:
                    raise MoveError("Player must be located at target lighthouse")
                self.game.lighthouses[self.player.pos].attack(self.player, move["energy"])
            elif move["command"] == "connect":
                if "destination" not in move:
                    raise MoveError("Connect command requires destination")
                try:
                    dest = tuple(move["destination"])
                    hash(dest)
                except Exception as _:
                    raise MoveError("Destination must be a coordinate pair")
                self.game.connect(self.player, dest)
            else:
                raise MoveError("Invalid command %r" % move["command"])
            self.gamer.success()
            self.last_error = None
        except MoveError as e:
            # sys.stderr.write("Bot %r move error: %s\n" % (self.player.name, e.message))
            self.last_error = e
            self.gamer.error(e, move)

    def close(self):
        if self.alive:
            # sys.stderr.write("Bot %r exit\n" % self.player.name)
            self.alive = False

    def __del__(self):
        self.close()
