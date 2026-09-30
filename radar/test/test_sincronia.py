# test_sincronia.py
# Verifica que el chirp y el ADC arrancan SIEMPRE en el mismo instante:
# mide la posición del pico directo en 10 capturas independientes.
# Detén main.py antes de correr esto.

import utime
import config
import hw
import radar_core as rc

rc.iniciar()
utime.sleep_ms(300)
print("=" * 50)
print("SINCRONÍA CHIRP / ADC (10 capturas)")
posiciones = []
for i in range(10):
    buf, fs = hw.capturar(True)
    a = rc._acum
    for j in range(rc.N):
        a[j] = buf[j]
    rc._espectro(a)
    rc._envolvente()
    pos, val = rc._pico_directo()
    posiciones.append(pos)
    print("  captura {:2d}: pico directo en {:8.3f} muestras".format(i + 1, pos))
    utime.sleep_ms(config.PAUSA_MS)

var = max(posiciones) - min(posiciones)
print("-" * 50)
print("Variación: {:.3f} muestras = {:.2f} us".format(var, var / rc.FS * 1e6))
if var < 0.1:
    print("Excelente: disparo determinista (menos de 0.1 muestras).")
elif var < 0.5:
    print("Aceptable, pero hay algo de variación.")
else:
    print("[!] El disparo varía: algo no está sincronizado.")
print("=" * 50)