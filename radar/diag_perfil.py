# diag_perfil.py
# Diagnóstico: imprime el perfil de ecos (ya sin el fondo) como una tabla
# distancia -> intensidad, para ver dónde aparecen los picos y si se mueven
# junto con el objeto.
# Detén main.py antes de correr esto.

import utime
import config
import radar_core as rc

PASO_CM = 3          # resolución de la tabla
DESDE_CM = 12
HASTA_CM = int(config.DIST_MAX_CM)


def fila_para(cm, fs):
    """Índice del perfil que corresponde a un eco a 'cm' centímetros."""
    v = rc.velocidad_sonido()
    return int(((2.0 * cm - config.SEPARACION_CM) / 100.0) / v * fs)


def imprimir_perfil(fs):
    p, largo = rc.perfil_actual()
    filas = []
    vmax = 1e-9
    for cm in range(DESDE_CM, HASTA_CM + 1, PASO_CM):
        j = fila_para(cm, fs)
        if j < 2 or j + 2 >= largo:
            continue
        m = max(p[j - 2], p[j - 1], p[j], p[j + 1], p[j + 2])
        filas.append((cm, m))
        if m > vmax:
            vmax = m
    for cm, m in filas:
        n = int(40 * m / vmax) if m > 0 else 0
        print("  {:4d} cm |{:<40}| {:.4f}".format(cm, "#" * n, m))


print("=" * 60)
print("DIAGNÓSTICO DEL PERFIL")
fs = rc.iniciar()
print("fs real: {:.1f} Hz".format(fs))
print("\nCalibrando: deja el frente SIN objeto...")
utime.sleep(2)
rc.calibrar_fondo()
print("Fondo registrado.\n")

while True:
    txt = input("Pon/mueve el objeto, escribe su distancia en cm y Enter (q = salir): ")
    if txt.strip().lower() == "q":
        break
    r = rc.medir(True)
    print("-" * 60)
    print("Objeto real: {} cm | medido: {} | SNR {:.1f}".format(
        txt.strip(),
        "{:.1f} cm".format(r["distancia_cm"]) if "distancia_cm" in r else "-",
        r.get("snr", 0.0)))
    imprimir_perfil(r["fs"])
    print("-" * 60)

rc.apagar()