# config.py
import math

# --- Pantalla (cuadrada) ---
WIDTH  = 1200
HEIGHT = 1200
FPS = 60
FULLSCREEN = False

# --- Archivos ---
ASSET_DIR = "assets"
BACKGROUND_IMAGE = f"{ASSET_DIR}/fondo_halloween.png"
WHEEL_IMAGE      = f"{ASSET_DIR}/ruleta.png"  # PNG sin texto, transparente

# --- Ruleta ---
N_SEGMENTS = 8
SEGMENT_LABELS = ["Dulce" if i % 2 == 0 else "Truco" for i in range(N_SEGMENTS)]
SEGMENT_ANGLE  = 2 * math.pi / N_SEGMENTS
# --- Tamaño relativo de la ruleta (fracción del lado menor de la pantalla)
WHEEL_REL_SIZE = 0.82  # probá 0.75–0.90

# --- Animación ---
SPIN_MIN_TURNS = 6.2
SPIN_MAX_TURNS = 12.4
SPIN_DURATION  = 6.2
RESULT_TIME    = 2.4

# --- Estética ---
TEXT_COLOR = (255, 248, 227)  # blanco cálido
UI_SHADOW  = (25, 25, 25)
