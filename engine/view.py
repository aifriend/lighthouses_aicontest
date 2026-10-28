import math
import os
from datetime import datetime

import pygame

CELL = 18

# Ocean / lighthouse palette
OCEAN_DEEP = (10, 22, 38)
OCEAN = (16, 34, 56)
OCEAN_LIGHT = (22, 48, 78)
SAND_LOW = (46, 42, 36)
SAND_HIGH = (220, 205, 168)
ENERGY_TINT = (80, 170, 100)
LIGHTHOUSE_BEAM = (255, 245, 180)
LIGHTHOUSE_TOWER = (245, 245, 240)
LIGHTHOUSE_OFF = (130, 130, 130)
TEXT_LIGHT = (250, 250, 245)
TEXT_DIM = (170, 185, 200)
HUD_BG = (14, 26, 42)
HUD_LINE = 26
GRID = (30, 56, 88)

# Friendly, well-separated player colors
PLAYERC = [
    (239, 83, 80),   # red
    (66, 133, 244),  # blue
    (38, 166, 91),   # green
    (251, 188, 5),   # yellow
    (0, 188, 212),   # cyan
    (171, 71, 188),  # purple
    (255, 152, 0),   # orange
    (236, 64, 122),  # pink
]


def _choose_font(preferred, fallback):
    """Return the first system font pygame can find, else fallback."""
    for name in preferred:
        path = pygame.font.match_font(name)
        if path:
            return name
    return fallback


