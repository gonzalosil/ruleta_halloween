# main.py
import math, time, pygame
from config import *
from wheel import Wheel
import serial
from serial.tools import list_ports

# ------- GPIO opcional (solo en Raspberry Pi) -------
HAVE_GPIO = False
BUTTON_PIN = 17  # GPIO17 (pin físico 11). Botón al GND.

try:
    import RPi.GPIO as GPIO
    HAVE_GPIO = True
except Exception:
    HAVE_GPIO = False


def setup_gpio():
    if not HAVE_GPIO:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def cleanup_gpio():
    if HAVE_GPIO:
        GPIO.cleanup()

def open_arduino_serial(baud=115200):
    # Intento auto: busca puertos con "Arduino" en descripción
    for p in list_ports.comports():
        desc = (p.description or "").lower()
        if "arduino" in desc or "mega" in desc or "ch340" in desc:
            try:
                ser = serial.Serial(p.device, baudrate=baud, timeout=0.0)
                ser.reset_input_buffer()
                return ser
            except Exception:
                pass
    # Fallback: ajustá a mano si hace falta, ej: "COM3" en Windows, "/dev/ttyACM0" en Linux, "/dev/cu.usbmodemXXXX" en macOS
    try:
        return serial.Serial("COM3", baudrate=baud, timeout=0.0)  # cambia si no es COM3
    except Exception:
        return None

def main():
    pygame.init()

    flags = 0
    if FULLSCREEN:
        flags |= pygame.FULLSCREEN
    # Más suave en PC
    flags |= pygame.SCALED | pygame.DOUBLEBUF
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags, vsync=1)

    pygame.display.set_caption("Ruleta Halloween – 8 segmentos")

    setup_gpio()

    clock = pygame.time.Clock()
    wheel = Wheel(screen)
    running = True

    # Debounce para botón físico
    last_press_ts = 0.0
    DEBOUNCE_S = 0.25

    ser = open_arduino_serial()


    try:
        while running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        running = False
                    elif e.key == pygame.K_SPACE and not wheel.is_spinning:
                        wheel.start_spin()

                    # --- Calibración en vivo ---
                    elif e.key == pygame.K_c:
                        wheel.show_calib = not wheel.show_calib
                    elif e.key == pygame.K_r:
                        wheel.image_offset = 0.0
                        wheel.pointer_offset = 0.0
                        wheel.rebuild_labels()
                    elif e.key == pygame.K_LEFT:
                        wheel.adjust_image_offset(-math.radians(1))   # reconstruye capa
                    elif e.key == pygame.K_RIGHT:
                        wheel.adjust_image_offset(+math.radians(1))   # reconstruye capa
                    elif e.key == pygame.K_UP:
                        wheel.nudge(dy=-6)  # sube 6 px
                    elif e.key == pygame.K_DOWN:
                        wheel.nudge(dy=+6)  # baja 6 px

            # --- Botón externo por Arduino Mega (Serial) ---
            if ser and ser.in_waiting:
                try:
                    line = ser.readline().decode(errors="ignore").strip()
                except Exception:
                    line = ""
                if line == "1":
                    now = time.time()
                    if (now - last_press_ts) > DEBOUNCE_S and not wheel.is_spinning:
                        wheel.start_spin()
                        last_press_ts = now

            # --- Botón físico (solo en Pi) ---
            if HAVE_GPIO:
                if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # presionado (a GND)
                    now = time.time()
                    if (now - last_press_ts) > DEBOUNCE_S and not wheel.is_spinning:
                        wheel.start_spin()
                        last_press_ts = now

            wheel.update()
            wheel.draw()

            # (si en wheel.draw() dejaste el bloque de mostrar imagen de Dulce/Truco,
            # se dibuja al final y queda por encima de todo)

            pygame.display.flip()
            clock.tick(FPS)
    finally:
        cleanup_gpio()
        pygame.quit()
        if ser:
            try:
                ser.close()
            except:
                pass


if __name__ == "__main__":
    main()
