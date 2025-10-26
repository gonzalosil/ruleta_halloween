#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ruleta Halloween (imagen que gira) – pantalla completa
- Fondo fijo (PNG/JPG)
- Ruleta PNG que rota (se aplica máscara circular para ocultar puntero dibujado en la imagen si lo tuviera)
- Puntero fijo arriba
- Animación con easing (desaceleración)
- PC: barra ESPACIO  |  RPi: botón en GPIO 17 (pull-up)
"""

import math, random, time
import pygame

# ---------------- Config ----------------
FULLSCREEN = True
FPS = 60

BACKGROUND_PATH = "fondo_halloween.png"  # tu fondo
WHEEL_PATH      = "ruleta.png"           # ruleta PNG (transparente)

# Tamaño de la ruleta respecto a la pantalla (0.0–1.0)
WHEEL_SCALE = 0.85

# Entrada física
BUTTON_GPIO = 17
DEBOUNCE_MS = 200
USE_GPIO = True
try:
    import RPi.GPIO as GPIO
except Exception:
    USE_GPIO = False

# Easing / animación
SPIN_MIN_TURNS = 3.8
SPIN_MAX_TURNS = 6.5
SPIN_DURATION  = 3.8

# 6 segmentos: alterna Dulce/Truco
SEGMENT_LABELS = ["Dulce", "Truco", "Dulce", "Truco", "Dulce", "Truco"]
N_SEG = 6
SEG_PER_RAD = (2 * math.pi) / N_SEG

TEXT_COLOR = (250, 250, 250)

# -------------- Utilidades --------------
def ease_out_cubic(t: float) -> float:
    t -= 1.0
    return t * t * t + 1.0

def load_image_scaled(path, target_w=None, target_h=None, convert_alpha=True):
    img = pygame.image.load(path)
    img = img.convert_alpha() if convert_alpha else img.convert()
    if target_w and target_h:
        img = pygame.transform.smoothscale(img, (target_w, target_h))
    return img

def circular_mask(surface):
    """Devuelve una versión de 'surface' recortada a un círculo máximo (para ocultar puntero embebido)."""
    w, h = surface.get_size()
    r = min(w, h) // 2
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (w // 2, h // 2), r-1)
    # Multiplicamos alphas
    out = surface.copy()
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out

# --------------- Entrada ----------------
class InputManager:
    def __init__(self, use_gpio=True, pin=17, debounce_ms=200):
        self.use_gpio = use_gpio
        self.pin = pin
        self.debounce_s = debounce_ms / 1000.0
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
                self.last = now
                time.sleep(0.02)
                return True
        else:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE] and (now - self.last) > self.debounce_s:
                self.last = now
                return True
        return False

    def cleanup(self):
        if self.use_gpio:
            GPIO.cleanup()

# --------------- Juego ------------------
class WheelGame:
    def __init__(self, screen):
        self.screen = screen
        self.dw, self.dh = self.screen.get_size()
        self.center = (self.dw // 2, self.dh // 2)

        # Fondo
        self.bg = load_image_scaled(BACKGROUND_PATH, self.dw, self.dh, convert_alpha=False)

        # Ruleta
        wheel_target = int(min(self.dw, self.dh) * WHEEL_SCALE)
        self.wheel_base = load_image_scaled(WHEEL_PATH, wheel_target, wheel_target)
        self.wheel_base = circular_mask(self.wheel_base)  # por si la imagen trae puntero

        self.wheel_angle = 0.0  # en radianes
        self.font_result = pygame.font.SysFont("Arial", 64, bold=True)
        self.font_hint   = pygame.font.SysFont("Arial", 24)

        self.last_result = None
        self.result_until = 0.0

    def draw_pointer(self):
        cx, cy = self.center
        r = self.wheel_base.get_width() // 2
        tip = (cx, cy - r - 18)
        base_y = cy - r + 44
        left = (cx - int(r * 0.10), base_y)
        right = (cx + int(r * 0.10), base_y)
        pygame.gfxdraw.filled_polygon(self.screen, [tip, left, right], (225, 40, 30))
        pygame.gfxdraw.aapolygon(self.screen, [tip, left, right], (90, 0, 0))

    def draw_center_hub(self):
        cx, cy = self.center
        r = self.wheel_base.get_width() // 2
        hub_r = int(r * 0.2)
        pygame.gfxdraw.filled_circle(self.screen, cx, cy, int(hub_r*1.3), (12,12,14))
        pygame.gfxdraw.filled_circle(self.screen, cx, cy, hub_r, (248,248,248))
        pygame.gfxdraw.filled_circle(self.screen, cx - int(hub_r*0.45), cy - int(hub_r*0.15), int(hub_r*0.25), (35,35,45))
        pygame.gfxdraw.filled_circle(self.screen, cx + int(hub_r*0.45), cy - int(hub_r*0.15), int(hub_r*0.25), (35,35,45))

    def draw(self):
        # fondo
        self.screen.blit(self.bg, (0, 0))
        # ruleta rotada (rotozoom usa grados)
        angle_deg = -math.degrees(self.wheel_angle)   # signo negativo: sentido horario visual
        rotated = pygame.transform.rotozoom(self.wheel_base, angle_deg, 1.0)
        rect = rotated.get_rect(center=self.center)
        self.screen.blit(rotated, rect)

        # puntero fijo y centro
        self.draw_pointer()
        self.draw_center_hub()

        # mensaje de resultado temporal
        if self.last_result and time.time() < self.result_until:
            txt = self.font_result.render(f"Resultado: {self.last_result}", True, TEXT_COLOR)
            self.screen.blit(txt, txt.get_rect(midtop=(self.dw//2, 30)))

    def spin_to_random(self, duration):
        # Elegimos un objetivo al azar (por pesos iguales)
        target_index = random.randrange(N_SEG)
        self.spin_to_index(target_index, duration)

    def spin_to_index(self, target_index, duration):
        start = self.wheel_angle % (2 * math.pi)
        pointer_world = -math.pi / 2  # el puntero está arriba
        target_mid = target_index * SEG_PER_RAD + SEG_PER_RAD / 2
        base_delta = pointer_world - target_mid
        extra = random.uniform(SPIN_MIN_TURNS, SPIN_MAX_TURNS) * 2 * math.pi
        total = base_delta + extra

        t0 = time.time()
        clock = pygame.time.Clock()
        while True:
            t = min(1.0, (time.time() - t0) / duration)
            eased = ease_out_cubic(t)
            self.wheel_angle = start + total * eased

            self.draw()
            pygame.display.flip()
            clock.tick(FPS)
            if t >= 1.0:
                break

        self.wheel_angle = start + total
        # Determinar resultado:
        idx = self.index_under_pointer()
        self.last_result = SEGMENT_LABELS[idx]
        self.result_until = time.time() + 2.2

    def index_under_pointer(self):
        # Ángulo arriba es -pi/2. El “ángulo del mundo” del segmento arriba:
        world = (-math.pi / 2) - self.wheel_angle
        world %= (2 * math.pi)
        return int(world // SEG_PER_RAD)

# --------------- Main -------------------
def main():
    pygame.init()
    flags = pygame.FULLSCREEN if FULLSCREEN else 0
    screen = pygame.display.set_mode((0, 0), flags)
    pygame.display.set_caption("Ruleta Halloween (imagen que gira)")

    game = WheelGame(screen)
    inputs = InputManager(use_gpio=USE_GPIO, pin=BUTTON_GPIO, debounce_ms=DEBOUNCE_MS)

    hint_font = pygame.font.SysFont("Arial", 24)
    running = True
    can_spin = True
    clock = pygame.time.Clock()

    try:
        while running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    running = False

            if can_spin and inputs.pressed():
                can_spin = False
                game.spin_to_random(SPIN_DURATION)
                pygame.time.delay(160)
                can_spin = True

            game.draw()

            # hint (útil en PC)
            W, H = screen.get_size()
            hint = "ESPACIO para girar (PC)  •  ESC para salir" if not USE_GPIO else "¡Apretá el botón para girar!  •  ESC para salir"
            s = hint_font.render(hint, True, (245, 245, 245))
            screen.blit(s, s.get_rect(midbottom=(W // 2, H - 14)))

            pygame.display.flip()
            clock.tick(FPS)
    finally:
        inputs.cleanup()
        pygame.quit()

if __name__ == "__main__":
    main()
