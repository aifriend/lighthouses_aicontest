"""Presentation-mode broadcast view (1280x720): black stage, big title,
board left/center, right scoreboard, round line and a text-only footer.

Drop-in alternative to GameView for ai_contest.py: same update() /
round_num / paused / handle_events() / close_event() / quit() /
save_screenshot() protocol and FPS handling. Pure pygame, text only
(no image assets).
"""

import math
import os
from datetime import datetime

import pygame

PLAYERC = [
    (255, 0, 0),
    (0, 0, 255),
    (0, 255, 0),
    (255, 255, 0),
    (0, 255, 255),
    (255, 0, 255),
    (255, 127, 0),
    (255, 127, 127),
]

BG = (0, 0, 0)
CELL_WALK = (40, 40, 48)
PANEL = (15, 15, 20)
TEXT = (235, 235, 235)
MUTED = (150, 150, 160)
NEUTRAL_LH = (220, 220, 220)


class PresentationView(object):
    FPS = 100
    WIDTH = 1280
    HEIGHT = 720
    # Board area (left/center) and scoreboard panel (right).
    BX, BY, BW, BH = 24, 84, 920, 552
    PANEL_X = 968

    def __init__(self, game, player_names=None,
                 title="AI CONTEST - LIGHTHOUSE AI",
                 total_rounds=0, game_label="Game 1/1"):
        self.game = game
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption(title)
        self.player_names = player_names or [p.name for p in game.players]
        self.title = title
        self.total_rounds = total_rounds
        self.game_label = game_label
        self.round_num = None
        self.paused = False
        self.nh = game.island.h - 1
        # Largest integer cell size that fits the board area; centered.
        self.cell = max(2, min(self.BW // game.island.w,
                               self.BH // game.island.h))
        self.ox = self.BX + (self.BW - self.cell * game.island.w) // 2
        self.oy = self.BY + (self.BH - self.cell * game.island.h) // 2
        self.font_title = pygame.font.SysFont("Consolas", 42, bold=True)
        self.font_line = pygame.font.SysFont("Consolas", 22, bold=True)
        self.font_small = pygame.font.SysFont("Consolas", 18)
        # Per-frame translucent overlay for triangle fills.
        self.overlay = pygame.Surface((self.WIDTH, self.HEIGHT),
                                      pygame.SRCALPHA)

    @staticmethod
    def player_color(num):
        # Cycle safely when there are more players than base colors.
        return PLAYERC[num % len(PLAYERC)]

    def _px(self, pos):
        """Map cell (x, y-up) to top-left screen pixel of its cell."""
        x, y = pos
        return self.ox + x * self.cell, self.oy + (self.nh - y) * self.cell

    def _center(self, pos):
        px, py = self._px(pos)
        return px + self.cell // 2, py + self.cell // 2

    def update(self, data=None):
        self.screen.fill(BG)
        self.overlay.fill((0, 0, 0, 0))
        self._board()
        self.screen.blit(self.overlay, (0, 0))
        self._markers()
        self._scoreboard()
        self._footer()
        pygame.display.flip()
        pygame.time.Clock().tick(self.FPS)

    def _board(self):
        island = self.game.island
        for cy in range(island.h):
            for cx in range(island.w):
                if not island[cx, cy]:
                    continue  # obstacles stay black
                px, py = self._px((cx, cy))
                self.screen.fill(CELL_WALK, (px, py, self.cell, self.cell))
                # Keep every cell visually distinct instead of merging the
                # island into one flat gray shape.
                pygame.draw.rect(self.screen, (64, 64, 74),
                                 (px, py, self.cell, self.cell), 1)
                energy = island.energy[cx, cy]
                if energy > 0:
                    # Small white energy dot; slightly bigger when rich.
                    r = 1 if energy < 50 else 2
                    pygame.draw.circle(self.screen, (245, 245, 245),
                                       (px + self.cell // 2,
                                        py + self.cell // 2), r)
        # Translucent player-colored triangle fills.
        for tri, cells in self.game.tris.items():
            owner = self.game.lighthouses[tri[0]].owner
            color = self.player_color(owner) + (60,)
            for cell in cells:
                px, py = self._px(cell)
                self.overlay.fill(color, (px, py, self.cell, self.cell))

    def _markers(self):
        # Connection lines between lighthouse centers.
        for (x0, y0), (x1, y1) in self.game.conns:
            owner = self.game.lighthouses[x0, y0].owner
            pygame.draw.line(self.screen, self.player_color(owner),
                             self._center((x0, y0)), self._center((x1, y1)),
                             2)
        # Lighthouses: colored diamonds (neutral = light gray/white).
        size = max(4, int(self.cell * 0.45))
        for pos, lh in self.game.lighthouses.items():
            color = NEUTRAL_LH if lh.owner is None \
                else self.player_color(lh.owner)
            cx, cy = self._center(pos)
            points = [(cx - size, cy), (cx, cy - size),
                      (cx + size, cy), (cx, cy + size)]
            pygame.draw.polygon(self.screen, color, points)
        # Players: colored squares; co-located players share the cell in a
        # mini-grid (same scheme as the engineering view).
        for cy in range(self.game.island.h):
            for cx in range(self.game.island.w):
                c_players = [p for p in self.game.players
                             if p.pos == (cx, cy)]
                if not c_players:
                    continue
                px, py = self._px((cx, cy))
                nx = int(math.ceil(math.sqrt(len(c_players))))
                ny = int(math.ceil(len(c_players) / float(nx)))
                ws = max(2.0, (self.cell - 4) / nx)
                hs = max(2.0, (self.cell - 4) / ny)
                for i, player in enumerate(c_players):
                    ix, iy = i % nx, i // nx
                    rect = (px + 2 + ix * ws, py + 2 + iy * hs,
                            max(2, ws - 1), max(2, hs - 1))
                    pygame.draw.rect(self.screen,
                                     self.player_color(player.num), rect)

    def _scoreboard(self):
        x0 = self.PANEL_X
        pygame.draw.rect(self.screen, PANEL,
                         (x0 - 8, self.BY - 8,
                          self.WIDTH - x0 - 16, self.BH + 16))
        label = self.font_line.render("SCOREBOARD", True, MUTED)
        self.screen.blit(label, (x0, self.BY))
        ranked = sorted(self.game.players, key=lambda p: -p.score)
        y = self.BY + 34
        for player in ranked:
            i = player.num
            name = self.player_names[i] if i < len(self.player_names) \
                else player.name
            line = "%s: %d (%d)" % (name[:14], player.score, player.energy)
            pygame.draw.rect(self.screen, self.player_color(i),
                             (x0, y + 4, 12, 12))
            label = self.font_small.render(line, True, TEXT)
            self.screen.blit(label, (x0 + 20, y))
            y += 26

    def _footer(self):
        if self.round_num is None:
            shown = "-"
            line = "%s - Round %s" % (self.game_label, shown)
        elif self.total_rounds > 0:
            shown = min(self.round_num + 1, self.total_rounds)
            line = "%s - Round %d/%d" % (self.game_label, shown,
                                         self.total_rounds)
        else:
            line = "%s - Round %d" % (self.game_label, self.round_num + 1)
        label = self.font_line.render(line, True, TEXT)
        self.screen.blit(label, (24, self.HEIGHT - 44))
        brand = self.font_small.render("LIGHTHOUSE AI", True, MUTED)
        self.screen.blit(brand, (self.WIDTH - 24 - brand.get_width(),
                                 self.HEIGHT - 40))
        title = self.font_title.render(self.title, True, TEXT)
        self.screen.blit(title, (24, 18))

    def handle_events(self):
        """Process keyboard events; same contract as GameView.handle_events."""
        result = {'quit': False, 'speed': None, 'screenshot': None}
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result['quit'] = True
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    result['quit'] = True
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_s:
                    result['screenshot'] = self.save_screenshot()
        return result

    def save_screenshot(self, path=None):
        if path is None:
            here = os.path.dirname(os.path.abspath(__file__))
            shots_dir = os.path.join(here, '..', 'screenshots')
            os.makedirs(shots_dir, exist_ok=True)
            path = os.path.join(
                shots_dir,
                "lighthouse_%s.png" % datetime.now().strftime("%Y%m%d_%H%M%S"))
        pygame.image.save(self.screen, path)
        return path

    @staticmethod
    def quit():
        pygame.display.quit()

    @staticmethod
    def close_event() -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # This would be a quit event.
                return True  # So the user can close the program
        return False
