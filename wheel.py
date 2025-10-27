# wheel.py
import math, time, random, pygame
from config import *
from background import load_background
def _measure_text_angle(font, text, radius):
    """Devuelve el ángulo total (en rad) que ocupa el texto sobre un arco,
    estimando cada letra por su ancho en pixeles / radius."""
    if not text:
        return 0.0
    total_px = sum(font.size(ch)[0] for ch in text)
    return total_px / max(1, radius)

def draw_arc_text(surf, text, font, center, radius, mid_angle, max_arc_angle,
                  color=(255,255,255), shadow=(20,20,20), shadow_offset=2):
    """
    Dibuja `text` centrado en `mid_angle` siguiendo el arco de radio `radius`.
    El texto ocupa como mucho `max_arc_angle` (rad). Cada letra se rota tangencialmente.
    """
    if not text:
        return
    cx, cy = center
    # ángulo “natural” que ocuparía el texto según su ancho
    natural_span = _measure_text_angle(font, text, radius)
    span = min(natural_span, max_arc_angle * 0.9)  # deja margen al borde del segmento
    start = mid_angle - span/2.0

    # recorre caracteres posicionándolos uno tras otro en el arco
    angle = start
    for ch in text:
        w, _ = font.size(ch)
        step = w / max(1, radius)  # ángulo que ocupa esta letra
        # ángulo central de la letra
        a = angle + step/2.0

        # posición en el arco
        x = cx + radius * math.cos(a)
        y = cy + radius * math.sin(a)

        # orientación tangencial (mirando hacia afuera)
        ang_deg = math.degrees(a) + 90

        # render + sombra
        glyph  = font.render(ch, True, color)
        gshade = font.render(ch, True, shadow)

        gshade = pygame.transform.rotozoom(gshade, ang_deg, 1.0)
        glyph  = pygame.transform.rotozoom(glyph,  ang_deg, 1.0)

        surf.blit(gshade, gshade.get_rect(center=(x+shadow_offset, y+shadow_offset)))
        surf.blit(glyph,  glyph.get_rect(center=(x, y)))

        angle += step

def ease_out_cubic(t: float) -> float:
    t -= 1.0
    return t*t*t + 1.0

