# test_sincronia.py
# Verifica que el chirp y el ADC arrancan SIEMPRE en el mismo instante:
# mide la posición del pico directo en 10 capturas independientes.
# A diferencia de la versión anterior, también busca en retardos NEGATIVOS
# (por si el chirp empieza ANTES que la grabación) y muestra la altura del pico.
# Detén main.py antes de correr esto.

import math
import utime
import config
import hw
import radar_core as rc
import fft_detector as fd

VENTANA = 40   # retardos a revisar: de -VENTANA a +VENTANA


def pico_con_negativos():
    """Correlación completa (incluye retardos negativos). Retorna (pos, valor)."""
    xr, xi, rr, ri = rc._xr, rc._xi, rc._rr, rc._ri
    n = rc.NFFT
    mitad = n // 2
    for i in (0, mitad):
        a = xr[i]; b = xi[i]
        xr[i] = a * rr[i] - b * ri[i]
        xi[i] = a * ri[i] + b * rr[i]
    for i in range(1, mitad):
        a = xr[i]; b = xi[i]
        xr[i] = 2.0 * (a * rr[i] - b * ri[i])
        xi[i] = 2.0 * (a * ri[i] + b * rr[i])
    for i in range(mitad + 1, n):
        xr[i] = 0.0
        xi[i] = 0.0
    fd.ifft(xr, xi)

    def env(lag):
        k = lag % n                     # los retardos negativos están al final
        return math.sqrt(xr[k] * xr[k] + xi[k] * xi[k])

    mejor = -VENTANA
    vmax = 0.0
    for lag in range(-VENTANA, VENTANA + 1):
        v = env(lag)
        if v > vmax:
            vmax = v
            mejor = lag
    y0 = env(mejor - 1); y1 = vmax; y2 = env(mejor + 1)
    den = y0 - 2.0 * y1 + y2
    frac = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    return mejor + frac, vmax


rc.iniciar()
utime.sleep_ms(300)
print("=" * 56)
print("SINCRONÍA CHIRP / ADC (10 capturas)")
print("Retardo acústico esperado del directo: ~{:.1f} muestras".format(
    config.SEPARACION_CM / 100.0 / rc.velocidad_sonido() * rc.FS))
posiciones = []
for i in range(10):
    buf, fs = hw.capturar(True)
    a = rc._acum
    for j in range(rc.N):
        a[j] = buf[j]
    rc._espectro(a)
    pos, val = pico_con_negativos()
    posiciones.append(pos)
    print("  captura {:2d}: pico en {:8.3f} muestras | altura {:10.1f}".format(
        i + 1, pos, val))
    utime.sleep_ms(config.PAUSA_MS)

var = max(posiciones) - min(posiciones)
print("-" * 56)
print("Variación: {:.3f} muestras = {:.2f} us".format(var, var / rc.FS * 1e6))
if var < 0.1:
    print("Excelente: disparo determinista (menos de 0.1 muestras).")
elif var < 0.5:
    print("Aceptable, pero hay algo de variación.")
else:
    print("[!] El disparo varía: algo no está sincronizado.")
print("=" * 56)