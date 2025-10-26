#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ruleta de Halloween con fondo por imagen (fallback procedimental)
- Pygame + gfxdraw, supersampling opcional para nitidez
- Carga una imagen de fondo (naranja con telarañas, etc.) y dibuja la ruleta encima
- Íconos dibujados por código (no requiere PNGs de segmentos)
- PC: barra ESPACIO para girar. RPi: botón en GPIO 17 (pull-up)
"""

import math, random, time
import pygame
import pygame.gfxdraw as gfx

# ===== Config global =====
FULLSCREEN = False                 # True para fullscreen (ideal en RPi)
WINDOW_SIZE = (1280, 720)
FPS = 60
TITLE = "Ruleta Halloween – Fondo por imagen"

# Supersampling (renderiza grande y luego baja con smoothscale)
SS = 2                             # 2 = buena calidad; usar 1 en RPi 2 si va justo

# Fondo (si falla la imagen, usa estos colores)
ORANGE1 = (255, 163, 26)
ORANGE2 = (248, 122, 13)
DOT = (245, 185, 90)

# Imagen de fondo
USE_BG_IMAGE = True
BACKGROUND_PATH = "fondo_halloween.png"   # <<— poné acá tu archivo

# Entrada GPIO (se desactiva sola en PC)
BUTTON_GPIO = 17
DEBOUNCE_MS = 200
USE_GPIO = True
try:
    import RPi.GPIO as GPIO
except Exception:
    USE_GPIO = False

# Segmentos
SEGMENTS = [
    {"label": "Poción",      "color": (255, 78, 36),  "win": True,  "icon": "potion"},
    {"label": "Murciélagos", "color": (69, 52, 97),   "win": True,  "icon": "bats"},
    {"label": "Calabaza",    "color": (255, 196, 22), "win": True,  "icon": "pumpkin"},
    {"label": "Fantasma",    "color": (129, 78, 182), "win": True,  "icon": "ghost"},
    {"label": "Caramelos",   "color": (255, 196, 22), "win": True,  "icon": "candies"},
    {"label": "Momia",       "color": (69, 52, 97),   "win": True,  "icon": "mummy"},
    {"label": "Gelatina",    "color": (255, 78, 36),  "win": True,  "icon": "jelly"},
    {"label": "Telaraña",    "color": (129, 78, 182), "win": True,  "icon": "web"},
]
WEIGHTS = [1]*len(SEGMENTS)

SPIN_MIN_TURNS = 3.5
SPIN_MAX_TURNS = 6.0
SPIN_DURATION  = 3.8

CONFETTI_PARTICLES = 140
CONFETTI_TIME = 1.4

TEXT = (250, 250, 250)

# ===== Utilidades =====
def ease_out_cubic(t):
    t -= 1.0
    return t*t*t + 1.0

def lerp(a,b,t): return a + (b-a)*t

def draw_vertical_gradient(surf, top, bottom):
    w,h = surf.get_size()
    for y in range(h):
        t = y/max(1,h-1)
        col = (int(lerp(top[0],bottom[0],t)),
               int(lerp(top[1],bottom[1],t)),
               int(lerp(top[2],bottom[2],t)))
        pygame.draw.line(surf, col, (0,y), (w,y))

def arc_points(cx, cy, r, a0, a1, steps=48):
    pts=[]
    for i in range(steps+1):
        t=i/steps
        a=a0+(a1-a0)*t
        pts.append((cx+r*math.cos(a), cy+r*math.sin(a)))
    return pts

def wedge_polygon(cx,cy,r0,r1,a0,a1,steps=48):
    outer = arc_points(cx,cy,r1,a0,a1,steps)
    inner = arc_points(cx,cy,r0,a1,a0,steps)
    return outer+inner

def draw_dots(surf, spacing, radius, color):
    w,h = surf.get_size()
    for y in range(spacing//2, h, spacing):
        offset = 0 if (y//spacing)%2==0 else spacing//2
        for x in range(offset+spacing//2, w, spacing):
            gfx.filled_circle(surf, x, y, radius, color)

def draw_spiderweb(surf, cx, cy, r, turns=6, rings=6, color=(250,230,200), alpha=160):
    col = (*color, alpha)
    for i in range(1, rings+1):
        rr = int(r*i/rings)
        gfx.aacircle(surf, cx, cy, rr, col)
    for i in range(turns):
        a = 2*math.pi*i/turns
        x = cx + r*math.cos(a); y = cy + r*math.sin(a)
        pygame.draw.aaline(surf, color, (cx,cy), (x,y))

def draw_spider(surf, x, y, size=16, color=(20,20,20)):
    gfx.filled_circle(surf, x, y, size//3, color)
    gfx.filled_circle(surf, x, y+size//3, size//2, color)
    for i in range(4):
        dx = (i+1)*2
        pygame.draw.aaline(surf, color, (x-dx, y+2), (x-dx-7, y-8))
        pygame.draw.aaline(surf, color, (x-dx-7, y-8), (x-dx-12, y-14))
        pygame.draw.aaline(surf, color, (x+dx, y+2), (x+dx+7, y-8))
        pygame.draw.aaline(surf, color, (x+dx+7, y-8), (x+dx+12, y-14))
    pygame.draw.aaline(surf, color, (x, y-40), (x, y-4))

def draw_skeleton_hand(surf, x, y, scale=1.0, flip=False):
    col=(245,245,245)
    def bone(ax,ay,bx,by,w=6):
        pygame.draw.line(surf,col,(ax,ay),(bx,by),max(1,int(w*scale)))
        gfx.filled_circle(surf,int(ax),int(ay),int(w*0.6*scale),col)
        gfx.filled_circle(surf,int(bx),int(by),int(w*0.6*scale),col)
    gfx.filled_circle(surf, int(x), int(y), int(18*scale), col)
    s = -1 if flip else 1
    bone(x, y-10*scale, x+35*s*scale, y-35*scale, 6)
    bone(x, y-2*scale,  x+38*s*scale, y-20*scale, 6)
    bone(x-2*s*scale, y+6*scale, x+36*s*scale, y-5*scale, 6)
    bone(x-4*s*scale, y+14*scale, x+30*s*scale, y+10*scale, 6)
    bone(x-5*s*scale, y+20*scale, x+24*s*scale, 6)

# ===== Íconos de segmentos (procedurales) =====
def icon_ghost(surf, cx, cy, r):
    white=(245,245,255); eye=(30,30,40); boo=(255,230,120)
    rect=pygame.Rect(0,0,int(r*1.1),int(r*1.2)); rect.center=(cx,cy)
    pygame.draw.ellipse(surf, white, rect)
    for i in range(-2,3):
        gfx.filled_circle(surf, int(cx+i*r*0.22), int(cy+r*0.55), int(r*0.22), white)
    gfx.filled_circle(surf, int(cx-r*0.18), int(cy-r*0.1), int(r*0.09), eye)
    gfx.filled_circle(surf, int(cx+r*0.18), int(cy-r*0.1), int(r*0.09), eye)
    gfx.filled_circle(surf, int(cx), int(cy+r*0.05), int(r*0.08), eye)
    font = pygame.font.SysFont("Arial", max(12,int(r*0.35)), bold=True)
    txt = font.render("BOOO", True, boo)
    surf.blit(txt, txt.get_rect(midleft=(cx+r*0.7, cy)))

def icon_pumpkin(surf, cx, cy, r):
    orange=(255,140,0); dark=(60,25,0); face=(25,10,0); green=(40,140,40)
    for k in range(-2,3):
        gfx.filled_circle(surf, int(cx+k*r*0.18), int(cy), int(r*0.65 - abs(k)*int(r*0.08)), orange)
    pygame.draw.rect(surf, green, (cx- r*0.12, cy - r*0.9, r*0.24, r*0.3))
    gfx.aacircle(surf, int(cx), int(cy), int(r*0.8), dark)
    pygame.draw.polygon(surf, face, [(cx-r*0.28,cy-r*0.15),(cx-r*0.1,cy-r*0.35),(cx-r*0.0,cy-r*0.1)])
    pygame.draw.polygon(surf, face, [(cx+r*0.28,cy-r*0.15),(cx+r*0.1,cy-r*0.35),(cx+0.0,cy-r*0.1)])
    pygame.draw.polygon(surf, face, [(cx-r*0.25,cy+r*0.2),(cx+r*0.25,cy+r*0.2),(cx,cy+r*0.35)])

def icon_bats(surf, cx, cy, r):
    black=(20,20,35)
    def bat(x,y,s=1):
        wing=[(x-30*s,y),(x-18*s,y-8*s),(x-6*s,y),(x+6*s,y),(x+18*s,y-8*s),(x+30*s,y)]
        pygame.draw.lines(surf, black, False, wing, max(1,int(3*s)))
        gfx.filled_circle(surf, int(x), int(y), int(6*s), black)
        pygame.draw.polygon(surf, black, [(x-5*s,y-6*s),(x,y-14*s),(x+5*s,y-6*s)])
    bat(cx-r*0.25, cy-r*0.05, r*0.06)
    bat(cx+r*0.15, cy+r*0.05, r*0.08)
    bat(cx-0, cy+r*0.12, r*0.05)

def icon_web(surf, cx, cy, r):
    draw_spiderweb(surf, int(cx), int(cy), int(r*0.7), turns=8, rings=5, color=(235,235,250))
    draw_spider(surf, int(cx+r*0.45), int(cy+r*0.05), size=int(r*0.22), color=(35,35,35))

def icon_mummy(surf, cx, cy, r):
    band=(240,240,240); shade=(200,200,210); eye=(40,40,50)
    rect=pygame.Rect(0,0,int(r*1.0),int(r*1.2)); rect.center=(cx,cy)
    pygame.draw.rect(surf, band, rect, border_radius=int(r*0.2))
    for i in range(-3,4):
        y = cy + i*r*0.25
        pygame.draw.rect(surf, shade if i%2==0 else band, (cx-r*0.5, y, r, r*0.18), border_radius=8)
    gfx.filled_circle(surf, int(cx-r*0.2), int(cy-r*0.1), int(r*0.08), eye)
    gfx.filled_circle(surf, int(cx+r*0.2), int(cy-r*0.1), int(r*0.08), eye)

def icon_candies(surf, cx, cy, r):
    cols=[(255,99,132),(255,205,86),(54,162,235),(153,102,255)]
    for i,c in enumerate(cols):
        ang = -0.7 + i*0.45
        x = cx + r*0.5*math.cos(ang)
        y = cy + r*0.3*math.sin(ang)
        gfx.filled_circle(surf, int(x), int(y), int(r*0.12), c)
        pygame.draw.polygon(surf, (230,230,230), [(x-r*0.2,y),(x-r*0.28,y-r*0.06),(x-r*0.28,y+r*0.06)])
        pygame.draw.polygon(surf, (230,230,230), [(x+r*0.2,y),(x+r*0.28,y-r*0.06),(x+r*0.28,y+r*0.06)])

def icon_jelly(surf, cx, cy, r):
    body=(160,220,255,180); outline=(200,240,255)
    dome = pygame.Surface((int(r*2), int(r*2)), pygame.SRCALPHA)
    pygame.draw.ellipse(dome, body, (0, r*0.2, r*2, r*1.2))
    gfx.filled_circle(dome, int(r*0.8), int(r*1.0), int(r*0.12), (40,40,60))
    gfx.filled_circle(dome, int(r*1.2), int(r*1.0), int(r*0.12), (40,40,60))
    surf.blit(dome, dome.get_rect(center=(cx,cy)))
    pygame.draw.ellipse(surf, outline, (cx-r, cy-r*0.2, r*2, r*1.2), 2)

def icon_potion(surf, cx, cy, r):
    glass=(210,240,255); liquid=(120, 200, 255); cork=(160,110,70)
    pygame.draw.rect(surf, cork, (cx-r*0.12, cy-r*0.9, r*0.24, r*0.18))
    pygame.draw.rect(surf, glass, (cx-r*0.14, cy-r*0.7, r*0.28, r*0.22), border_radius=6)
    pygame.draw.ellipse(surf, glass, (cx-r*0.8, cy-r*0.2, r*1.6, r*1.1))
    pygame.draw.ellipse(surf, liquid, (cx-r*0.7, cy+r*0.15, r*1.4, r*0.55))
    pygame.draw.ellipse(surf, (255,255,255,120), (cx-r*0.4, cy+r*0.05, r*0.35, r*0.2))

ICON_DRAWERS = {
    "ghost":   icon_ghost,
    "pumpkin": icon_pumpkin,
    "bats":    icon_bats,
    "web":     icon_web,
    "mummy":   icon_mummy,
    "candies": icon_candies,
    "jelly":   icon_jelly,
    "potion":  icon_potion,
}

# ===== Entrada =====
class InputManager:
    def __init__(self, use_gpio=True, pin=17, debounce_ms=200):
        self.use_gpio = use_gpio
        self.pin = pin
        self.debounce_s = debounce_ms/1000.0
        self.last = 0
        if self.use_gpio:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            except Exception:
                self.use_gpio = False

    def pressed(self):
        now = time.time()
        if self.use_gpio:
            val = GPIO.input(self.pin)
            if val == 0 and (now - self.last) > self.debounce_s:
                self.last = now
                time.sleep(0.02)
                return True
        else:
            pressed = pygame.key.get_pressed()
            if pressed[pygame.K_SPACE] and (now - self.last) > self.debounce_s:
                self.last = now
                return True
        return False

    def cleanup(self):
        if self.use_gpio:
            GPIO.cleanup()

# ===== Ruleta =====
class StylizedWheel:
    def __init__(self, screen, segments):
        global USE_BG_IMAGE
        self.screen = screen
        self.dw, self.dh = self.screen.get_size()
        self.buf = pygame.Surface((self.dw*SS, self.dh*SS), pygame.SRCALPHA)

        self.segments = segments
        self.n = len(segments)
        self.per = 2*math.pi/self.n
        self.mids = [(i+0.5)*self.per for i in range(self.n)]

        self.angle = 0.0
        self.cx, self.cy = self.buf.get_width()//2, self.buf.get_height()//2
        self.radius = int(min(self.cx, self.cy)*0.8)

        self.r_inner = int(self.radius*0.22)
        self.r_outer = self.radius

        self.font_mid = pygame.font.SysFont("Arial", int(28*SS), bold=True)
        self.font_big = pygame.font.SysFont("Arial", int(64*SS), bold=True)

        self.confetti = []

        # --- Fondo: imagen o procedimental
        self.bg = pygame.Surface(self.buf.get_size(), pygame.SRCALPHA)
        if USE_BG_IMAGE:
            try:
                raw = pygame.image.load(BACKGROUND_PATH).convert_alpha()
                self.bg_img = pygame.transform.smoothscale(raw, (self.buf.get_width(), self.buf.get_height()))
                self.bg.blit(self.bg_img, (0, 0))
            except Exception as e:
                print(f"[WARN] No pude cargar {BACKGROUND_PATH}: {e}. Uso fondo procedimental.")
                USE_BG_IMAGE = False

        if not USE_BG_IMAGE:
            draw_vertical_gradient(self.bg, ORANGE1, ORANGE2)
            draw_dots(self.bg, 28*SS, 2*SS, DOT)
            draw_spiderweb(self.bg, int(90*SS), int(90*SS), int(120*SS), turns=9, rings=7, color=(255,245,220))
            draw_spiderweb(self.bg, self.buf.get_width()-int(120*SS), int(70*SS), int(140*SS), turns=9, rings=7, color=(255,245,220))
            draw_spider(self.bg, int(self.buf.get_width()*0.87), int(self.buf.get_height()*0.16), size=int(14*SS), color=(35,35,35))

    def _draw_center_skull(self):
        cx,cy = self.cx, self.cy
        skull = (248,248,248)
        eye = (35,35,45)
        gfx.filled_circle(self.buf, cx, cy, int(self.r_inner*0.55), (10,10,12))
        gfx.filled_circle(self.buf, cx, cy, int(self.r_inner*0.4), skull)
        gfx.filled_circle(self.buf, int(cx - self.r_inner*0.18), int(cy - self.r_inner*0.05), int(self.r_inner*0.08), eye)
        gfx.filled_circle(self.buf, int(cx + self.r_inner*0.18), int(cy - self.r_inner*0.05), int(self.r_inner*0.08), eye)
        for i in range(-2,3):
            pygame.draw.rect(self.buf, eye, (cx+i*self.r_inner*0.08, cy+self.r_inner*0.18, self.r_inner*0.04, self.r_inner*0.12))

    def _draw_pointer(self):
        cx,cy = self.cx, self.cy
        tip = (cx, cy - self.r_outer - int(18*SS))
        base_y = cy - self.r_outer + int(40*SS)
        left = (cx - int(self.r_outer*0.08), base_y)
        right= (cx + int(self.r_outer*0.08), base_y)
        shadow=[(x+3*SS, y+3*SS) for x,y in (tip,left,right)]
        pygame.gfxdraw.filled_polygon(self.buf, [(int(x),int(y)) for x,y in shadow], (0,0,0,90))
        pygame.gfxdraw.filled_polygon(self.buf, [(int(x),int(y)) for x,y in (tip,left,right)], (220,35,25))
        pygame.gfxdraw.aapolygon(self.buf, [(int(x),int(y)) for x,y in (tip,left,right)], (90,0,0))

    def _draw_hands(self):
        draw_skeleton_hand(self.buf, int(self.cx - self.r_outer*1.05), int(self.cy + self.r_outer*0.45), scale=SS*1.0, flip=False)
        draw_skeleton_hand(self.buf, int(self.cx + self.r_outer*1.05), int(self.cy + self.r_outer*0.45), scale=SS*1.0, flip=True)

    def _spawn_confetti(self):
        now = time.time()
        W,H = self.buf.get_size()
        cols = [(255,120,120),(255,196,110),(160,255,160),(160,200,255),(255,240,180)]
        for _ in range(CONFETTI_PARTICLES):
            self.confetti.append({
                "x": random.uniform(0,W),
                "y": random.uniform(0,H*0.6),
                "r": random.randint(2*SS, 4*SS),
                "c": random.choice(cols),
                "t": now + random.uniform(0.5, CONFETTI_TIME)
            })

    def draw(self, result_text=None):
        self.buf.blit(self.bg, (0,0))

        # Glow exterior
        for i in range(8,0,-1):
            r = self.r_outer + i*6*SS
            alpha = max(10, 28 - i*3)
            gfx.filled_circle(self.buf, self.cx, self.cy, r, (30,10,40,alpha))
        gfx.aacircle(self.buf, self.cx, self.cy, self.r_outer+3*SS, (30,12,45))
        gfx.aacircle(self.buf, self.cx, self.cy, self.r_outer+2*SS, (30,12,45))

        # Segmentos
        for i, seg in enumerate(self.segments):
            a0 = i*self.per + self.angle
            a1 = (i+1)*self.per + self.angle
            poly = wedge_polygon(self.cx, self.cy, self.r_inner, self.r_outer, a0, a1, steps=54)
            P = [(int(x),int(y)) for x,y in poly]
            pygame.gfxdraw.filled_polygon(self.buf, P, seg["color"])
            pygame.gfxdraw.aapolygon(self.buf, P, (0,0,0,40))

        # Divisiones
        for i in range(self.n):
            a = i*self.per + self.angle
            x0 = self.cx + self.r_inner*math.cos(a)
            y0 = self.cy + self.r_inner*math.sin(a)
            x1 = self.cx + self.r_outer*math.cos(a)
            y1 = self.cy + self.r_outer*math.sin(a)
            pygame.draw.aaline(self.buf, (0,0,0), (x0,y0), (x1,y1))

        # Íconos
        for i,seg in enumerate(self.segments):
            mid = self.mids[i] + self.angle
            rx = self.cx + (self.r_inner + (self.r_outer-self.r_inner)*0.58)*math.cos(mid)
            ry = self.cy + (self.r_inner + (self.r_outer-self.r_inner)*0.58)*math.sin(mid)
            drawer = ICON_DRAWERS.get(seg.get("icon"))
            if drawer:
                drawer(self.buf, rx, ry, r=int(self.r_outer*0.16))

        # Centro, puntero y manos
        self._draw_center_skull()
        self._draw_pointer()
        self._draw_hands()

        # Confetti
        now = time.time()
        self.confetti = [p for p in self.confetti if p["t"] > now]
        for p in self.confetti:
            pygame.gfxdraw.filled_circle(self.buf, int(p["x"]), int(p["y"]), p["r"], p["c"])

        # Resultado
        if result_text:
            s = self.font_big.render(result_text, True, TEXT)
            self.buf.blit(s, s.get_rect(center=(self.cx, int(64*SS))))

        # Downscale y blit
        scaled = pygame.transform.smoothscale(self.buf, (self.dw, self.dh))
        self.screen.blit(scaled, (0,0))

    def spin_to(self, idx, duration=SPIN_DURATION):
        start = self.angle % (2*math.pi)
        pointer_world = -math.pi/2
        target_mid = idx*self.per + self.per/2
        base_delta = pointer_world - target_mid
        extra = random.uniform(SPIN_MIN_TURNS, SPIN_MAX_TURNS) * 2*math.pi
        total = base_delta + extra

        t0 = time.time()
        clock = pygame.time.Clock()
        while True:
            t = min(1.0, (time.time()-t0)/duration)
            self.angle = start + total*ease_out_cubic(t)
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)
            if t >= 1.0:
                break
        self.angle = start + total

    def index_under_pointer(self):
        ang = (-math.pi/2) - self.angle
        ang %= (2*math.pi)
        return int(ang // self.per)

    def celebrate(self): self._spawn_confetti()

# ===== Lógica principal =====
def weighted_choice(items, weights):
    if not weights: return random.randrange(len(items))
    total=float(sum(weights)); r=random.uniform(0,total); acc=0.0
    for i,w in enumerate(weights):
        acc+=w
        if r<=acc: return i
    return len(items)-1

def main():
    pygame.init()
    flags = pygame.FULLSCREEN if FULLSCREEN else 0
    screen = (pygame.display.set_mode((0,0), flags) if FULLSCREEN
              else pygame.display.set_mode(WINDOW_SIZE))
    pygame.display.set_caption(TITLE)

    wheel = StylizedWheel(screen, SEGMENTS)
    inputs = InputManager(use_gpio=USE_GPIO, pin=BUTTON_GPIO, debounce_ms=DEBOUNCE_MS)
    hint_font = pygame.font.SysFont("Arial", 22)

    running=True; can_spin=True
    last_label=None; until=0
    clock=pygame.time.Clock()

    try:
        while running:
            for e in pygame.event.get():
                if e.type==pygame.QUIT: running=False
                elif e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: running=False

            if can_spin and inputs.pressed():
                can_spin=False
                target = weighted_choice(SEGMENTS, WEIGHTS)
                wheel.spin_to(target, duration=SPIN_DURATION)
                idx = wheel.index_under_pointer()
                seg = SEGMENTS[idx]
                last_label = seg["label"]
                until = time.time()+2.2
                wheel.celebrate()
                pygame.time.delay(160)
                can_spin=True

            wheel.draw(result_text=(f"Resultado: {last_label}" if last_label and time.time()<until else None))

            W,H = screen.get_size()
            hint = "ESPACIO para girar (modo PC)" if not USE_GPIO else "¡Apretá el botón para girar!"
            s = hint_font.render(hint, True, (245,245,245))
            screen.blit(s, s.get_rect(midbottom=(W//2, H-12)))

            pygame.display.flip()
            clock.tick(FPS)
    finally:
        inputs.cleanup()
        pygame.quit()

if __name__=="__main__":
    main()
