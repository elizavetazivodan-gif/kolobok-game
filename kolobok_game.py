import json
import math
import os
import random
import sys

try:
    import pygame
except ImportError:  
    pygame = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEVEL_DIR = os.path.join(BASE_DIR, "levels")
SAVE_FILE = os.path.join(BASE_DIR, "best_times.json")

WIDTH, HEIGHT = 1040, 640
FPS = 60

# кольори
BG_TOP = (12, 26, 20)
BG_BOTTOM = (24, 45, 35)
ROOT_COLOR = (75, 45, 25)
ROOT_DARK = (50, 30, 15)
MOSS_COLOR = (60, 155, 60)
MOSS_LIGHT = (100, 200, 80)
RUNE_COLOR = (0, 220, 180)
KOLOBOK_BASE = (245, 185, 80)
KOLOBOK_SHADOW = (210, 140, 40)
KOLOBOK_CHEEK = (240, 120, 120)
KOLOBOK_FLOUR = (255, 250, 235)
MUSHROOM_CAP = (0, 220, 210)
MUSHROOM_GLOW = (0, 255, 230)
FLOUR_BAG = (240, 235, 210)
SPIKE_COLOR = (190, 50, 50)
SPIKE_TIP = (240, 90, 90)
GOAL_GOLD = (255, 215, 0)
GOAL_GLOW = (255, 235, 120)

SMALL_MASS = 80
BIG_MASS = 120
MAX_MASS = 200

particles = []


def burst(x, y, color, n=10, speed=3.0, life=20, size=(3, 5)):
    for _ in range(n):
        particles.append({
            'x': x, 'y': y,
            'vx': random.uniform(-speed, speed),
            'vy': random.uniform(-speed, speed),
            'life': life, 'color': color, 'size': random.randint(size[0], size[1]),
        })


def circle_hits_rect(cx, cy, r, rx, ry, rw, rh):
    nx = max(rx, min(cx, rx + rw))
    ny = max(ry, min(cy, ry + rh))
    return (cx - nx) ** 2 + (cy - ny) ** 2 < r * r


