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

# ===== Texto curvo correcto (pantalla con eje Y hacia abajo) =====
def _measure_text_angle(font, text, radius):
    if not text:
        return 0.0
    total_px = sum(font.size(ch)[0] for ch in text)
    return total_px / max(1, radius)

def draw_arc_text(surf, text, font, center, radius, mid_angle, max_arc_angle,
                  color=(255,255,255), shadow=(20,20,20), shadow_offset=2):
    """
    Dibuja `text` centrado en `mid_angle` siguiendo un arco de radio `radius`,
    legible y sin espejo en ambos hemisferios.
    """
    if not text:
        return

    cx, cy = center

    # cuánto arco ocuparía naturalmente el texto según su ancho y el radio
    natural_span = _measure_text_angle(font, text, radius)
    span = min(natural_span, max_arc_angle * 0.90)

    left = (math.cos(mid_angle) < 0.0)  # hemisferio izquierdo de la rueda

    if left:
        # recorro el arco en sentido decreciente y REVERSO los caracteres
        start = mid_angle + span / 2.0
        step_sign = -1.0
        chars = text[::-1]
    else:
        start = mid_angle - span / 2.0
        step_sign = +1.0
        chars = text

    angle = start
    for ch in chars:
        w, _ = font.size(ch)
        dtheta = (w / max(1, radius)) * step_sign
        a = angle + dtheta / 2.0

        # posición sobre el arco
        x = cx + radius * math.cos(a)
        y = cy + radius * math.sin(a)

        # 🔧 Rotación correcta para coordenadas de pantalla (Y hacia abajo)
        # 👉 tu hallazgo: usar -deg(a) - 90 evita el efecto "espejo"
        ang_deg = -math.degrees(a) - 90.0

        # render + sombra
        glyph  = font.render(ch, True, color)
        gshade = font.render(ch, True, shadow)
        gshade = pygame.transform.rotozoom(gshade, ang_deg, 1.0)
        glyph  = pygame.transform.rotozoom(glyph,  ang_deg, 1.0)

        surf.blit(gshade, gshade.get_rect(center=(x+shadow_offset, y+shadow_offset)))
        surf.blit(glyph,  glyph.get_rect(center=(x, y)))

        angle += dtheta




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
        self.wheel_img = pygame.transform.smoothscale(self.wheel_img, (500, 500))
        # Img dulce y truco
        self.truco = pygame.image.load("assets/truco.png").convert_alpha()
        self.dulce = pygame.image.load("assets/dulce.png").convert_alpha()
        # Geometría del texto sobre la rueda
        self.r_outer = 500 // 2
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
        self.image_offset   = 5.515   # alinea textos con el PNG
        self.pointer_offset = 0.0   # alinea cálculo de índice con el puntero

        # Offset de posición (px) para mover rueda + textos juntos
        self.off_x = 0
        self.off_y = 0


        # Capa base con todos los textos ya colocados (sin rotación de rueda)
        self.labels_base = self._build_labels_surface()

        # Overlay de calibración
        self.show_calib = False

    def nudge(self, dx=0, dy=0):
        """Mueve la ruleta y las letras juntas."""
        self.off_x += dx
        self.off_y += dy

    def draw_pointer(self):
        """
        Puntero negro con borde blanco, centrado arriba y con la punta
        apoyada sobre la circunferencia de la ruleta.
        """
        cx = self.cx + self.off_x
        cy = self.cy + self.off_y

        # tamaño relativo (más grande)
        base_height = int(self.r_outer * 0.18)
        half_width = int(self.r_outer * 0.12)

        # la punta se apoya sobre la circunferencia de la ruleta
        tip_y = cy - self.r_outer + int(self.r_outer * 0.03 + 325)
        base_y = tip_y - base_height

        tip = (cx, tip_y)
        left = (cx - half_width, base_y)
        right = (cx + half_width, base_y)

        pygame.draw.polygon(self.screen, (0, 0, 0), [tip, left, right])
        pygame.draw.polygon(self.screen, (255, 255, 255), [tip, left, right], 3)

    def _build_labels_surface(self) -> pygame.Surface:
        surf = pygame.Surface((820, 820), pygame.SRCALPHA)
        cx, cy = 410, 410
        for i in range(N_SEGMENTS):
            mid = (i + 0.5) * SEGMENT_ANGLE + self.image_offset  # SOLO offset de imagen
            draw_arc_text(
                surf,
                SEGMENT_LABELS[i],
                self.font_label,
                center=(cx, cy),
                radius=self.label_r,
                mid_angle=mid,
                max_arc_angle=SEGMENT_ANGLE * 0.80,
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

        center = (self.cx + self.off_x, self.cy + self.off_y+200)

        wheel_rot = pygame.transform.rotozoom(self.wheel_img, math.degrees(self.angle), 1.0)
        self.screen.blit(wheel_rot, wheel_rot.get_rect(center=center))

        labels_rot = pygame.transform.rotozoom(self.labels_base, math.degrees(self.angle), 1.0)
        self.screen.blit(labels_rot, labels_rot.get_rect(center=center))



        # 4) Overlay de calibración (opcional)
        if self.show_calib:
            self._draw_calibration_overlay()
        self.draw_pointer()
        # 3) Resultado con imagen (Dulce o Truco)
        if self.result and time.time() < self.result_until:
            if self.result.lower() == "dulce":
                img = self.dulce
            else:
                img = self.truco

            # Escala según el tamaño de pantalla (ajustá a gusto)
            size = int(min(WIDTH, HEIGHT) * 0.5)
            img = pygame.transform.smoothscale(img, (size, size))

            # Dibujar centrada en la parte superior
            rect = img.get_rect(center=(self.cx, self.cy))
            self.screen.blit(img, rect)
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
