import io
import json
import math
import random
from enum import Enum
from pathlib import Path

import cairosvg
import pygame

WIDTH, HEIGHT = 1280, 720
FPS = 60
ASSET_DIR = Path(__file__).parent / "assets"
BANK_RIGHT = 340
WATER_TOP = 460
WATER_BOTTOM = HEIGHT - 10
SAVE_PATH = Path.home() / ".fox_fishing_save.json"

pygame.init()
pygame.font.init()

FONT_BIG = pygame.font.SysFont("DejaVu Sans", 48, bold=True)
FONT_MED = pygame.font.SysFont("DejaVu Sans", 22, bold=True)
FONT_SMALL = pygame.font.SysFont("DejaVu Sans", 16)
FONT_TINY = pygame.font.SysFont("DejaVu Sans", 14)


def load_svg(name, size):
    png = cairosvg.svg2png(url=str(ASSET_DIR / name),
                           output_width=size[0], output_height=size[1])
    return pygame.image.load(io.BytesIO(png)).convert_alpha()


UPGRADES = {
    'reel': {
        'name': 'Szybkość zwijania',
        'desc': '+8% szybkosci postepu w minigrze',
        'base_cost': 80, 'mult': 1.45,
    },
    'zone': {
        'name': 'Wieksza strefa',
        'desc': '+0.008 wysokosci zielonej strefy',
        'base_cost': 100, 'mult': 1.50,
    },
    'patience': {
        'name': 'Cierpliwosc',
        'desc': '+0.4s czasu w minigrze',
        'base_cost': 70, 'mult': 1.40,
    },
    'bait': {
        'name': 'Przyneta',
        'desc': '+10% zainteresowania ryb',
        'base_cost': 60, 'mult': 1.35,
    },
    'power': {
        'name': 'Moc rzutu',
        'desc': '+10% maksymalnego zasiegu',
        'base_cost': 50, 'mult': 1.40,
    },
    'luck': {
        'name': 'Szczescie',
        'desc': '+15% szans na rzadkie ryby',
        'base_cost': 120, 'mult': 1.50,
    },
}

UPGRADE_ORDER = ['reel', 'zone', 'patience', 'bait', 'power', 'luck']


def upgrade_cost(key, level):
    u = UPGRADES[key]
    return int(u['base_cost'] * (u['mult'] ** level))


def upgrade_effect(key, level):
    if key == 'reel':
        return 1.0 + 0.08 * level
    if key == 'zone':
        return min(0.65, 0.22 + 0.008 * level)
    if key == 'patience':
        return 0.4 * level
    if key == 'bait':
        return 1.0 + 0.10 * level
    if key == 'power':
        return 1.0 + 0.10 * level
    if key == 'luck':
        return 0.15 * level
    return 1.0


def load_save():
    try:
        with open(SAVE_PATH) as f:
            data = json.load(f)
        score = int(data.get('score', 0))
        levels = {k: int(data.get('upgrade_levels', {}).get(k, 0))
                  for k in UPGRADES}
        return score, levels
    except Exception:
        return 0, {k: 0 for k in UPGRADES}


def save_game(score, levels):
    try:
        with open(SAVE_PATH, 'w') as f:
            json.dump({'score': score, 'upgrade_levels': levels}, f)
    except Exception:
        pass


class Species:
    def __init__(self, name, color, size, depth_min, depth_max,
                 speed, difficulty, weight, danger=0.0):
        self.name = name
        self.color = color
        self.size = size
        self.depth_min = depth_min
        self.depth_max = depth_max
        self.speed = speed
        self.difficulty = difficulty
        self.weight = weight
        self.danger = danger


SPECIES = [
    Species("Plotka",       (170, 210, 100), 0.55, 0.05, 0.30,  90, 0.7, 12, 0.0),
    Species("Okon",         (230, 180,  80), 0.75, 0.15, 0.45, 110, 0.9, 10, 0.1),
    Species("Karp",         (200, 150, 100), 1.10, 0.30, 0.55,  70, 1.1,  7, 0.2),
    Species("Szczupak",     ( 90, 130,  70), 1.35, 0.35, 0.65, 150, 1.5,  4, 0.5),
    Species("Sum",          ( 80,  60,  50), 1.50, 0.55, 0.80,  80, 1.4,  3, 0.4),
    Species("Zlota rybka",  (255, 215,  80), 0.55, 0.75, 0.95, 130, 1.7,  1, 0.5),
]

TOTAL_WEIGHT = sum(s.weight for s in SPECIES)


