# serial_manager.py
import time
import serial
from serial.tools import list_ports

BAUD = 115200
OPEN_WAIT = 2.0
RETRY_TIME = 3.0   # intentar reconectar cada 3s
TIMEOUT = 0.05

ser = None
last_connect_attempt = 0.0


# ------------------- DETECCIÓN DE ARDUINO -------------------

def _is_arduino(p):
    """Detecta Arduino / CH340 / clones por descripción."""
    desc = (p.description or "").lower()
    return any(k in desc for k in ("arduino", "mega", "ch340", "usb-serial", "usb serial", "cp210"))


def _find_port():
    ports = list_ports.comports()
    for p in ports:
        if _is_arduino(p):
            return p.device
    return None


def _connect():
    """Intenta abrir el puerto detectado automáticamente."""
    global ser
    port = _find_port()
    if not port:
        return False
    try:
        s = serial.Serial(port, BAUD, timeout=TIMEOUT)
        time.sleep(OPEN_WAIT)  # El Mega se reinicia al abrir el puerto
        s.reset_input_buffer()
        ser = s
        print(f"[Serial] ✅ Conectado a {port}")
        return True
    except Exception as e:
        print(f"[Serial] ❌ No se pudo abrir {port}: {e}")
        ser = None
        return False


# ------------------- API PARA LA RULETA -------------------

def get_button_press():
    """
    Llamar en cada frame desde main.
    Devuelve True cuando el Arduino envía '1'.
    Maneja reconexión automática.
    """
    global ser, last_connect_attempt

    # Si no está conectado → intentar reconectar
    if ser is None:
        now = time.time()
        if (now - last_connect_attempt) > RETRY_TIME:
            last_connect_attempt = now
            _connect()
        return False

    try:
        while ser.in_waiting:
            line = ser.readline().decode(errors="ignore").strip()
            if line == "1":
                return True
    except Exception as e:
        print(f"[Serial] ⚠️ Conexión perdida: {e}")
        try:
            ser.close()
        except:
            pass
        ser = None
        return False

    return False


# ------------------- MODO TEST STANDALONE -------------------

if __name__ == "__main__":
    print("\n=== 🟠 MODO PRUEBA DE BOTÓN (Arduino) 🟠 ===\n")
    print("Cerrá el Monitor Serial del IDE antes de continuar.\n")

    while True:
        pressed = get_button_press()
        if pressed:
            print("🔘  BOTÓN DETECTADO  (1)")
        time.sleep(0.02)   # evita usar 100% CPU
