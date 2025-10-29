# test_serial_auto.py
import time, sys
import serial
from serial.tools import list_ports

print("🔍 Buscando puertos disponibles...\n")

ports = list_ports.comports()
if not ports:
    print("⚠ No se encontraron puertos. ¿Arduino conectado? ¿Driver instalado? ¿Cable de datos?")
    sys.exit(1)

for p in ports:
    print(f"→ {p.device}   |   {p.description}")

# 1) Intento por descripción (Arduino/Mega/CH340)
candidates = [p for p in ports if any(k in (p.description or "").lower() for k in ("arduino", "mega", "ch340"))]

# 2) Si no hay candidatos claros, probamos todos (último recurso)
if not candidates:
    candidates = ports

ser = None
for p in candidates:
    try:
        print(f"\n⏳ Abriendo {p.device} a 115200...")
        ser = serial.Serial(p.device, 115200, timeout=0.2)
        time.sleep(2.0)           # Mega se resetea al abrir
        ser.reset_input_buffer()
        print(f"✅ OK: {p.device} ({p.description})")
        break
    except Exception as e:
        print(f"❌ No pude abrir {p.device}: {e}")
        ser = None

if not ser:
    print("\n❌ No logré abrir ningún puerto. Cerrá el Monitor Serial del IDE y probá otro cable/USB.")
    sys.exit(2)

print("\n✅ Listo. APRETÁ EL BOTÓN en el Arduino (debería verse '1' cada vez):\n")
try:
    while True:
        if ser.in_waiting:
            line = ser.readline().decode(errors="ignore").strip()
            if line:
                print(f"📩 Recibido: {line}")
        # evitamos 100% CPU
        time.sleep(0.01)
except KeyboardInterrupt:
    print("\nCerrando...")
finally:
    try: ser.close()
    except: pass