def fmt_time(sec):
    sec = max(0.0, float(sec))
    m = int(sec // 60)
    return "%d:%05.2f" % (m, sec - m * 60)


def wrap_text(font, text, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if cur and font.size(trial)[0] > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


# об'єкти світу
class Platform:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = int(x), int(y), int(w), int(h)

    def draw(self, surface, ox):
        x = self.x - ox
        if x + self.w < 0 or x > WIDTH:
            return
        y, w, h = self.y, self.w, self.h
        pygame.draw.rect(surface, ROOT_COLOR, (x, y, w, h), border_radius=8)
        pygame.draw.rect(surface, ROOT_DARK, (x, y + 10, w, max(1, h - 10)), border_radius=8)
        pygame.draw.rect(surface, MOSS_COLOR, (x, y, w, 10),
                         border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.rect(surface, MOSS_LIGHT, (x, y, w, 3),
                         border_top_left_radius=8, border_top_right_radius=8)
        for tx in range(x + 8, x + w - 8, 16):
            pygame.draw.line(surface, MOSS_LIGHT, (tx, y), (tx - 2, y - 4), 2)
            pygame.draw.line(surface, MOSS_LIGHT, (tx + 4, y), (tx + 6, y - 5), 2)
        if w >= 100:
            pygame.draw.circle(surface, RUNE_COLOR, (x + 30, y + 22), 3)
            pygame.draw.circle(surface, RUNE_COLOR, (x + w - 30, y + 22), 3)


class Wall:
    """Дерев'яна стіна: маленького Колобка зупиняє, великий її пробиває"""

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = int(x), int(y), int(w), int(h)

    def draw(self, surface, ox, font):
        x = self.x - ox
        pygame.draw.rect(surface, (130, 80, 35), (x, self.y, self.w, self.h), border_radius=4)
        pygame.draw.rect(surface, (90, 50, 20), (x, self.y, self.w, self.h), 3, border_radius=4)
        for wy in range(self.y + 15, self.y + self.h, 25):
            pygame.draw.line(surface, (70, 40, 15), (x, wy), (x + self.w, wy), 2)
        txt = font.render("Дерев'яна стіна", True, (255, 220, 160))
        surface.blit(txt, (x + self.w // 2 - txt.get_width() // 2, self.y - 20))


class Enemy:
    """Лісовий «пеньок»: патрулює платформу між x_min та x_max"""
    W, H = 30, 26

    def __init__(self, x_min, x_max, bottom):
        self.x_min, self.x_max = int(x_min), int(x_max)
        if self.x_max - self.x_min < self.W:
            raise ValueError("зона патрулювання ворога занадто вузька")
        self.x = float(self.x_min)
        self.y = int(bottom) - self.H
        self.dir = 1
        self.speed = 1.3
        self.alive = True

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    def update(self):
        self.x += self.dir * self.speed
        if self.x < self.x_min:
            self.x, self.dir = self.x_min, 1
        elif self.x + self.W > self.x_max:
            self.x, self.dir = self.x_max - self.W, -1

    def draw(self, surface, ox, tick):
        x = int(self.x) - ox
        if x + self.W < 0 or x > WIDTH:
            return
        y = int(self.y)
        bob = int(math.sin(tick * 0.2 + self.x) * 2)
        pygame.draw.rect(surface, (95, 60, 35), (x, y + 4 + bob, self.W, self.H - 4), border_radius=8)
        pygame.draw.rect(surface, (140, 95, 55), (x, y + bob, self.W, 10), border_radius=6)
        pygame.draw.rect(surface, (50, 30, 15), (x, y + 4 + bob, self.W, self.H - 4), 2, border_radius=8)
        ex = x + (18 if self.dir > 0 else 6)
        pygame.draw.circle(surface, (255, 70, 70), (ex, y + 12 + bob), 3)
        pygame.draw.circle(surface, (255, 70, 70), (ex + 6, y + 12 + bob), 3)
        pygame.draw.line(surface, (30, 10, 10), (ex - 3, y + 7 + bob), (ex + 3, y + 9 + bob), 2)
        pygame.draw.line(surface, (30, 10, 10), (ex + 9, y + 7 + bob), (ex + 3, y + 9 + bob), 2)


# рівень
class Level:

    def __init__(self, data):
        self.name = str(data.get("name", "Рівень"))
        self.width = int(data.get("width", WIDTH))
        sx, sy = data["spawn"]
        self.spawn = (float(sx), float(sy))
        self.platforms = [Platform(*r) for r in data["platforms"]]
        if not self.platforms:
            raise ValueError("у рівні немає платформ")
        self.items = []
        for x, y in data.get("flour", []):
            self.items.append({'type': 'flour', 'x': int(x), 'y': int(y), 'collected': False})
        for x, y in data.get("mushrooms", []):
            self.items.append({'type': 'mushroom', 'x': int(x), 'y': int(y), 'collected': False})
        self.spikes = [pygame.Rect(*[int(v) for v in r]) for r in data.get("spikes", [])]
        self.walls = [Wall(*r) for r in data.get("walls", [])]
        self.enemies = [Enemy(*e) for e in data.get("enemies", [])]
        self.goal = pygame.Rect(*[int(v) for v in data["goal"]])
        self.hints = list(data.get("hints", []))
        for h in self.hints:
            h["x"], h["w"], h["text"]  # перевірка обов'язкових полів
        oven = data.get("oven")
        self.oven = (int(oven[0]), int(oven[1])) if oven else None


def load_level_file(filename):
    """Повертає (дані, None) або (None, текст_помилки)."""
    path = os.path.join(LEVEL_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        Level(data)  # перевірка структури
        return data, None
    except FileNotFoundError:
        return None, "файл %s не знайдено" % filename
    except (OSError, ValueError, KeyError, TypeError, IndexError) as e:
        return None, "%s: %s" % (filename, e)


def generate_random_level(seed, segments=22):
    rng = random.Random(seed)
    platforms = [[0, 540, 340, 100]]
    flour, mushrooms, spikes, walls, enemies = [], [], [], [], []
    x_right, y = 340, 540
    flour_total = 0
    for i in range(segments):
        gap = rng.randint(45, 105)
        ny = max(220, min(540, y + rng.randint(-80, 60)))
        w = rng.randint(130, 260)
        nx = x_right + gap
        platforms.append([nx, ny, w, 30])

        # борошно: на перших платформах гарантовано 2 мішечки, щоб можна було стати великим
        n_flour = 2 if i < 2 else rng.choice([0, 1, 1, 2, 3])
        for k in range(n_flour):
            flour.append([nx + (k + 1) * w // (n_flour + 1), ny - 30])
        flour_total += n_flour
        if rng.random() < 0.25:
            mushrooms.append([nx + w // 2, ny - 75])

        # перешкоди (взаємовиключні на одній платформі)
        r = rng.random()
        if i >= 2 and w >= 170 and r < 0.28 and flour_total >= 2:
            spikes.append([nx + rng.randint(50, w - 110), ny - 15, 45, 15])
        elif i >= 3 and w >= 190 and r < 0.38 and flour_total >= 3:
            walls.append([nx + w // 2, ny - 90, 30, 90])
        elif i >= 1 and w >= 170 and r < 0.60:
            enemies.append([nx + 8, nx + w - 8, ny])
        x_right, y = nx + w, ny

    fx = x_right + 80
    fy = max(260, y - 60)
    platforms.append([fx, fy, 300, 640 - fy])
    return {
        "name": "Випадковий ліс (seed %s)" % seed,
        "width": fx + 360,
        "spawn": [90, 490],
        "oven": [0, 540],
        "goal": [fx + 190, fy - 75, 70, 75],
        "platforms": platforms,
        "flour": flour, "mushrooms": mushrooms,
        "spikes": spikes, "walls": walls, "enemies": enemies,
        "hints": [],
    }


def load_best():
    try:
        with open(SAVE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_best(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass  # рекорд просто не збережеться


# Колобок
class Kolobok:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.mass = SMALL_MASS
        self.radius = 20
        self.is_grounded = False
        self.jumps_left = 2
        self.dash_cooldown = 0
        self.dash_time = 0
        self.dash_dir = 1
        self.invuln_timer = 0
        self.facing_right = True

    @property
    def is_big(self):
        return self.mass >= BIG_MASS

    @property
    def hp(self):
        return 2 if self.is_big else 1

    @property
    def state_name(self):
        return "великий Колобок (пробиває стіни)" if self.is_big else "маленький Колобок (швидкий, 1 HP)"

    def rect(self):
        r = int(self.radius)
        return pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)

    def add_mass(self, amount):
        self.mass = min(MAX_MASS, self.mass + amount)

    def hurt(self):
        """True, якщо Колобок загинув"""
        if self.invuln_timer > 0:
            return False
        if self.is_big:
            self.mass = SMALL_MASS
            self.vy = -7.5
            self.invuln_timer = 60
            burst(self.x, self.y, KOLOBOK_FLOUR, 16, 4, 25, (3, 6))
            return False
        return True

    def jump(self):
        if self.is_grounded or self.jumps_left > 0:
            power = -9.8 if self.is_big else -11.0
            if not self.is_grounded and self.jumps_left == 1:
                power *= 0.9
            for _ in range(6):
                particles.append({
                    'x': self.x, 'y': self.y + self.radius,
                    'vx': random.uniform(-2, 2), 'vy': random.uniform(0.5, 2.5),
                    'life': 15, 'color': (220, 220, 200), 'size': 4})
            self.vy = power
            self.is_grounded = False
            self.jumps_left -= 1

    def dash(self):
        if self.dash_cooldown > 0:
            return
        self.dash_dir = 1 if self.facing_right else -1
        self.dash_time = 9
        self.dash_cooldown = 25
        for _ in range(8):
            particles.append({
                'x': self.x, 'y': self.y,
                'vx': random.uniform(-2, 2) - self.dash_dir * 3, 'vy': random.uniform(-2, 2),
                'life': 20, 'color': (255, 235, 180), 'size': random.randint(3, 6)})

    def _collide(self, rx, ry, rw, rh):
        cx = max(rx, min(self.x, rx + rw))
        cy = max(ry, min(self.y, ry + rh))
        dx, dy = self.x - cx, self.y - cy
        d2 = dx * dx + dy * dy
        if d2 >= self.radius * self.radius:
            return
        if d2 == 0:
            self.y = ry - self.radius
            self.vy = 0
            self.is_grounded = True
            self.jumps_left = 2
            return
        dist = math.sqrt(d2)
        nx, ny = dx / dist, dy / dist
        if ny < -0.5 and self.vy >= 0:
            self.y = ry - self.radius
            self.vy = 0
            self.is_grounded = True
            self.jumps_left = 2
        elif ny > 0.5 and self.vy < 0:
            self.y = ry + rh + self.radius
            self.vy = 0
        elif nx < 0:
            self.x = rx - self.radius
            self.vx = 0
        elif nx > 0:
            self.x = rx + rw + self.radius
            self.vx = 0

    def update(self, keys, platforms, walls, world_w):
        events = []
        # маленький Колобок легший і прудкіший, великий - повільніший і важчий
        self.radius = int(18 + (min(self.mass, MAX_MASS) / 100) * 8)
        speed_mult = 0.9 if self.is_big else 1.25
        accel = 0.7 * speed_mult
        max_vx = 7.5 * speed_mult
        friction = 0.91

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx -= accel
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx += accel
            self.facing_right = True

        if self.dash_time > 0:  # ривок: фіксована швидкість, без гравітації
            self.dash_time -= 1
            self.vx = self.dash_dir * 14.0
            self.vy = 0.0
        else:
            self.vx = max(-max_vx, min(max_vx, self.vx)) * friction
            self.vy += 0.5 if self.is_big else 0.42

        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        if self.invuln_timer > 0:
            self.invuln_timer -= 1

        self.x += self.vx
        self.y += self.vy
        if self.x < self.radius:
            self.x, self.vx = self.radius, 0
        elif self.x > world_w - self.radius:
            self.x, self.vx = world_w - self.radius, 0

        # борошняний пил під час руху по землі
        if self.is_grounded and abs(self.vx) > 0.8 and random.random() < 0.4:
            particles.append({
                'x': self.x - self.vx * 2, 'y': self.y + self.radius - 2,
                'vx': random.uniform(-0.5, 0.5), 'vy': random.uniform(-1, -0.2),
                'life': 15, 'color': KOLOBOK_FLOUR, 'size': random.randint(2, 4)})

        # великий Колобок пробиває стіни
        if self.is_big:
            for w in walls[:]:
                if circle_hits_rect(self.x, self.y, self.radius, w.x, w.y, w.w, w.h):
                    walls.remove(w)
                    events.append("wall")
                    for _ in range(25):
                        particles.append({
                            'x': w.x + w.w // 2, 'y': w.y + w.h // 2,
                            'vx': random.uniform(-5, 5), 'vy': random.uniform(-6, 2),
                            'life': 30, 'color': (140, 90, 40), 'size': random.randint(4, 8)})

        # зіткнення: платформи та уцілілі стіни (суцільні для маленького Колобка)
        self.is_grounded = False
        for p in platforms:
            self._collide(p.x, p.y, p.w, p.h)
        for w in walls:
            self._collide(w.x, w.y, w.w, w.h)
        return events

    def draw(self, surface, ox):
        cxp = int(self.x) - ox
        glow_r = self.radius + (6 if self.is_big else 3)
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        glow_color = (255, 200, 50, 60) if self.is_big else (255, 230, 150, 35)
        pygame.draw.circle(glow, glow_color, (glow_r, glow_r), glow_r)
        surface.blit(glow, (cxp - glow_r, int(self.y) - glow_r))
        if self.invuln_timer % 4 in (1, 2):
            return  # блимання після удару
        center = (cxp, int(self.y))
        pygame.draw.circle(surface, KOLOBOK_BASE, center, self.radius)
        pygame.draw.circle(surface, KOLOBOK_SHADOW, center, self.radius, 3)
        d = 1 if self.facing_right else -1
        ex1, ex2, ey = cxp + d * 4 - 3, cxp + d * 4 + 5, int(self.y) - 4
        for ex in (ex1, ex2):
            pygame.draw.circle(surface, (30, 15, 5), (ex, ey), 3)
            pygame.draw.circle(surface, (255, 255, 255), (ex - 1, ey - 1), 1)
        pygame.draw.circle(surface, KOLOBOK_CHEEK, (cxp + d * 4 - 6, int(self.y) + 3), 3)
        pygame.draw.circle(surface, KOLOBOK_CHEEK, (cxp + d * 4 + 7, int(self.y) + 3), 3)
        smile = pygame.Rect(cxp + d * 4 - 3, int(self.y) + 2, 8, 6)
        pygame.draw.arc(surface, (60, 30, 10), smile, math.pi, math.pi * 2, 2)


#  допоміжне малювання 
def draw_spikes(surface, rect, ox):
    x0 = rect.x - ox
    for i in range(max(1, rect.w // 15)):
        sx = x0 + i * 15
        pts = [(sx, rect.y + rect.h), (sx + 7.5, rect.y), (sx + 15, rect.y + rect.h)]
        pygame.draw.polygon(surface, SPIKE_COLOR, pts)
        pygame.draw.polygon(surface, SPIKE_TIP, [(sx + 5, rect.y + 6), (sx + 7.5, rect.y), (sx + 10, rect.y + 6)])


def draw_item(surface, item, ox):
    ix, iy = item['x'] - ox, item['y']
    if item['type'] == 'flour':
        pygame.draw.circle(surface, FLOUR_BAG, (ix, iy + 2), 9)
        pygame.draw.polygon(surface, (220, 200, 160), [(ix - 5, iy - 6), (ix, iy - 10), (ix + 5, iy - 6)])
    else:
        pygame.draw.circle(surface, (0, 120, 110), (ix, iy - 2), 14, 2)
        pygame.draw.rect(surface, (230, 230, 220), (ix - 3, iy, 6, 8), border_radius=2)
        pygame.draw.ellipse(surface, MUSHROOM_CAP, (ix - 10, iy - 12, 20, 12))
        pygame.draw.circle(surface, (255, 255, 255), (ix - 4, iy - 6), 2)
        pygame.draw.circle(surface, (255, 255, 255), (ix + 3, iy - 7), 2)


def draw_oven(surface, ox, x, y_bottom, font):
    px, w, h = x - ox, 80, 70
    pygame.draw.rect(surface, (110, 80, 65), (px, y_bottom - h, w, h), border_radius=14)
    pygame.draw.rect(surface, (70, 50, 40), (px, y_bottom - h, w, h), 3, border_radius=14)
    pygame.draw.rect(surface, (25, 12, 8), (px + 20, y_bottom - 46, 40, 46),
                     border_top_left_radius=20, border_top_right_radius=20)
    pygame.draw.circle(surface, (255, 140, 40), (px + 40, y_bottom - 14), 9)
    pygame.draw.circle(surface, (255, 210, 90), (px + 40, y_bottom - 12), 5)
    txt = font.render("Піч", True, (255, 220, 170))
    surface.blit(txt, (px + w // 2 - txt.get_width() // 2, y_bottom - h - 18))


def draw_heart(surface, x, y, color):
    pygame.draw.circle(surface, color, (x - 4, y), 5)
    pygame.draw.circle(surface, color, (x + 4, y), 5)
    pygame.draw.polygon(surface, color, [(x - 8, y + 2), (x + 8, y + 2), (x, y + 11)])


# гра
class Game:
    MODE_TITLES = {
        "story": "Історія", "speedrun": "Забіг на час",
        "random": "Випадковий ліс", "tutorial": "Навчання",
    }

    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Колобок: втеча з печі!")
        self.clock = pygame.time.Clock()
        try:
            self.font_hud = pygame.font.SysFont('Arial', 18, bold=True)
            self.font_small = pygame.font.SysFont('Arial', 15)
            self.font_large = pygame.font.SysFont('Arial', 32, bold=True)
            self.font_huge = pygame.font.SysFont('Arial', 44, bold=True)
        except Exception:
            self.font_hud = pygame.font.Font(None, 22)
            self.font_small = pygame.font.Font(None, 18)
            self.font_large = pygame.font.Font(None, 36)
            self.font_huge = pygame.font.Font(None, 50)

        self.fireflies = [{
            'x': random.randint(0, WIDTH), 'y': random.randint(0, HEIGHT),
            'radius': random.uniform(1.5, 3.5),
            'speed_y': random.uniform(-0.4, -0.1), 'speed_x': random.uniform(-0.2, 0.2),
            'phase': random.uniform(0, math.pi * 2)} for _ in range(25)]
        self.bg = self.make_background()

        self.best = load_best()
        self.state = "MENU"
        self.mode = None
        self.level_data = None
        self.level = None
        self.player = None
        self.msg = ""
        self.paused = False
        self.running = True
        self.tick = 0
        self.seed = None
        self.timer = 0.0
        self.score = 0
        self.final_time = 0.0
        self.new_record = False
        self.checkpoint = None
        self.deaths = 0
        self.hint = None
        self.cam_x = 0.0

    def make_background(self):
        surf = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / HEIGHT
            color = tuple(int(BG_TOP[i] * (1 - t) + BG_BOTTOM[i] * t) for i in range(3))
            pygame.draw.line(surf, color, (0, y), (WIDTH, y))
        return surf

    # керування станами
    def start(self, mode, seed=None):
        self.msg = ""
        if mode == "random":
            self.seed = seed if seed is not None else random.randint(1, 999999)
            data = generate_random_level(self.seed)
        else:
            filename = "tutorial.json" if mode == "tutorial" else "level1.json"
            data, err = load_level_file(filename)
            if err:
                self.msg = "Не вдалося завантажити рівень: " + err
                self.state = "MENU"
                return
        self.mode = mode
        self.level_data = data
        self.reset()

    def reset(self):
        self.level = Level(self.level_data)  # свіжі об'єкти: стіни, борошно, вороги
        sx, sy = self.level.spawn
        self.player = Kolobok(sx, sy)
        particles.clear()
        self.score = 0
        self.timer = 0.0
        self.final_time = 0.0
        self.new_record = False
        self.checkpoint = None
        self.deaths = 0
        self.hint = None
        self.cam_x = 0.0
        self.paused = False
        self.state = "PLAYING"

    def die(self):
        self.deaths += 1
        if self.mode == "tutorial":  # у навчанні Колобок відроджується на контрольній точці
            if self.checkpoint:
                (x, y), mass = self.checkpoint
            else:
                (x, y), mass = self.level.spawn, SMALL_MASS
            self.player = Kolobok(x, y)
            self.player.mass = mass
            self.player.invuln_timer = 60
            return
        self.final_time = self.timer
        self.state = "GAME_OVER"

    def win(self):
        self.final_time = self.timer
        self.state = "WIN"
        if self.mode == "speedrun":
            best = self.best.get("speedrun")
            if best is None or self.final_time < best:
                self.best["speedrun"] = round(self.final_time, 2)
                self.new_record = True
                save_best(self.best)

    # події
    def on_key(self, key):
        if self.state == "MENU":
            if key == pygame.K_1:
                self.start("story")
            elif key == pygame.K_2:
                self.start("speedrun")
            elif key == pygame.K_3:
                self.start("random")
            elif key == pygame.K_t:
                self.start("tutorial")
            elif key == pygame.K_ESCAPE:
                self.running = False
            return
        if key == pygame.K_ESCAPE:
            self.state = "MENU"
            self.paused = False
        elif key == pygame.K_p and self.state == "PLAYING":
            self.paused = not self.paused
        elif key == pygame.K_r:
            self.reset()
        elif key == pygame.K_n and self.mode == "random":
            self.start("random")
        elif key == pygame.K_RETURN and self.state == "WIN" and self.mode == "tutorial":
            self.start("story")
        elif self.state == "PLAYING" and not self.paused:
            if key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                self.player.jump()
            elif key in (pygame.K_LSHIFT, pygame.K_x):
                self.player.dash()

    # логіка кадру
    def update(self, dt):
        lvl, p = self.level, self.player
        self.timer += dt
        keys = pygame.key.get_pressed()
        for ev in p.update(keys, lvl.platforms, lvl.walls, lvl.width):
            if ev == "wall":
                self.score += 100
        if p.y > HEIGHT + 80:
            self.die()
            return
        kol = p.rect()

        for item in lvl.items:
            if item['collected']:
                continue
            if kol.colliderect(pygame.Rect(item['x'] - 12, item['y'] - 12, 24, 24)):
                item['collected'] = True
                if item['type'] == 'flour':
                    p.add_mass(20)
                    self.score += 150
                    burst(item['x'], item['y'], (255, 245, 200), 10, 3, 20, (3, 5))
                else:
                    self.score += 300
                    burst(item['x'], item['y'], MUSHROOM_GLOW, 12, 3, 22, (3, 6))

        for s in lvl.spikes:
            if kol.colliderect(s) and p.hurt():
                self.die()
                return

        for e in lvl.enemies:
            if not e.alive:
                continue
            e.update()
            er = e.rect()
            if kol.colliderect(er):
                if p.vy > 1 and p.y < e.y:  
                    e.alive = False
                    p.vy = -8.0
                    p.jumps_left = max(p.jumps_left, 1)
                    self.score += 200
                    burst(er.centerx, er.centery, (180, 120, 60), 14, 4, 25, (3, 6))
                elif p.hurt():
                    self.die()
                    return
        lvl.enemies = [e for e in lvl.enemies if e.alive]

        self.update_hint()

        if kol.colliderect(lvl.goal):
            self.win()
            return

        max_cam = max(0, lvl.width - WIDTH)
        target = max(0, min(max_cam, p.x - WIDTH / 2))
        self.cam_x += (target - self.cam_x) * 0.12

    def update_hint(self):
        px = self.player.x
        self.hint = None
        for h in self.level.hints:
            if h["x"] <= px < h["x"] + h["w"]:
                self.hint = h
                rp = h.get("respawn")
                if rp and (self.checkpoint is None or rp[0] > self.checkpoint[0][0]):
                    self.checkpoint = ((rp[0], rp[1]), self.player.mass)
                break

    # малювання
    def text(self, font, s, color, pos, center=False):
        surf = font.render(s, True, color)
        x, y = pos
        if center:
            x -= surf.get_width() // 2
        self.screen.blit(surf, (x, y))

    def draw_background(self):
        self.screen.blit(self.bg, (0, 0))
        for ff in self.fireflies:
            ff['y'] += ff['speed_y']
            ff['x'] += ff['speed_x']
            ff['phase'] += 0.05
            if ff['y'] < -10:
                ff['y'] = HEIGHT + 10
                ff['x'] = random.randint(0, WIDTH)
            alpha = int(120 + 80 * math.sin(ff['phase']))
            size = int(ff['radius'] * 4)
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(surf, (140, 255, 200, alpha), (size // 2, size // 2), int(ff['radius']))
            self.screen.blit(surf, (int(ff['x']), int(ff['y'])))

    def draw_world(self):
        lvl, ox = self.level, int(self.cam_x)
        if lvl.oven:
            draw_oven(self.screen, ox, lvl.oven[0], lvl.oven[1], self.font_small)
        for p in lvl.platforms:
            p.draw(self.screen, ox)
        for w in lvl.walls:
            w.draw(self.screen, ox, self.font_small)
        for s in lvl.spikes:
            draw_spikes(self.screen, s, ox)
        for item in lvl.items:
            if not item['collected']:
                draw_item(self.screen, item, ox)
        for e in lvl.enemies:
            e.draw(self.screen, ox, self.tick)
        g = lvl.goal.move(-ox, 0)
        pygame.draw.rect(self.screen, GOAL_GOLD, g, border_radius=12)
        pygame.draw.rect(self.screen, GOAL_GLOW, g, 4, border_radius=12)
        self.text(self.font_hud, "Долина", (40, 20, 0), (g.x + 5, g.y + 18))
        self.text(self.font_small, "випічки", (60, 30, 0), (g.x + 8, g.y + 42))

        for p in particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] <= 0:
                particles.remove(p)
            else:
                pygame.draw.circle(self.screen, p['color'], (int(p['x']) - ox, int(p['y'])), p['size'])
        if self.state != "GAME_OVER":
            self.player.draw(self.screen, ox)

    def draw_hud(self):
        p = self.player
        panel = pygame.Surface((440, 92), pygame.SRCALPHA)
        pygame.draw.rect(panel, (15, 25, 20, 210), (0, 0, 440, 92), border_radius=10)
        pygame.draw.rect(panel, (60, 120, 90, 180), (0, 0, 440, 92), 2, border_radius=10)
        self.screen.blit(panel, (15, 15))
        color = (255, 215, 0) if p.is_big else (120, 220, 255)
        self.text(self.font_hud, "Статус: " + p.state_name, color, (28, 22))
        pygame.draw.rect(self.screen, (40, 50, 45), (28, 48, 200, 14), border_radius=7)
        fill = int(max(0.0, min(1.0, p.mass / MAX_MASS)) * 200)
        pygame.draw.rect(self.screen, (100, 230, 100) if p.is_big else (240, 180, 60),
                         (28, 48, fill, 14), border_radius=7)
        # позначка порогу «великий Колобок»
        thr = 28 + int(BIG_MASS / MAX_MASS * 200)
        pygame.draw.line(self.screen, (255, 255, 255), (thr, 46), (thr, 64), 2)
        self.text(self.font_small, "Маса: %d кг" % p.mass, (255, 255, 255), (238, 47))
        for i in range(2):
            col = (230, 60, 80) if i < p.hp else (70, 50, 55)
            draw_heart(self.screen, 360 + i * 26, 52, col)
        self.text(self.font_small,
                  "Бал: %d | Час: %s | Режим: %s" % (self.score, fmt_time(self.timer),
                                                      self.MODE_TITLES.get(self.mode, "")),
                  (180, 220, 200), (28, 70))
        if self.mode == "speedrun":
            t = fmt_time(self.final_time if self.state != "PLAYING" else self.timer)
            surf = self.font_huge.render(t, True, (255, 235, 170))
            self.screen.blit(surf, (WIDTH - surf.get_width() - 24, 16))
            best = self.best.get("speedrun")
            b = "Рекорд: " + (fmt_time(best) if best is not None else "—")
            surf = self.font_small.render(b, True, (200, 230, 210))
            self.screen.blit(surf, (WIDTH - surf.get_width() - 24, 66))

        bar = pygame.Surface((680, 30), pygame.SRCALPHA)
        pygame.draw.rect(bar, (10, 20, 15, 180), (0, 0, 680, 30), border_radius=6)
        self.screen.blit(bar, (WIDTH // 2 - 340, HEIGHT - 40))
        self.text(self.font_small,
                  "A/D - рух   Space/W - стрибок (x2)   LShift/X - ривок   R - рестарт   P - пауза   Esc - меню",
                  (200, 230, 210), (WIDTH // 2, HEIGHT - 34), center=True)

    def draw_hint(self):
        if not self.hint:
            return
        lines = wrap_text(self.font_hud, self.hint["text"], 700)
        h = 18 + 24 * len(lines)
        panel = pygame.Surface((740, h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 40, 60, 225), (0, 0, 740, h), border_radius=12)
        pygame.draw.rect(panel, (110, 190, 255), (0, 0, 740, h), 2, border_radius=12)
        self.screen.blit(panel, (WIDTH // 2 - 370, 120))
        for i, line in enumerate(lines):
            self.text(self.font_hud, line, (235, 245, 255), (WIDTH // 2, 129 + i * 24), center=True)

    def draw_card(self, w, h, fill, border):
        card = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(card, fill, (0, 0, w, h), border_radius=14)
        pygame.draw.rect(card, border, (0, 0, w, h), 3, border_radius=14)
        self.screen.blit(card, (WIDTH // 2 - w // 2, HEIGHT // 2 - h // 2))

    def draw_overlay(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        if self.paused:
            self.draw_card(360, 110, (15, 25, 35, 235), (120, 180, 230))
            self.text(self.font_large, "ПАУЗА", (230, 240, 255), (cx, cy - 36), center=True)
            self.text(self.font_small, "P - продовжити, Esc - меню", (200, 220, 240), (cx, cy + 14), center=True)
        elif self.state == "GAME_OVER":
            self.draw_card(560, 170, (40, 15, 15, 230), (220, 60, 60))
            self.text(self.font_large, "КОЛОБОК ПОМЕР В ЛІСІ!", (255, 90, 90), (cx, cy - 55), center=True)
            self.text(self.font_hud, "Час: %s | Бал: %d" % (fmt_time(self.final_time), self.score),
                      (240, 240, 240), (cx, cy - 5), center=True)
            self.text(self.font_small, "R - спробувати ще раз   Esc - меню", (220, 200, 200), (cx, cy + 35), center=True)
        elif self.state == "WIN":
            self.draw_card(620, 200, (15, 45, 25, 235), (80, 240, 140))
            title = "НАВЧАННЯ ПРОЙДЕНО!" if self.mode == "tutorial" else "ПЕРЕМОГА! ВИ У ДОЛИНІ ВИПІЧКИ!"
            self.text(self.font_large, title, (100, 255, 150), (cx, cy - 70), center=True)
            self.text(self.font_hud, "Бал: %d | Час: %s" % (self.score, fmt_time(self.final_time)),
                      (255, 235, 170), (cx, cy - 20), center=True)
            if self.new_record:
                self.text(self.font_hud, "Новий рекорд!", (255, 215, 0), (cx, cy + 8), center=True)
            hint = "Enter - до гри   R - ще раз   Esc - меню" if self.mode == "tutorial" \
                else "R - зіграти знову   Esc - меню"
            self.text(self.font_small, hint, (200, 240, 210), (cx, cy + 50), center=True)

    def draw_menu(self):
        self.draw_background()
        cx = WIDTH // 2
        self.text(self.font_huge, "Колобок: втеча з печі!", (255, 210, 110), (cx, 90), center=True)
        self.text(self.font_small, "Ітерація 2 - платформер у містичному лісі", (180, 220, 200), (cx, 150), center=True)
        items = [
            ("T", "Навчання (рекомендуємо для першого запуску)"),
            ("1", "Історія - рівень «Містичний ліс»"),
            ("2", "Забіг на час - пройти рівень якнайшвидше"),
            ("3", "Випадковий ліс - згенерований рівень"),
            ("Esc", "Вихід"),
        ]
        for i, (k, label) in enumerate(items):
            y = 220 + i * 56
            pygame.draw.rect(self.screen, (20, 40, 32), (cx - 330, y, 660, 44), border_radius=10)
            pygame.draw.rect(self.screen, (60, 120, 90), (cx - 330, y, 660, 44), 2, border_radius=10)
            self.text(self.font_large, k, (255, 215, 0), (cx - 310, y + 4))
            self.text(self.font_hud, label, (235, 245, 235), (cx - 210, y + 12))
        best = self.best.get("speedrun")
        self.text(self.font_small, "Рекорд забігу: " + (fmt_time(best) if best is not None else "—"),
                  (200, 230, 210), (cx, 520), center=True)
        if self.msg:
            self.text(self.font_hud, self.msg, (255, 110, 110), (cx, 560), center=True)

    def draw(self):
        if self.state == "MENU":
            self.draw_menu()
            return
        self.draw_background()
        self.draw_world()
        self.draw_hud()
        self.draw_hint()
        self.draw_overlay()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.tick += 1
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.on_key(event.key)
            if self.state == "PLAYING" and not self.paused:
                self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()


def main():
    print("Колобок: втеча з печі!")
    if pygame is None:
        print("[!] Pygame не встановлено")
        print("Встановлення: pip install pygame-ce (або pip install pygame)")
        print("Запуск: python kolobok_game.py")
        return
    print("[+] Запуск графічного прототипу (ітерація 2)...")
    Game().run()


if __name__ == "__main__":
    main()
