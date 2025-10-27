# background.py
import pygame
from config import BACKGROUND_IMAGE, WIDTH, HEIGHT

def load_background():
    """Carga y ajusta el fondo cuadrado. Si no está, usa fallback liso."""
    try:
        bg = pygame.image.load(BACKGROUND_IMAGE).convert()
        bg = pygame.transform.smoothscale(bg, (WIDTH, HEIGHT))
        # Sutil oscurecido para que la ruleta destaque
        dark = bg.copy()
        dark.fill((235, 235, 235), special_flags=pygame.BLEND_RGB_MULT)
        return dark
    except Exception:
        surf = pygame.Surface((WIDTH, HEIGHT))
        # degradé naranja rápido
        top, bot = (255, 160, 60), (120, 50, 30)
        for y in range(HEIGHT):
            t = y / max(1, HEIGHT-1)
            c = (int(top[0] + (bot[0]-top[0])*t),
                 int(top[1] + (bot[1]-top[1])*t),
                 int(top[2] + (bot[2]-top[2])*t))
            pygame.draw.line(surf, c, (0, y), (WIDTH, y))
        return surf
