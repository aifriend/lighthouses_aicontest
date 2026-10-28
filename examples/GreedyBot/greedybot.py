#!/usr/bin/python
# -*- coding: utf-8 -*-

import math
import random
import sys

import interface


class GreedyBot(interface.Bot):
    """Bot de ejemplo codicioso.

    Se mueve hacia la casilla visible con más energía (desempatando hacia
    el faro más cercano) y, cuando está sobre un faro, conecta faros
    propios o ataca/recarga con la mitad de su energía.
    """
    NAME = "GreedyBot"

    MOVES = ((-1, -1), (-1, 0), (-1, 1), (0, -1),
             (0, 1), (1, -1), (1, 0), (1, 1))

    def play(self, state):
        """Jugar: llamado cada turno.
        Debe devolver una acción (jugada)."""
        cx, cy = state["position"]
        lighthouses = dict((tuple(lh["position"]), lh)
                           for lh in state["lighthouses"])

        # Si estamos en un faro...
        if (cx, cy) in self.lighthouses:
            here = lighthouses[(cx, cy)]
            # Conectar con el primer faro propio para el que tengamos clave
            if here["owner"] == self.player_num:
                for dest in self.lighthouses:
                    other = lighthouses[dest]
                    if (dest != (cx, cy)
                            and other["owner"] == self.player_num
                            and other["have_key"]
                            and [cx, cy] not in other["connections"]):
                        return self.connect(dest)
            # Atacar/recargar con la mitad de la energía acumulada
            if state["energy"] > 1:
                return self.attack(state["energy"] // 2)

        # Mover a la casilla válida con más energía visible; a igualdad de
        # energía, la más cercana al faro más próximo.
        horizon = len(state["view"]) // 2
        best, best_key = None, None
        for dx, dy in self.MOVES:
            nx, ny = cx + dx, cy + dy
            if not (0 <= ny < len(self.map) and 0 <= nx < len(self.map[0])):
                continue
            if not self.map[ny][nx]:
                continue
            energy = state["view"][dy + horizon][dx + horizon]
            nearest = min(math.hypot(nx - lx, ny - ly)
                          for lx, ly in self.lighthouses)
            key = (energy, -nearest, random.random())
            if best_key is None or key > best_key:
                best, best_key = (dx, dy), key
        if best is None:
            return self.nop()
        return self.move(*best)


if __name__ == "__main__":
    iface = interface.Interface(GreedyBot)
    iface.run()