class Wheel:
    def __init__(self, screen):
        self.screen = screen
        self.cx, self.cy = WIDTH//2, HEIGHT//2

        # Fondo
        self.bg = load_background()

        # Imagen de ruleta (PNG sin texto, transparente)
        self.wheel_img = pygame.image.load(WHEEL_IMAGE).convert_alpha()
        # Escala para dejar margen en 900x900
        self.wheel_img = pygame.transform.smoothscale(self.wheel_img, (820, 820))

        # Geometría del texto sobre la rueda
        self.r_outer = 820 // 2
        self.r_inner = int(self.r_outer * 0.22)
        self.label_r = int(self.r_inner + (self.r_outer - self.r_inner) * 0.60)

        # Estado de giro
        self.angle = 0.0
        self.is_spinning = False
        self.start_time = 0.0
        self.duration = 0.0
        self.start_angle = 0.0
        self.total_rotation = 0.0

        # Resultado
        self.result = None
        self.result_until = 0.0

        # Tipografías
        self.font_label  = pygame.font.SysFont("Arial", 42, bold=True)
        self.font_result = pygame.font.SysFont("Arial", 64, bold=True)
        self.font_small  = pygame.font.SysFont("Arial", 22)

        # Offsets de calibración (mutables en vivo)
        self.image_offset   = 0.0   # alinea textos con el PNG
        self.pointer_offset = 0.0   # alinea cálculo de índice con el puntero

        # Capa base con todos los textos ya colocados (sin rotación de rueda)
        self.labels_base = self._build_labels_surface()

        # Overlay de calibración
        self.show_calib = False

    # -------- construcción de la capa de textos (no depende de self.angle) -----
    def _build_labels_surface(self) -> pygame.Surface:
        """Crea una superficie 820x820 transparente con los 7 textos curvados.
        Usa image_offset para alinear con la gráfica del PNG."""
        surf = pygame.Surface((820, 820), pygame.SRCALPHA)
        cx, cy = 410, 410

        # radio donde irán las letras (ya lo tenés calculado en __init__)
        label_radius = self.label_r

        # cada etiqueta se dibuja centrada en el ángulo del segmento
        for i in range(N_SEGMENTS):
            mid = (i + 0.5) * SEGMENT_ANGLE + self.image_offset
            draw_arc_text(
                surf,
                SEGMENT_LABELS[i],
                self.font_label,
                center=(cx, cy),
                radius=label_radius,
                mid_angle=mid,
                max_arc_angle=SEGMENT_ANGLE * 0.80,  # ocupá ~80% del segmento
                color=TEXT_COLOR,
                shadow=UI_SHADOW,
                shadow_offset=2
            )
        return surf

    def rebuild_labels(self):
        """Llamar cuando cambie image_offset o el set de textos."""
        self.labels_base = self._build_labels_surface()

    # ---------- Giro ----------
    def start_spin(self):
        self.is_spinning   = True
        self.start_time    = time.time()
        self.duration      = SPIN_DURATION
        self.start_angle   = self.angle
        extra = random.uniform(SPIN_MIN_TURNS, SPIN_MAX_TURNS) * 2 * math.pi
        self.total_rotation = extra

    def update(self):
        if not self.is_spinning:
            return
        t = min((time.time() - self.start_time) / self.duration, 1.0)
        self.angle = self.start_angle + self.total_rotation * ease_out_cubic(t)
        if t >= 1.0:
            self.is_spinning = False
            self.angle %= 2 * math.pi

            # Puntero conceptual arriba (-90°) + OFFSET SOLO PARA CÁLCULO
            pointer = -math.pi/2 + self.pointer_offset
            raw = (pointer - self.angle) % (2 * math.pi)
            idx = int((raw + 1e-7) // SEGMENT_ANGLE) % N_SEGMENTS

            self.result = SEGMENT_LABELS[idx]
            self.result_until = time.time() + RESULT_TIME

    # ---------- Render ----------
    def draw(self):
        # Fondo
        self.screen.blit(self.bg, (0, 0))

        # 1) Rueda
        wheel_rot = pygame.transform.rotozoom(self.wheel_img, math.degrees(self.angle), 1.0)
        rect = wheel_rot.get_rect(center=(self.cx, self.cy))
        self.screen.blit(wheel_rot, rect)

        # 2) Capa de textos: se rota IGUAL que la rueda ⇒ siempre alineada
        labels_rot = pygame.transform.rotozoom(self.labels_base, math.degrees(self.angle), 1.0)
        self.screen.blit(labels_rot, labels_rot.get_rect(center=(self.cx, self.cy)))

        # 3) Resultado temporal
        if self.result and time.time() < self.result_until:
            s1 = self.font_result.render(f"Resultado: {self.result}", True, UI_SHADOW)
            s2 = self.font_result.render(f"Resultado: {self.result}", True, TEXT_COLOR)
            self.screen.blit(s1, s1.get_rect(center=(self.cx+3, 80+3)))
            self.screen.blit(s2, s2.get_rect(center=(self.cx, 80)))

        # 4) Overlay de calibración (opcional)
        if self.show_calib:
            self._draw_calibration_overlay()

    # ---------- Calibración ----------
    def adjust_image_offset(self, delta_rad: float):
        self.image_offset = (self.image_offset + delta_rad) % (2*math.pi)
        self.rebuild_labels()

    def adjust_pointer_offset(self, delta_rad: float):
        self.pointer_offset = (self.pointer_offset + delta_rad) % (2*math.pi)

    def _draw_calibration_overlay(self):
        box = pygame.Surface((380, 120), pygame.SRCALPHA)
        box.fill((0, 0, 0, 140))
        self.screen.blit(box, box.get_rect(topleft=(12, 12)))

        def deg(x): return f"{(math.degrees(x))%360:6.2f}°"
        lines = [
            "CALIBRACIÓN",
            f"Image Offset  (←/→): {deg(self.image_offset)}",
            f"Pointer Offset(↑/↓): {deg(self.pointer_offset)}",
            "R = reset  •  C = ocultar"
        ]
        y = 22
        for k, txt in enumerate(lines):
            col = (255, 230, 150) if k == 0 else (240, 240, 240)
            s = self.font_small.render(txt, True, col)
            self.screen.blit(s, (24, y))
            y += 26