def pick_species(luck_bonus=0.0):
    if luck_bonus > 0 and random.random() < min(0.7, luck_bonus):
        rare = [s for s in SPECIES if s.weight <= 4]
        if rare:
            total = sum(s.weight for s in rare)
            r = random.uniform(0, total)
            acc = 0.0
            for s in rare:
                acc += s.weight
                if r <= acc:
                    return s
            return rare[-1]

    r = random.uniform(0, TOTAL_WEIGHT)
    acc = 0.0
    for s in SPECIES:
        acc += s.weight
        if r <= acc:
            return s
    return SPECIES[-1]


def make_fish_surface(color, scale):
    w = max(30, int(60 * scale))
    h = max(20, int(40 * scale))
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cy = h // 2
    body_w = int(w * 0.75)
    body_h = int(h * 0.75)
    body_x = 2
    body_y = (h - body_h) // 2

    pygame.draw.ellipse(surf, color, (body_x, body_y, body_w, body_h))
    dark = tuple(max(0, c - 50) for c in color)
    pygame.draw.ellipse(surf, dark,
                        (body_x + 4, body_y + body_h // 2,
                         body_w - 8, max(2, body_h // 2 - 2)))
    tail_x = body_x + body_w - 4
    pygame.draw.polygon(surf, color, [
        (tail_x, cy),
        (w - 2, cy - body_h // 2),
        (w - 2, cy + body_h // 2)
    ])
    eye_x = body_x + max(6, int(8 * scale))
    eye_r = max(2, int(3 * scale))
    pygame.draw.circle(surf, (255, 255, 255), (eye_x, cy - 3), eye_r)
    pygame.draw.circle(surf, (0, 0, 0), (eye_x, cy - 3), max(1, eye_r - 1))
    return surf


class State(Enum):
    CASTING = 1
    BITE = 2
    MINIGAME = 3
    CAUGHT = 4


class Fish:
    def __init__(self, species=None, luck_bonus=0.0):
        self.species = species or pick_species(luck_bonus)
        self.img_r = make_fish_surface(self.species.color, self.species.size)
        self.img_l = pygame.transform.flip(self.img_r, True, False)
        self.interest = 0.0
        self.reset()

    def reset(self):
        self.x = random.uniform(BANK_RIGHT + 120, WIDTH - 100)
        self.depth = random.uniform(self.species.depth_min, self.species.depth_max)
        self.vx = random.choice([-1, 1]) * self.species.speed
        self.t = random.uniform(0, 10)

    @property
    def y(self):
        return WATER_TOP + self.depth * (WATER_BOTTOM - WATER_TOP)

    def update(self, dt, bobber, state, bait_mult=1.0):
        self.t += dt
        self.x += self.vx * dt
        if self.x < BANK_RIGHT + 60:
            self.x = BANK_RIGHT + 60
            self.vx = abs(self.vx)
        if self.x > WIDTH - 60:
            self.x = WIDTH - 60
            self.vx = -abs(self.vx)

        if state == State.CASTING and bobber.landed:
            dx = abs(self.x - bobber.x)
            dd = abs(self.depth - bobber.depth)
            if dx < 90 and dd < 0.10:
                rate = 1.5 * (1 - dx / 90) * (1 - dd / 0.10) * bait_mult
                self.interest += rate * dt
            else:
                self.interest = max(0, self.interest - 0.4 * dt)
        else:
            self.interest = max(0, self.interest - 0.5 * dt)

    def draw(self, surf):
        img = self.img_r if self.vx > 0 else self.img_l
        bob = math.sin(self.t * 5) * 2
        px = self.x - img.get_width() / 2
        py = self.y - img.get_height() / 2 + bob

        if self.interest > 0.3:
            alpha = int(150 * min(1.0, (self.interest - 0.3) / 0.7))
            glow = pygame.Surface((img.get_width() + 20, img.get_height() + 20),
                                  pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 240, 100, alpha),
                                (0, 0, glow.get_width(), glow.get_height()))
            surf.blit(glow, (int(px) - 10, int(py) - 10))

        surf.blit(img, (int(px), int(py)))


class Bobber:
    def __init__(self):
        self.x = BANK_RIGHT + 200
        self.depth = 0.0
        self.flying = False
        self.landed = False
        self.target_x = self.x
        self.start_x = self.x
        self.flight_t = 0.0
        self.flight_dur = 0.7
        self.t = 0.0

    @property
    def y(self):
        return WATER_TOP + self.depth * (WATER_BOTTOM - WATER_TOP)

    def cast_to(self, tx):
        self.start_x = BANK_RIGHT + 20
        self.target_x = tx
        self.x = self.start_x
        self.flying = True
        self.landed = False
        self.flight_t = 0.0
        self.depth = 0.0

    def update(self, dt, keys):
        if self.flying:
            self.flight_t += dt
            k = min(1.0, self.flight_t / self.flight_dur)
            self.x = self.start_x + (self.target_x - self.start_x) * k
            if k >= 1.0:
                self.flying = False
                self.landed = True
                self.depth = 0.0
                self.t = 0.0
                return True
            return False

        if self.landed:
            self.t += dt
            delta = 0.0
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                delta = 1.0
            elif keys[pygame.K_w] or keys[pygame.K_UP]:
                delta = -1.0
            else:
                delta = 0.3
            self.depth += delta * dt * 0.4
            self.depth = max(0.0, min(1.0, self.depth))
        return False


class Minigame:
    def __init__(self, species, depth, levels):
        self.species = species
        self.depth = depth
        self.green_y = 0.4
        self.green_v = 0.0
        self.green_h = upgrade_effect('zone', levels['zone'])
        self.fish_y = 0.5
        self.fish_v = 0.0
        self.progress = 0.5
        self.finished = False
        self.won = False
        self.stolen = False
        self.reel_mult = upgrade_effect('reel', levels['reel'])

        base_time = 9.0 - depth * 4.0 - species.danger * 3.0
        patience_bonus = upgrade_effect('patience', levels['patience'])
        self.time_left = max(4.0, base_time) + patience_bonus
        self.time_total = self.time_left
        self.predator_threat = (species.danger > 0.25
                                and random.random() < species.danger)

    def update(self, dt, mouse_down):
        if self.finished:
            return

        self.time_left -= dt
        if self.time_left <= 0:
            self.finished = True
            self.won = False
            self.stolen = self.predator_threat
            return

        if mouse_down:
            self.green_v += 3.0 * dt
        else:
            self.green_v -= 4.0 * dt
        self.green_v = max(-1.3, min(1.3, self.green_v))
        self.green_y += self.green_v * dt
        if self.green_y < 0:
            self.green_y = 0
            self.green_v = 0
        if self.green_y > 1 - self.green_h:
            self.green_y = 1 - self.green_h
            self.green_v = 0

        agility = 2.5 + self.species.difficulty * 1.5
        max_v = 0.9 + self.species.difficulty * 0.3
        self.fish_v += random.uniform(-1, 1) * agility * dt
        self.fish_v = max(-max_v, min(max_v, self.fish_v))
        self.fish_y += self.fish_v * dt
        if self.fish_y < 0.02:
            self.fish_y = 0.02
            self.fish_v = abs(self.fish_v)
        if self.fish_y > 0.92:
            self.fish_y = 0.92
            self.fish_v = -abs(self.fish_v)

        in_zone = (self.fish_y + 0.06 >= self.green_y
                   and self.fish_y <= self.green_y + self.green_h)
        speed = (0.4 - self.species.difficulty * 0.06) * self.reel_mult
        if in_zone:
            self.progress += speed * dt
        else:
            self.progress -= 0.30 * dt
        self.progress = max(0.0, min(1.0, self.progress))

        if self.progress >= 1.0:
            self.finished = True
            self.won = True
        elif self.progress <= 0.0:
            self.finished = True
            self.won = False


class Ripple:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.t = 0.0
        self.max_t = 0.9

    def update(self, dt):
        self.t += dt
        return self.t < self.max_t

    def draw(self, surf):
        k = self.t / self.max_t
        r = int(8 + k * 60)
        alpha = int(200 * (1 - k))
        if alpha <= 0 or r <= 0:
            return
        s = pygame.Surface((r * 2 + 4, r + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (255, 255, 255, alpha), (2, 2, r * 2, r))
        surf.blit(s, (int(self.x - r), int(self.y - 2)))


class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.vx = random.uniform(-220, 220)
        self.vy = random.uniform(-320, -80)
        self.t = 0.0
        self.max_t = random.uniform(0.7, 1.3)
        self.color = color
        self.size = random.randint(3, 7)

    def update(self, dt):
        self.t += dt
        self.vy += 600 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.t < self.max_t

    def draw(self, surf):
        k = 1 - self.t / self.max_t
        alpha = int(255 * k)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha),
                           (self.size, self.size), self.size)
        surf.blit(s, (int(self.x - self.size), int(self.y - self.size)))


class FloatingText:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.t = 0.0
        self.duration = 2.0

    def update(self, dt):
        self.t += dt
        self.y -= 40 * dt
        return self.t < self.duration

    def draw(self, surf):
        alpha = int(255 * (1 - self.t / self.duration))
        s = FONT_MED.render(self.text, True, self.color)
        s.set_alpha(alpha)
        surf.blit(s, (self.x - s.get_width() / 2,
                      self.y - s.get_height() / 2))


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Fox Fishing")
        self.clock = pygame.time.Clock()

        self.fox_img = load_svg("fox.svg", (180, 220))

        self.score, self.levels = load_save()

        self.fish_population = [
            Fish(luck_bonus=upgrade_effect('luck', self.levels['luck']))
            for _ in range(10)
        ]
        self.bobber = Bobber()
        self.minigame = None
        self.state = State.CASTING
        self.time = 0.0

        self.cast_charging = False
        self.cast_power = 0.0

        self.bite_timer = 0.0
        self.hooked_fish = None

        self.ripples = []
        self.particles = []
        self.floating_texts = []

        self.msg = ""
        self.msg_timer = 0.0

        self.menu_open = False
        self.menu_rects = []
        self.hint_msg = ""
        self.hint_timer = 0.0

        self.bg = self.make_bg()

    def make_bg(self):
        surf = pygame.Surface((WIDTH, HEIGHT))
        for y in range(WATER_TOP):
            k = y / WATER_TOP
            r = int(120 + 100 * k)
            g = int(180 + 40 * k)
            b = int(230 + 15 * k)
            pygame.draw.line(surf, (r, g, b), (0, y), (WIDTH, y))
        pygame.draw.circle(surf, (255, 235, 170), (1060, 130), 70)
        pygame.draw.circle(surf, (255, 250, 210), (1060, 130), 45)
        for cx, cy, r in [(200, 100, 40), (280, 110, 30),
                          (760, 150, 45), (830, 155, 35)]:
            s = pygame.Surface((r * 4, r * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (255, 255, 255, 200), (0, 0, r * 4, r * 2))
            surf.blit(s, (cx, cy))

        pygame.draw.rect(surf, (60, 130, 55),
                         (0, WATER_TOP - 40, BANK_RIGHT,
                          HEIGHT - WATER_TOP + 40))
        pygame.draw.rect(surf, (90, 170, 70),
                         (0, WATER_TOP - 40, BANK_RIGHT, 10))

        rng = random.Random(123)
        for _ in range(30):
            gx = rng.randint(0, BANK_RIGHT - 20)
            gy = WATER_TOP - 40 + rng.randint(2, 6)
            pygame.draw.line(surf, (40, 100, 40),
                             (gx, gy), (gx - 2, gy - 8), 2)
            pygame.draw.line(surf, (40, 100, 40),
                             (gx + 4, gy), (gx + 6, gy - 7), 2)

        pygame.draw.rect(surf, (95, 65, 35),
                         (0, WATER_TOP, BANK_RIGHT, HEIGHT - WATER_TOP))
        for _ in range(100):
            dx = rng.randint(0, BANK_RIGHT - 10)
            dy = rng.randint(WATER_TOP + 10, HEIGHT - 10)
            c = rng.choice([(80, 50, 25), (110, 80, 45)])
            pygame.draw.circle(surf, c, (dx, dy), rng.randint(1, 3))
        return surf

    def reset_fish_interest(self):
        for f in self.fish_population:
            f.interest = 0.0

    def retrieve_bobber(self):
        self.bobber = Bobber()
        self.reset_fish_interest()

    def trigger_bite(self, fish):
        self.hooked_fish = fish
        self.state = State.BITE
        self.bite_timer = 0.0

    def start_minigame(self):
        if self.hooked_fish:
            self.minigame = Minigame(
                self.hooked_fish.species,
                self.hooked_fish.depth,
                self.levels,
            )
        else:
            self.minigame = Minigame(SPECIES[0], 0.3, self.levels)
        self.state = State.MINIGAME

    def finalize_minigame(self):
        if self.minigame.won and self.hooked_fish:
            sp = self.hooked_fish.species
            depth = self.hooked_fish.depth
            points = int((20 / math.sqrt(sp.weight)) + depth * 30)
            self.score += points
            self.floating_texts.append(FloatingText(
                WIDTH / 2, 250, f"+{points} ({sp.name})", (255, 240, 150)
            ))
            if self.hooked_fish in self.fish_population:
                self.fish_population.remove(self.hooked_fish)
                self.fish_population.append(Fish(
                    luck_bonus=upgrade_effect('luck', self.levels['luck'])
                ))
            self.msg = f"Zlowiono: {sp.name}!"
            for _ in range(35):
                self.particles.append(Particle(
                    WIDTH / 2 + random.uniform(-150, 150),
                    HEIGHT / 2 + random.uniform(-80, 80),
                    random.choice([(255, 220, 100), (255, 150, 60),
                                   (255, 255, 255)])
                ))
        elif self.minigame.stolen:
            self.msg = "Zjedzona przez drapieznika!"
        else:
            self.msg = "Uciekla!"
        self.msg_timer = 1.8
        self.state = State.CAUGHT
        self.hooked_fish = None
        save_game(self.score, self.levels)

    def update(self, dt, mouse_down, keys):
        self.time += dt
        if self.msg_timer > 0:
            self.msg_timer -= dt
        if self.hint_timer > 0:
            self.hint_timer -= dt

        self.ripples = [r for r in self.ripples if r.update(dt)]
        self.particles = [p for p in self.particles if p.update(dt)]
        self.floating_texts = [t for t in self.floating_texts if t.update(dt)]

        if self.state == State.CASTING:
            landed = self.bobber.update(dt, keys)
            if landed:
                self.ripples.append(Ripple(self.bobber.x, self.bobber.y))

            bait_mult = upgrade_effect('bait', self.levels['bait'])
            for f in self.fish_population:
                f.update(dt, self.bobber, self.state, bait_mult)

            if self.bobber.landed:
                best = None
                for f in self.fish_population:
                    if f.interest > 1.0 and (best is None
                                             or f.interest > best.interest):
                        best = f
                if best is not None:
                    self.trigger_bite(best)

        elif self.state == State.BITE:
            self.bite_timer += dt
            if self.bite_timer > 1.5:
                self.msg = "Uciekla!"
                self.msg_timer = 1.2
                self.hooked_fish = None
                self.retrieve_bobber()
                self.state = State.CASTING

        elif self.state == State.MINIGAME:
            self.minigame.update(dt, mouse_down)
            if self.minigame.finished:
                self.finalize_minigame()

        elif self.state == State.CAUGHT:
            if self.msg_timer <= 0:
                self.retrieve_bobber()
                self.state = State.CASTING

    def buy_upgrade(self, key):
        level = self.levels[key]
        cost = upgrade_cost(key, level)
        if self.score < cost:
            self.hint_msg = "Za malo punktow!"
            self.hint_timer = 1.5
            return
        self.score -= cost
        self.levels[key] = level + 1
        if key == 'luck':
            self.fish_population = [
                Fish(luck_bonus=upgrade_effect('luck', self.levels['luck']))
                for _ in range(10)
            ]
        self.hint_msg = f"Kupiono: {UPGRADES[key]['name']} (poz. {level+1})"
        self.hint_timer = 1.5
        save_game(self.score, self.levels)

    def draw_water(self):
        water_h = HEIGHT - WATER_TOP
        for y in range(WATER_TOP, HEIGHT, 4):
            k = (y - WATER_TOP) / water_h
            r = int(40 + 20 * k)
            g = int(140 - 60 * k)
            b = int(200 - 70 * k)
            if k < 0.3:
                g += 20
            elif k > 0.6:
                r -= 10
                g -= 30
                b -= 20
            pygame.draw.line(self.screen, (r, g, b),
                             (BANK_RIGHT, y), (WIDTH, y))

        for i in range(10):
            yy = WATER_TOP + 20 + i * 25
            if yy >= HEIGHT:
                break
            pts = []
            for x in range(BANK_RIGHT, WIDTH + 20, 20):
                yy_w = yy + math.sin(x * 0.02 + self.time * 1.6 + i * 0.8) * 3
                pts.append((int(x), int(yy_w)))
            if len(pts) >= 2:
                pygame.draw.lines(self.screen, (110, 190, 230), False, pts, 1)

    def draw_depth_marker(self):
        mx = WIDTH - 55
        my_top = WATER_TOP + 20
        my_bot = WATER_BOTTOM - 20
        my_h = my_bot - my_top

        pygame.draw.rect(self.screen, (30, 30, 40),
                         (mx - 5, my_top - 5, 26, my_h + 10), border_radius=6)
        pygame.draw.rect(self.screen, (60, 140, 100),
                         (mx, my_top, 16, int(my_h * 0.3)))
        pygame.draw.rect(self.screen, (40, 90, 160),
                         (mx, my_top + int(my_h * 0.3), 16, int(my_h * 0.3)))
        pygame.draw.rect(self.screen, (20, 40, 100),
                         (mx, my_top + int(my_h * 0.6), 16, int(my_h * 0.4)))
        pygame.draw.rect(self.screen, (120, 180, 240),
                         (mx, my_top, 16, my_h), 2, border_radius=4)

        marker_y = my_top + int(my_h * self.bobber.depth)
        pygame.draw.polygon(self.screen, (255, 200, 50), [
            (mx - 10, marker_y),
            (mx - 2, marker_y - 6),
            (mx - 2, marker_y + 6),
        ])

        for pct, label in [(0.15, "Plytko"), (0.45, "Srodek"), (0.80, "Gleboko")]:
            t = FONT_TINY.render(label, True, (220, 230, 255))
            self.screen.blit(t, (mx - 66, my_top + int(my_h * pct) - 8))

        d_txt = FONT_TINY.render(f"{int(self.bobber.depth * 100)}%",
                                 True, (255, 240, 180))
        self.screen.blit(d_txt, (mx, my_top + my_h + 8))

    def draw_bobber(self):
        if not self.bobber.landed and not self.bobber.flying:
            return
        rod_tip = (BANK_RIGHT - 20, WATER_TOP - 30)
        if self.bobber.flying:
            k = self.bobber.flight_t / self.bobber.flight_dur
            bob_y = WATER_TOP - math.sin(k * math.pi) * 120
            bob_x = self.bobber.x
        else:
            bob_y = self.bobber.y + math.sin(self.time * 4) * 2
            bob_x = self.bobber.x

        pygame.draw.line(self.screen, (240, 240, 240),
                         rod_tip, (int(bob_x), int(bob_y - 4)), 1)

        if self.bobber.landed and self.bobber.depth > 0.01:
            s = pygame.Surface((1, int(self.bobber.y - WATER_TOP)),
                               pygame.SRCALPHA)
            s.fill((150, 200, 255, 120))
            self.screen.blit(s, (int(bob_x), WATER_TOP))

        pygame.draw.circle(self.screen, (220, 40, 40),
                           (int(bob_x), int(bob_y)), 8)
        pygame.draw.circle(self.screen, (245, 245, 245),
                           (int(bob_x), int(bob_y) + 4), 6)
        pygame.draw.circle(self.screen, (60, 60, 60),
                           (int(bob_x), int(bob_y)), 8, 1)

    def draw_minigame(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 540, 560
        px = WIDTH / 2 - pw / 2
        py = HEIGHT / 2 - ph / 2
        pygame.draw.rect(self.screen, (30, 40, 60),
                         (px, py, pw, ph), border_radius=16)
        pygame.draw.rect(self.screen, (80, 140, 220),
                         (px, py, pw, ph), 3, border_radius=16)

        title = FONT_MED.render(
            f"Zlow: {self.minigame.species.name}!", True, (240, 240, 240))
        self.screen.blit(title,
                         (WIDTH / 2 - title.get_width() / 2, py + 20))

        time_ratio = self.minigame.time_left / self.minigame.time_total
        tb_w = pw - 80
        tb_x = px + 40
        tb_y = py + 60
        pygame.draw.rect(self.screen, (20, 20, 30),
                         (tb_x, tb_y, tb_w, 16), border_radius=4)
        tw = int(tb_w * time_ratio)
        if time_ratio < 0.3:
            flash = int(155 + 100 * math.sin(self.time * 20))
            col = (255, flash, 80)
        else:
            col = (255, 180, 60)
        pygame.draw.rect(self.screen, col,
                         (tb_x, tb_y, tw, 16), border_radius=4)
        pygame.draw.rect(self.screen, (200, 200, 200),
                         (tb_x, tb_y, tb_w, 16), 2, border_radius=4)

        bar_x = px + 70
        bar_y = py + 120
        bar_w = 70
        bar_h = ph - 200

        for i in range(bar_h):
            k = i / bar_h
            c = (int(20 + 60 * k), int(80 + 70 * k), int(170 + 40 * k))
            pygame.draw.line(self.screen, c,
                             (bar_x, bar_y + i), (bar_x + bar_w, bar_y + i))
        pygame.draw.rect(self.screen, (150, 200, 255),
                         (bar_x, bar_y, bar_w, bar_h), 2)

        gz_y = bar_y + (1 - self.minigame.green_y
                        - self.minigame.green_h) * bar_h
        gz_h = self.minigame.green_h * bar_h
        pulse = 0.5 + 0.5 * math.sin(self.time * 6)
        gz = pygame.Surface((bar_w, int(gz_h)), pygame.SRCALPHA)
        gz.fill((60, 220, 90, int(150 + 70 * pulse)))
        self.screen.blit(gz, (bar_x, gz_y))
        pygame.draw.rect(self.screen, (150, 255, 170),
                         (bar_x, gz_y, bar_w, gz_h), 2, border_radius=4)

        fish_y = bar_y + (1 - self.minigame.fish_y) * bar_h
        pygame.draw.ellipse(self.screen, (255, 255, 255),
                            (bar_x + bar_w / 2 - 22, fish_y - 10, 44, 22))
        pygame.draw.ellipse(self.screen, self.minigame.species.color,
                            (bar_x + bar_w / 2 - 22, fish_y - 10, 44, 22), 2)

        prog_x = px + pw - 120
        prog_y = bar_y
        prog_w = 40
        prog_h = bar_h
        pygame.draw.rect(self.screen, (40, 40, 50),
                         (prog_x, prog_y, prog_w, prog_h), border_radius=8)
        fill_h = int(self.minigame.progress * prog_h)
        for i in range(fill_h):
            k = i / max(1, fill_h)
            c = (int(255), int(150 + 80 * k), int(40))
            pygame.draw.line(self.screen, c,
                             (prog_x + 2, prog_y + prog_h - i),
                             (prog_x + prog_w - 2, prog_y + prog_h - i))
        pygame.draw.rect(self.screen, (200, 200, 200),
                         (prog_x, prog_y, prog_w, prog_h), 2, border_radius=8)

        if self.minigame.predator_threat:
            tx, ty = px + pw - 60, py + 20
            pygame.draw.polygon(self.screen, (255, 80, 80), [
                (tx, ty), (tx - 20, ty + 30), (tx + 20, ty + 30)
            ])
            pygame.draw.polygon(self.screen, (200, 50, 50), [
                (tx, ty), (tx - 20, ty + 30), (tx + 20, ty + 30)
            ], 2)
            warn = FONT_MED.render("!", True, (255, 255, 255))
            self.screen.blit(warn, (tx - warn.get_width() / 2, ty + 6))
            t = FONT_TINY.render("Drapieznik!", True, (255, 150, 150))
            self.screen.blit(t, (tx - t.get_width() / 2, ty + 35))

        hint = FONT_SMALL.render(
            "LPM = podnos zielona strefe | Utrzymaj rybe w strefie",
            True, (220, 220, 220))
        self.screen.blit(hint,
                         (WIDTH / 2 - hint.get_width() / 2, py + ph - 36))

    def draw_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        title = FONT_BIG.render("Ulepszenia", True, (255, 255, 255))
        self.screen.blit(title, (WIDTH / 2 - title.get_width() / 2, 25))

        score_txt = FONT_MED.render(f"Punkty: {self.score}",
                                    True, (255, 220, 120))
        self.screen.blit(score_txt,
                         (WIDTH / 2 - score_txt.get_width() / 2, 95))

        cols = 2
        rows = 3
        box_w = 540
        box_h = 140
        gap = 20
        total_w = cols * box_w + (cols - 1) * gap
        start_x = WIDTH / 2 - total_w / 2
        start_y = 160

        self.menu_rects = []
        for i, key in enumerate(UPGRADE_ORDER):
            col = i % cols
            row = i // cols
            bx = start_x + col * (box_w + gap)
            by = start_y + row * (box_h + gap)
            rect = pygame.Rect(bx, by, box_w, box_h)
            self.menu_rects.append((key, rect))

            level = self.levels[key]
            cost = upgrade_cost(key, level)
            affordable = self.score >= cost

            bg = (40, 70, 110) if affordable else (50, 50, 60)
            pygame.draw.rect(self.screen, bg, rect, border_radius=10)
            border = (120, 200, 255) if affordable else (100, 100, 100)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=10)

            name_txt = FONT_MED.render(UPGRADES[key]['name'],
                                       True, (255, 255, 255))
            self.screen.blit(name_txt, (bx + 15, by + 12))

            lvl_txt = FONT_SMALL.render(f"Poziom: {level}",
                                        True, (200, 220, 255))
            self.screen.blit(lvl_txt, (bx + 15, by + 48))

            desc_txt = FONT_SMALL.render(UPGRADES[key]['desc'],
                                         True, (220, 220, 220))
            self.screen.blit(desc_txt, (bx + 15, by + 72))

            cur_eff = upgrade_effect(key, level)
            nxt_eff = upgrade_effect(key, level + 1)
            if key in ('reel', 'bait', 'power'):
                eff_txt = f"Efekt: x{cur_eff:.2f} -> x{nxt_eff:.2f}"
            elif key == 'zone':
                eff_txt = f"Efekt: {cur_eff:.3f} -> {nxt_eff:.3f}"
            elif key == 'patience':
                eff_txt = f"Efekt: +{cur_eff:.1f}s -> +{nxt_eff:.1f}s"
            elif key == 'luck':
                eff_txt = (f"Efekt: +{cur_eff*100:.0f}% -> "
                           f"+{nxt_eff*100:.0f}%")
            else:
                eff_txt = ""

            e_txt = FONT_TINY.render(eff_txt, True, (180, 220, 180))
            self.screen.blit(e_txt, (bx + 15, by + 98))

            cost_color = (255, 220, 100) if affordable else (255, 100, 100)
            cost_txt = FONT_MED.render(f"Koszt: {cost}",
                                       True, cost_color)
            self.screen.blit(cost_txt,
                             (bx + box_w - cost_txt.get_width() - 15,
                              by + box_h - 40))

        hint = FONT_SMALL.render(
            "Kliknij kafelek by kupic | U = zamknij",
            True, (200, 200, 200))
        self.screen.blit(hint,
                         (WIDTH / 2 - hint.get_width() / 2, HEIGHT - 60))

        if self.hint_timer > 0 and self.hint_msg:
            alpha = int(255 * min(1.0, self.hint_timer))
            c = FONT_MED.render(self.hint_msg, True, (255, 255, 200))
            c.set_alpha(alpha)
            self.screen.blit(c, (WIDTH / 2 - c.get_width() / 2, HEIGHT - 100))

    def draw(self):
        self.screen.blit(self.bg, (0, 0))
        self.draw_water()

        for r in self.ripples:
            r.draw(self.screen)
        for f in self.fish_population:
            f.draw(self.screen)

        breath = math.sin(self.time * 2.0) * 3
        fox_x = 120
        fox_y = WATER_TOP - 40 - self.fox_img.get_height() + breath
        self.screen.blit(self.fox_img, (fox_x, fox_y))

        hand = (fox_x + 130, fox_y + 150)
        tip = (BANK_RIGHT - 20, WATER_TOP - 30)
        pygame.draw.line(self.screen, (100, 60, 30), hand, tip, 6)
        pygame.draw.circle(self.screen, (60, 40, 20), tip, 4)

        if self.state in (State.CASTING, State.BITE):
            self.draw_bobber()

        self.draw_depth_marker()

        if self.state == State.CASTING and self.cast_charging:
            bx, by, bw, bh = 60, 360, 240, 18
            pygame.draw.rect(self.screen, (30, 30, 30),
                             (bx, by, bw, bh), border_radius=8)
            fill_w = int(bw * self.cast_power)
            col = (int(255 * self.cast_power),
                   int(200 * (1 - self.cast_power)), 60)
            pygame.draw.rect(self.screen, col,
                             (bx, by, fill_w, bh), border_radius=8)
            pygame.draw.rect(self.screen, (220, 220, 220),
                             (bx, by, bw, bh), 2, border_radius=8)
            label = FONT_TINY.render("Moc rzutu", True, (240, 240, 240))
            self.screen.blit(label, (bx, by - 20))

        if self.state == State.BITE:
            bob_up = math.sin(self.bite_timer * 20) * 6
            s = FONT_BIG.render("!", True, (255, 80, 80))
            bx = self.bobber.x - s.get_width() / 2
            by = self.bobber.y - 70 + bob_up
            self.screen.blit(s, (bx, by))
            hint = FONT_MED.render("Kliknij szybko!", True, (255, 255, 255))
            self.screen.blit(hint,
                             (WIDTH / 2 - hint.get_width() / 2, 40))

        if self.state == State.MINIGAME:
            self.draw_minigame()

        for p in self.particles:
            p.draw(self.screen)
        for t in self.floating_texts:
            t.draw(self.screen)

        score_txt = FONT_MED.render(f"Punkty: {self.score}",
                                    True, (255, 255, 255))
        self.screen.blit(score_txt,
                         (WIDTH - score_txt.get_width() - 20, 20))

        if self.msg_timer > 0 and self.msg:
            shadow = FONT_BIG.render(self.msg, True, (0, 0, 0))
            text = FONT_BIG.render(self.msg, True, (255, 255, 255))
            cx = WIDTH / 2 - text.get_width() / 2
            cy = 100
            self.screen.blit(shadow, (cx + 3, cy + 3))
            self.screen.blit(text, (cx, cy))

        hint = FONT_SMALL.render(
            "LPM przytrzymaj i pusc = rzut | W/S lub strzalki = glebokosc | R = zwin | U = ulepszenia | ESC = wyjscie",
            True, (230, 230, 230))
        self.screen.blit(hint, (16, HEIGHT - 26))

        if self.menu_open:
            self.draw_menu()

        pygame.display.flip()


def main():
    game = Game()
    running = True
    while running:
        dt = game.clock.tick(FPS) / 1000.0
        mouse_down = pygame.mouse.get_pressed()[0]
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_u and game.state == State.CASTING:
                    game.menu_open = not game.menu_open
                    if game.menu_open:
                        game.cast_charging = False
                        game.cast_power = 0.0
                elif (event.key == pygame.K_r
                      and game.state == State.CASTING
                      and not game.menu_open):
                    game.retrieve_bobber()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game.menu_open:
                    for key, rect in game.menu_rects:
                        if rect.collidepoint(event.pos):
                            game.buy_upgrade(key)
                            break
                elif (game.state == State.CASTING
                      and not game.bobber.landed
                      and not game.bobber.flying):
                    mx, my = event.pos
                    if mx >= BANK_RIGHT:
                        game.cast_charging = True
                elif game.state == State.BITE:
                    game.start_minigame()
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if (not game.menu_open
                        and game.state == State.CASTING
                        and game.cast_charging):
                    game.cast_charging = False
                    power = game.cast_power
                    game.cast_power = 0.0
                    power_mult = upgrade_effect('power', game.levels['power'])
                    tx = (BANK_RIGHT + 100
                          + power * (WIDTH - BANK_RIGHT - 200) * power_mult)
                    tx = min(tx, WIDTH - 60)
                    game.bobber.cast_to(tx)
                    game.reset_fish_interest()

        if game.cast_charging and not game.menu_open:
            game.cast_power = min(1.0, game.cast_power + dt * 1.2)

        if not game.menu_open:
            game.update(dt, mouse_down, keys)

        game.draw()

    save_game(game.score, game.levels)
    pygame.quit()


if __name__ == "__main__":
    main()