class GameView(object):
    FPS = 100

    def __init__(self, game, player_names=None, scale=2):
        self.game = game
        pygame.init()
        pygame.font.init()
        self.scale = scale
        self.fw = self.game.island.w * CELL * self.scale
        self.fh = self.game.island.h * CELL * self.scale
        self.player_names = player_names or [p.name for p in game.players]
        self.round_num = None
        self.hud_h = max(110, (len(self.game.players) + 1) * HUD_LINE + 18)
        size = self.fw, self.fh + self.hud_h
        self.screen = pygame.display.set_mode(size)
        pygame.display.set_caption("Lighthouse AI — playground")

        self.arena = pygame.Surface((self.fw, self.fh), 0, self.screen)
        self.view = pygame.Surface((self.fw, self.fh), pygame.SRCALPHA, self.screen)
        self.glow = pygame.Surface((self.fw, self.fh), pygame.SRCALPHA, self.screen)
        self.nh = self.game.island.h - 1

        # Fonts: prefer clean UI fonts, fall back to Arial/Consolas
        board_font = _choose_font(["Menlo", "Monaco", "Consolas"], "Consolas")
        label_font = _choose_font(["Helvetica Neue", "Helvetica", "Arial"], "Arial")
        hud_font = _choose_font(["Helvetica Neue", "Helvetica", "Arial Black", "Arial"], "Arial")
        self.my_font_board = pygame.font.SysFont(board_font, 10)
        self.my_font_label = pygame.font.SysFont(label_font, 13)
        self.my_font_hud = pygame.font.SysFont(hud_font, 15)
        self.my_font_pause = pygame.font.SysFont(hud_font, 36)

        # Runtime interactive state
        self.paused = False
        self.speed_mult = 1.0
        self.show_hud = True
        self.show_beams = True
        self.show_vision = True
        self.text_arena = ''
        self._last_beam_angle = 0.0
        self._energy_palette = [
            self._lerp_rgb(SAND_LOW, SAND_HIGH, i / 20.0)
            for i in range(21)
        ]

    def _lerp_rgb(self, a, b, t):
        t = max(0.0, min(1.0, t))
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    def _lerp_energy(self, energy):
        idx = min(20, max(0, int(energy / 100.0 * 20)))
        base = self._energy_palette[idx]
        # shift greener as energy rises
        green = self._lerp_rgb(base, ENERGY_TINT, (energy / 100.0) ** 2 * 0.45)
        return green

    def update(self, data=None):
        # per-frame beam animation
        self._last_beam_angle = (pygame.time.get_ticks() / 1200.0) % (2 * math.pi)

        self.arena.fill(OCEAN_DEEP)
        self.view.fill((0, 0, 0, 0))
        self.glow.fill((0, 0, 0, 0))

        # draw all cells
        for cy in range(self.game.island.h):
            for cx in range(self.game.island.w):
                self.draw_cell((cx, cy))

        # draw connection beams (glowing owner links)
        for (x0, y0), (x1, y1) in self.game.conns:
            owner = self.game.lighthouses[x0, y0].owner
            color = PLAYERC[owner]
            y0f, y1f = self.nh - y0, self.nh - y1
            self._glow_line(
                (x0 * CELL + CELL / 2, y0f * CELL + CELL / 2),
                (x1 * CELL + CELL / 2, y1f * CELL + CELL / 2),
                color,
            )

        if isinstance(data, DataView):
            data.to_show(self)

        self._view()

        # composite layers: arena -> glow (additive) -> view (alpha) -> screen
        self.screen.blit(self.arena, (0, 0))
        self.screen.blit(self.glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.screen.blit(self.view, (0, 0))

        if self.show_hud:
            self._hud()

        if self.paused:
            self._draw_pause_overlay()

        pygame.display.flip()
        pygame.time.Clock().tick(self.FPS)

    def _hud(self):
        top = self.fh
        # gradient-ish panel
        pygame.draw.rect(self.screen, HUD_BG, (0, top, self.fw, self.hud_h))
        pygame.draw.line(self.screen, OCEAN_LIGHT, (0, top), (self.fw, top), 2)

        # round title
        title = "ROUND %s" % (self.round_num if self.round_num is not None else "-")
        if self.paused:
            title += "  (PAUSED)"
        label = self.my_font_hud.render(title, True, TEXT_LIGHT)
        self.screen.blit(label, (14, top + 10))

        # speed indicator
        speed_text = "speed %.1fx" % self.speed_mult
        speed_label = self.my_font_hud.render(speed_text, True, TEXT_DIM)
        self.screen.blit(speed_label, (14, top + 30))

        # controls hint
        hint = "space pause · +/- speed · B beams · V vision · H hud · S screenshot"
        hint_label = self.my_font_hud.render(hint, True, (90, 110, 135))
        self.screen.blit(hint_label, (self.fw - hint_label.get_width() - 14, top + 10))

        max_score = max(1, max(p.score for p in self.game.players))
        for i, player in enumerate(self.game.players):
            name = self.player_names[i] if i < len(self.player_names) else player.name
            lh_owned = sum(1 for lh in self.game.lighthouses.values() if lh.owner == i)
            y = top + 52 + i * HUD_LINE

            color = PLAYERC[player.num]
            # player chip
            pygame.draw.rect(self.screen, color, (14, y + 4, 14, 14), border_radius=3)
            pygame.draw.rect(self.screen, TEXT_LIGHT, (14, y + 4, 14, 14), 1, border_radius=3)

            # mini score bar
            bar_w = min(120, int(100 * player.score / max_score))
            pygame.draw.rect(self.screen, (40, 60, 90), (36, y + 10, 120, 5), border_radius=2)
            pygame.draw.rect(self.screen, color, (36, y + 10, bar_w, 5), border_radius=2)

            line = ("%-12s  score: %-6d  energy: %-6d  lighthouses: %-3d  pos: %s"
                    % (name, player.score, player.energy, lh_owned, player.pos))
            label = self.my_font_hud.render(line, True, TEXT_LIGHT)
            self.screen.blit(label, (164, y))

    def _draw_pause_overlay(self):
        overlay = pygame.Surface((self.fw, self.fh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))
        text = self.my_font_pause.render("PAUSED", True, TEXT_LIGHT)
        rect = text.get_rect(center=(self.fw // 2, self.fh // 2))
        self.screen.blit(text, rect)

    @staticmethod
    def quit():
        pygame.display.quit()

    def handle_events(self):
        """Process keyboard/mouse events and return a summary dict.

        Returns keys:
            quit: bool
            speed: float|None   multiplier to apply to base delay
            screenshot: str|None a path that was just saved
        """
        result = {'quit': False, 'speed': None, 'screenshot': None}
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result['quit'] = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    result['quit'] = True
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    self.speed_mult = min(8.0, self.speed_mult + 0.5)
                    result['speed'] = self.speed_mult
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.speed_mult = max(0.25, self.speed_mult - 0.5)
                    result['speed'] = self.speed_mult
                elif event.key == pygame.K_r:
                    self.speed_mult = 1.0
                    result['speed'] = 1.0
                elif event.key == pygame.K_b:
                    self.show_beams = not self.show_beams
                elif event.key == pygame.K_v:
                    self.show_vision = not self.show_vision
                elif event.key == pygame.K_h:
                    self.show_hud = not self.show_hud
                elif event.key == pygame.K_s:
                    result['screenshot'] = self.save_screenshot()
        return result

    @staticmethod
    def close_event() -> bool:
        """Legacy quit check. New code should use handle_events()."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                return True
        return False

    def save_screenshot(self, path=None):
        if path is None:
            here = os.path.dirname(os.path.abspath(__file__))
            shots_dir = os.path.join(here, '..', 'screenshots')
            os.makedirs(shots_dir, exist_ok=True)
            path = os.path.join(shots_dir,
                                "lighthouse_%s.png" % datetime.now().strftime("%Y%m%d_%H%M%S"))
        import pygame
        pygame.image.save(self.screen, path)
        return path

    def _afill(self, xy, wh, c):
        x0, y0 = xy
        w, h = wh
        x0 *= self.scale
        y0 *= self.scale
        w *= self.scale
        h *= self.scale
        self.arena.fill(c, (x0, y0, w, h))

    def _rect(self, xy, wh, c, width=0, radius=0):
        x0, y0 = xy
        w, h = wh
        x0 *= self.scale
        y0 *= self.scale
        w *= self.scale
        h *= self.scale
        if radius:
            pygame.draw.rect(self.arena, c, (x0, y0, w, h), width,
                             border_radius=int(radius * self.scale))
        else:
            pygame.draw.rect(self.arena, c, (x0, y0, w, h), width)

    def _aaline(self, xy, x1y1, c):
        x0, y0 = xy
        x1, y1 = x1y1
        x0 *= self.scale
        y0 *= self.scale
        x1 *= self.scale
        y1 *= self.scale
        pygame.draw.aaline(self.arena, c, (x0, y0), (x1, y1))

    def _glow_line(self, xy, x1y1, c):
        """Draw a connection line with a soft additive glow."""
        x0, y0 = xy
        x1, y1 = x1y1
        x0 *= self.scale
        y0 *= self.scale
        x1 *= self.scale
        y1 *= self.scale
        glow_c = c + (70,)
        for off in range(4 * self.scale, 0, -2 * self.scale):
            pygame.draw.line(self.glow, glow_c, (x0, y0), (x1, y1), off)
        pygame.draw.line(self.arena, c, (x0, y0), (x1, y1), 2 * self.scale)

    def _circle(self, cxcy, r, c, width=0):
        cx, cy = cxcy
        cx *= self.scale
        cy *= self.scale
        r *= self.scale
        pygame.draw.circle(self.arena, c, (int(cx), int(cy)), int(r), width)

    def _circle_alpha(self, cxcy, r, c):
        cx, cy = cxcy
        cx *= self.scale
        cy *= self.scale
        r *= self.scale
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, c, (r, r), r)
        self.view.blit(s, (int(cx - r), int(cy - r)))

    def _diamond(self, cxcy, size, c, width=0):
        cx, cy = cxcy
        cx *= self.scale
        cy *= self.scale
        size *= self.scale
        points = [
            (cx - size, cy),
            (cx, cy - size),
            (cx + size, cy),
            (cx, cy + size),
        ]
        pygame.draw.polygon(self.arena, c, points, width)

    def _to_text_board(self, content, pose, color=TEXT_LIGHT):
        x0, y0 = pose
        x0 *= self.scale
        y0 *= self.scale
        shadow = self.my_font_board.render(content, True, (0, 0, 0))
        text = self.my_font_board.render(content, True, color)
        self.arena.blit(shadow, (x0 + 1, y0 + 1))
        self.arena.blit(text, (x0, y0))

    def to_text_label(self, content, pose):
        x0, y0 = pose
        x0 *= self.scale
        y0 *= self.scale
        shadow = self.my_font_label.render(content, True, (0, 0, 0))
        text = self.my_font_label.render(content, True, TEXT_LIGHT)
        self.arena.blit(shadow, (x0 + 1, y0 + 1))
        self.arena.blit(text, (x0, y0))

    def _view(self):
        """Draw player vision radius and tokens."""
        dist = self.game.island.HORIZON
        for player in self.game.players:
            cx, cy = player.pos
            py = (self.nh - cy) * CELL
            px = cx * CELL
            cx_s = px + CELL / 2
            cy_s = py + CELL / 2
            if self.show_vision:
                r = (dist + 0.5) * CELL
                self._circle_alpha((cx_s, cy_s), r, PLAYERC[player.num] + (25,))

        # draw tokens after vision so they sit on top
        for cy in range(self.game.island.h):
            for cx in range(self.game.island.w):
                if not self.game.island[cx, cy]:
                    continue
                c_players = [p for p in self.game.players if p.pos == (cx, cy)]
                if not c_players:
                    continue
                py = (self.nh - cy) * CELL
                px = cx * CELL
                self._draw_player_tokens(px, py, c_players)

    def _draw_player_tokens(self, px, py, players):
        n = len(players)
        if n == 1:
            player = players[0]
            color = PLAYERC[player.num]
            self._circle((px + CELL / 2, py + CELL / 2), CELL * 0.32, color)
            self._circle((px + CELL / 2, py + CELL / 2), CELL * 0.32, TEXT_LIGHT, width=2)
            num = self.my_font_board.render(str(player.num + 1), True, TEXT_LIGHT)
            self.arena.blit(num, (px + CELL / 2 - num.get_width() / 2,
                                  py + CELL / 2 - num.get_height() / 2))
            return

        # multiple players: split cell into a grid of small chips
        nx = int(math.ceil(math.sqrt(n)))
        ny = int(math.ceil(n / float(nx)))
        pad = 2
        chip_w = (CELL - pad * (nx + 1)) / nx
        chip_h = (CELL - pad * (ny + 1)) / ny
        for i, player in enumerate(players):
            iy = i // nx
            ix = i % nx
            x = px + pad + ix * (chip_w + pad)
            y = py + pad + iy * (chip_h + pad)
            color = PLAYERC[player.num]
            self._rect((x, y), (chip_w, chip_h), color, radius=2)

    def _draw_lighthouse_beam(self, px, py, owner):
        if not self.show_beams:
            return
        cx, cy = px + CELL / 2, py + CELL / 2
        length = (self.game.island.HORIZON + 1.5) * CELL
        angle = self._last_beam_angle + (px + py) * 0.07
        spread = 0.25
        p1 = (cx + math.cos(angle - spread) * length,
              cy + math.sin(angle - spread) * length)
        p2 = (cx + math.cos(angle + spread) * length,
              cy + math.sin(angle + spread) * length)
        color = LIGHTHOUSE_BEAM + (12,)
        s = pygame.Surface((self.fw, self.fh), pygame.SRCALPHA)
        pygame.draw.polygon(s, color, [(cx, cy), p1, p2])
        self.view.blit(s, (0, 0))

    def draw_cell(self, cxcy):
        cx, cy = cxcy
        py = (self.nh - cy) * CELL
        px = cx * CELL

        if not self.game.island[cx, cy]:
            # ocean: soft checker pattern
            off = ((cx + cy) % 2) * 4
            c = (OCEAN[0] + off, OCEAN[1] + off, OCEAN[2] + off)
            self._afill((px, py), (CELL, CELL), c)
            return

        energy = self.game.island.energy[cx, cy]
        bg = self._lerp_energy(energy)

        # blend owner influence from triangles
        for vertices, fill in self.game.tris.items():
            if (cx, cy) in fill:
                owner = self.game.lighthouses[vertices[0]].owner
                bg = self.calpha(bg, PLAYERC[owner], 0.18)

        self._afill((px, py), (CELL, CELL), bg)
        # subtle grid line
        self._rect((px, py), (CELL, CELL), GRID, width=1)

        # energy label
        brightness = bg[0] * 0.299 + bg[1] * 0.587 + bg[2] * 0.114
        text_color = (30, 30, 30) if brightness > 150 else TEXT_LIGHT
        self._to_text_board(str(energy), (px + 2, py + 2), text_color)

        if (cx, cy) in self.game.lighthouses:
            lh = self.game.lighthouses[cx, cy]
            color = LIGHTHOUSE_OFF
            if lh.owner is not None:
                color = PLAYERC[lh.owner]
            # tower base
            self._circle((px + CELL / 2, py + CELL / 2), 5, color)
            self._circle((px + CELL / 2, py + CELL / 2), 5, TEXT_LIGHT, width=1)
            # diamond lantern on top
            self._diamond((px + CELL / 2, py + CELL / 2), 3, TEXT_LIGHT, 0)
            # rotating beam
            self._draw_lighthouse_beam(px, py, lh.owner)

    @staticmethod
    def cmul(rgb, mul):
        r, g, b = rgb
        return int(r * mul), int(g * mul), int(b * mul)

    @staticmethod
    def calpha(r1g1b1, r2g2b2, a):
        r1, g1, b1 = r1g1b1
        r2, g2, b2 = r2g2b2
        return (int(r2 * a + r1 * (1 - a)),
                int(g2 * a + g1 * (1 - a)),
                int(b2 * a + b1 * (1 - a)))


class DataView:
    def __init__(self):
        self.off_set = 5
        self.args = dict()

    def update(self, *args):
        self.args = args

    def to_show(self, view: GameView):
        for idx, arg in enumerate(self.args):
            label, value = list(dict(arg).items()).pop()
            if isinstance(value, str):
                value_label = value
            elif isinstance(value, tuple):
                value_label = str(value)
            else:
                value_label = round(value, 3)
            view.to_text_label(
                f"{label}: {value_label}", (105, 1 + (idx * self.off_set)))
