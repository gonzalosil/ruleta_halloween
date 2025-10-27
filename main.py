#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ruleta Halloween – v4 patrones (6 secciones, sin PNGs)
- Dulce = cálidos | Truco = fríos
- Centro oscuro (sin blanco)
- Sin triángulo selector; puntero conceptual arriba
- PC: ESPACIO | RPi: GPIO 17
"""

import math, random, time, pygame

# ===== Config =====
FULLSCREEN = True
FPS = 60
SS = 2  # 2 = nítido; en RPi 2 podés bajar a 1

BACKGROUND_PATH = "fondo_halloween.png"  # si existe, se usa

# Entrada física (se desactiva si no hay GPIO)
BUTTON_GPIO = 17
DEBOUNCE_MS = 200
USE_GPIO = True
try:
    import RPi.GPIO as GPIO
except Exception:
    USE_GPIO = False

# Animación
SPIN_MIN_TURNS = 3.8
SPIN_MAX_TURNS = 6.2
SPIN_DURATION  = 3.8

# Geometría ruleta
N_SEG = 6
SEG_PER_RAD = 2 * math.pi / N_SEG

# Paleta
TEXT = (250, 250, 250)
UI_SHADOW = (0, 0, 0)

# Patrones de color:
# Dulce (cálidos) y Truco (fríos), alternados
WARM1 = (255, 120, 40)    # naranja
WARM2 = (255, 196, 58)    # amarillo calabaza
WARM3 = (255, 100, 150)   # fucsia candy
COOL1 = (98,  82, 160)    # violeta
COOL2 = (52,  140, 180)   # azul verdoso
COOL3 = (70,  185, 120)   # verde lima

SEGMENT_LABELS = ["Dulce", "Truco", "Dulce", "Truco", "Dulce", "Truco"]
SEG_COLORS     = [WARM1,  COOL1,  WARM2,  COOL2,  WARM3,  COOL3]

# ==== Utils ====
def ease_out_cubic(t: float) -> float:
    t -= 1.0; return t*t*t + 1.0

def clamp(v, a, b): return max(a, min(b, v))

def arc_points(cx, cy, r, a0, a1, steps=72):
    pts=[]
    for i in range(steps+1):
        t=i/steps; a=a0+(a1-a0)*t
        pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    return pts

def wedge_polygon(cx, cy, r0, r1, a0, a1, steps=72):
    return arc_points(cx,cy,r1,a0,a1,steps) + arc_points(cx,cy,r0,a1,a0,steps)

def load_bg_scaled(w, h):
    try:
        raw = pygame.image.load(BACKGROUND_PATH).convert()
        return pygame.transform.smoothscale(raw, (w, h))
    except Exception:
        # degradé simple fallback
        s = pygame.Surface((w,h))
        top, bot = (255,163,26), (248,122,13)
        for y in range(h):
            t = y/max(1,h-1)
            col = (int(top[0]+(bot[0]-top[0])*t),
                   int(top[1]+(bot[1]-top[1])*t),
                   int(top[2]+(bot[2]-top[2])*t))
            pygame.draw.line(s, col, (0,y), (w,y))
        return s

# ==== Iconos (procedurales y simples) ====
def icon_candies(surf, cx, cy, r):
    cols=[(255,99,132),(255,205,86),(54,162,235)]
    for i,c in enumerate(cols):
        x = int(cx + (i-1)*r*0.35)
        y = int(cy + ((i%2)*2-1)*r*0.08)
        pygame.draw.circle(surf, c, (x, y), int(r*0.14))
        pygame.draw.polygon(surf, (235,235,235), [(x-int(r*0.22),y),
                                                  (x-int(r*0.30),y-int(r*0.08)),
                                                  (x-int(r*0.30),y+int(r*0.08))])
        pygame.draw.polygon(surf, (235,235,235), [(x+int(r*0.22),y),
                                                  (x+int(r*0.30),y-int(r*0.08)),
                                                  (x+int(r*0.30),y+int(r*0.08))])

def icon_pumpkin(surf, cx, cy, r):
    orange=(255,140,0); face=(30,12,0); green=(40,140,40)
    for k in range(-2,3):
        pygame.draw.circle(surf, orange, (int(cx+k*r*0.18), int(cy)), int(r*0.7 - abs(k)*int(r*0.08)))
    pygame.draw.rect(surf, green, (int(cx-r*0.12), int(cy-r*0.95), int(r*0.24), int(r*0.3)))
    pygame.draw.polygon(surf, face, [(int(cx-r*0.28),int(cy-r*0.15)),(int(cx-r*0.08),int(cy-r*0.4)),(int(cx-0.0),int(cy-r*0.1))])
    pygame.draw.polygon(surf, face, [(int(cx+r*0.28),int(cy-r*0.15)),(int(cx+r*0.08),int(cy-r*0.4)),(int(cx+0.0),int(cy-r*0.1))])
    pygame.draw.polygon(surf, face, [(int(cx-r*0.25),int(cy+r*0.22)),(int(cx+r*0.25),int(cy+r*0.22)),(int(cx),int(cy+r*0.38))])

def icon_potion(surf, cx, cy, r):
    glass=(210,240,255); liquid=(255, 120, 190)  # rosa para “dulce”
    pygame.draw.rect(surf, (160,110,70), (int(cx-r*0.12), int(cy-r*0.9), int(r*0.24), int(r*0.18)))
    pygame.draw.rect(surf, glass, (int(cx-r*0.14), int(cy-r*0.7), int(r*0.28), int(r*0.22)), border_radius=6)
    pygame.draw.ellipse(surf, glass, (int(cx-r*0.8), int(cy-r*0.2), int(r*1.6), int(r*1.1)))
    pygame.draw.ellipse(surf, liquid, (int(cx-r*0.72), int(cy+r*0.12), int(r*1.44), int(r*0.58)))

def icon_ghost(surf, cx, cy, r):
    white=(235,235,245); eye=(35,35,45)
    body=pygame.Rect(0,0,int(r*1.2), int(r*1.35)); body.center=(int(cx),int(cy))
    pygame.draw.ellipse(surf, white, body)
    for i in range(-2,3):
        pygame.draw.circle(surf, white, (int(cx+i*r*0.22), int(cy+r*0.60)), int(r*0.22))
    pygame.draw.circle(surf, eye, (int(cx-r*0.2), int(cy-r*0.05)), int(r*0.1))
    pygame.draw.circle(surf, eye, (int(cx+r*0.2), int(cy-r*0.05)), int(r*0.1))

def icon_bats(surf, cx, cy, r):
    col=(25,25,40)
    def bat(x,y,s=1.0):
        wing=[(x-30*s,y),(x-18*s,y-8*s),(x-6*s,y),(x+6*s,y),(x+18*s,y-8*s),(x+30*s,y)]
        pygame.draw.lines(surf, col, False, [(int(a),int(b)) for a,b in wing], max(1,int(3*s)))
        pygame.draw.circle(surf, col, (int(x),int(y)), int(6*s))
        pygame.draw.polygon(surf, col, [(int(x-5*s),int(y-6*s)),(int(x),int(y-14*s)),(int(x+5*s),int(y-6*s))])
    bat(cx-r*0.1, cy-r*0.02, r*0.08); bat(cx+r*0.2, cy+r*0.06, r*0.06)

def icon_web(surf, cx, cy, r):
    color=(235,235,250); rad=int(r*0.8)
    for k in range(1,6):
        pygame.draw.circle(surf, color, (int(cx),int(cy)), int(rad*k/6), 1)
    for i in range(8):
        a=2*math.pi*i/8; x=cx+rad*math.cos(a); y=cy+rad*math.sin(a)
        pygame.draw.aaline(surf, color, (int(cx),int(cy)), (int(x),int(y)))

ICON_DRAWERS = {
    "candies": icon_candies,  # Dulce
    "pumpkin": icon_pumpkin,  # Dulce
    "potion":  icon_potion,   # Dulce (rosa)
    "ghost":   icon_ghost,    # Truco
    "bats":    icon_bats,     # Truco
    "web":     icon_web,      # Truco
}

# Mapeo iconos en sentido horario (arranca a la derecha)
ICONS_ORDER = ["candies","ghost","pumpkin","bats","potion","web"]

# ===== Entrada =====
class InputManager:
    def __init__(self, use_gpio=True, pin=17, debounce_ms=200):
        self.use_gpio = use_gpio
        self.pin = pin
        self.debounce_s = debounce_ms/1000.0
        self.last = 0.0
        if self.use_gpio:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            except Exception:
                self.use_gpio = False

    def pressed(self):
        now = time.time()
        if self.use_gpio:
            if GPIO.input(self.pin) == 0 and (now - self.last) > self.debounce_s:
                self.last = now; time.sleep(0.02); return True
        else:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE] and (now - self.last) > self.debounce_s:
                self.last = now; return True
        return False

    def cleanup(self):
        if self.use_gpio: GPIO.cleanup()

# ===== Wheel =====
class PatternWheel:
    def __init__(self, screen):
        self.screen = screen
        self.dw, self.dh = self.screen.get_size()
        self.buf = pygame.Surface((self.dw*SS, self.dh*SS)).convert()
        self.cx, self.cy = self.buf.get_width()//2, self.buf.get_height()//2
        self.radius = int(min(self.cx, self.cy) * 0.78)
        self.r_inner = int(self.radius * 0.22)
        self.r_outer = self.radius
        self.per = 2*math.pi / N_SEG
        self.mids = [(i+0.5)*self.per for i in range(N_SEG)]

        self.font_label  = pygame.font.SysFont("Arial", int(32*SS), bold=True)
        self.font_result = pygame.font.SysFont("Arial", int(72*SS), bold=True)
        self.font_hint   = pygame.font.SysFont("Arial", int(22*SS))

        self.bg = load_bg_scaled(self.buf.get_width(), self.buf.get_height())

        self.angle=0.0; self.is_spinning=False
        self.spin_start_time=0.0; self.spin_duration=0.0
        self.spin_start_angle=0.0; self.spin_total_delta=0.0
        self.last_result=None; self.result_until=0.0

    def _shadow_under_wheel(self):
        rx = int(self.r_outer * 0.95); ry = int(self.r_outer * 0.22)
        base = pygame.Surface((rx*2, ry*2), pygame.SRCALPHA)
        for i in range(14, 0, -1):
            alpha = int(8 + i*4)
            pygame.draw.ellipse(base, (0,0,0,alpha), (i*2, i, rx*2 - i*4, ry*2 - i*2))
        self.buf.blit(base, base.get_rect(center=(self.cx, int(self.cy + self.r_outer*0.82))))

    def _center_dark_hub(self):
        # Centro oscuro limpio (sin blanco)
        hub_r = int(self.r_outer*0.22)
        ring_r = int(self.r_outer*0.28)
        # aro metálico oscuro
        pygame.draw.circle(self.buf, (18,18,22), (self.cx, self.cy), ring_r)
        for i in range(10):
            pygame.draw.circle(self.buf, (40+6*i,40+6*i,50+7*i), (self.cx, self.cy), ring_r-i, 1)
        pygame.draw.circle(self.buf, (10,10,12), (self.cx, self.cy), hub_r)

    def draw(self):
        self.buf.blit(self.bg, (0,0))
        self._shadow_under_wheel()

        # segmentos + bordes
        for i in range(N_SEG):
            a0 = i*self.per + self.angle
            a1 = (i+1)*self.per + self.angle
            poly = wedge_polygon(self.cx, self.cy, self.r_inner, self.r_outer, a0, a1, steps=80)
            pygame.draw.polygon(self.buf, SEG_COLORS[i], [(int(x),int(y)) for x,y in poly])
            pygame.draw.polygon(self.buf, (20,20,28), [(int(x),int(y)) for x,y in poly], 1)

        # separadores finos
        for i in range(N_SEG):
            a = i*self.per + self.angle
            x0 = self.cx + self.r_inner*math.cos(a); y0 = self.cy + self.r_inner*math.sin(a)
            x1 = self.cx + self.r_outer*math.cos(a); y1 = self.cy + self.r_outer*math.sin(a)
            pygame.draw.aaline(self.buf, (10,10,16), (x0,y0), (x1,y1))

        # iconos + textos
        for i in range(N_SEG):
            mid = self.mids[i] + self.angle
            # icono
            ix = self.cx + (self.r_inner + (self.r_outer-self.r_inner)*0.60)*math.cos(mid)
            iy = self.cy + (self.r_inner + (self.r_outer-self.r_inner)*0.60)*math.sin(mid)
            ICON_DRAWERS[ICONS_ORDER[i]](self.buf, ix, iy, int(self.r_outer*0.16))
            # texto
            tx = self.cx + (self.r_inner + (self.r_outer-self.r_inner)*0.36)*math.cos(mid)
            ty = self.cy + (self.r_inner + (self.r_outer-self.r_inner)*0.36)*math.sin(mid)
            lbl = SEGMENT_LABELS[i]
            s1 = self.font_label.render(lbl, True, UI_SHADOW)
            s2 = self.font_label.render(lbl, True, TEXT)
            self.buf.blit(s1, s1.get_rect(center=(tx+2*SS, ty+2*SS)))
            self.buf.blit(s2, s2.get_rect(center=(tx, ty)))

        # centro oscuro
        self._center_dark_hub()

        # resultado temporal
        if self.last_result and time.time() < self.result_until:
            s1 = self.font_result.render(f"Resultado: {self.last_result}", True, UI_SHADOW)
            s2 = self.font_result.render(f"Resultado: {self.last_result}", True, TEXT)
            self.buf.blit(s1, s1.get_rect(center=(self.cx+3*SS, 70*SS+3*SS)))
            self.buf.blit(s2, s2.get_rect(center=(self.cx, 70*SS)))

        # salida
        scaled = pygame.transform.smoothscale(self.buf, (self.dw, self.dh))
        self.screen.blit(scaled, (0,0))

    # animación
    def start_spin_to_index(self, idx, duration):
        self.is_spinning = True
        self.spin_start_time = time.time()
        self.spin_duration = max(0.5, float(duration))
        self.spin_start_angle = self.angle % (2*math.pi)
        pointer_world = -math.pi / 2  # referencia arriba
        target_mid = idx * self.per + self.per/2
        base_delta = pointer_world - target_mid
        extra = random.uniform(SPIN_MIN_TURNS, SPIN_MAX_TURNS) * 2 * math.pi
        self.spin_total_delta = base_delta + extra

    def update(self):
        if not getattr(self, "is_spinning", False): return
        t = (time.time() - self.spin_start_time) / self.spin_duration
        t = clamp(t, 0.0, 1.0)
        self.angle = self.spin_start_angle + self.spin_total_delta * ease_out_cubic(t)
        if t >= 1.0:
            self.is_spinning = False
            idx = self.index_under_pointer()
            self.last_result = SEGMENT_LABELS[idx]
            self.result_until = time.time() + 2.0

    def index_under_pointer(self):
        world = (-math.pi / 2) - self.angle
        world %= (2 * math.pi)
        return int(world // (2*math.pi / N_SEG))

# ===== Main =====
def main():
    pygame.init()
    flags = pygame.FULLSCREEN if FULLSCREEN else 0
    screen = pygame.display.set_mode((0, 0), flags)
    pygame.display.set_caption("Ruleta Halloween – v4 Patrones")

    wheel = PatternWheel(screen)
    hint_font = pygame.font.SysFont("Arial", 24)
    inputs = InputManager(use_gpio=USE_GPIO, pin=BUTTON_GPIO, debounce_ms=DEBOUNCE_MS)
    clock = pygame.time.Clock()

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: running = False

        if not getattr(wheel, "is_spinning", False) and inputs.pressed():
            wheel.start_spin_to_index(random.randrange(N_SEG), SPIN_DURATION)

        wheel.update()
        wheel.draw()

        # hint
        W,H = screen.get_size()
        hint = "ESPACIO para girar (PC)  •  ESC para salir" if not USE_GPIO else "¡Botón para girar!  •  ESC para salir"
        s = hint_font.render(hint, True, (245,245,245))
        screen.blit(s, s.get_rect(midbottom=(W//2, H-14)))

        pygame.display.flip()
        clock.tick(FPS)

    inputs.cleanup()
    pygame.quit()

if __name__ == "__main__":
    main()
