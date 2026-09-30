# test_preamp.py
# Prueba del preamplificador: mide el ruido en silencio y el nivel del chirp
# directo, revisa si la señal se recorta y da un veredicto.
# Los valores se muestran en la escala de 16 bits (0-65535), como antes.
# Detén main.py antes de correr esto.

import math
import utime
import config
import hw

BLOQUE = 33          # ~1 ms a 33 kHz
CLIP_BAJO = 5500     # el transistor 2 se satura cerca de 0.2-0.3 V...
CLIP_ALTO = 44000    # ...y su colector no puede subir más allá de VF2 (~2.2-2.4 V)
ESCALA = 16          # 12 bits -> escala de 16 bits


def estadisticas(buf, n):
    media = 0
    lo = 65535
    hi = 0
    for i in range(n):
        v = buf[i] * ESCALA
        media += v
        if v < lo:
            lo = v
        if v > hi:
            hi = v
    media = media / n
    var = 0.0
    for i in range(n):
        d = buf[i] * ESCALA - media
        var += d * d
    return media, lo, hi, math.sqrt(var / n)


def pp_por_bloques(buf, n):
    res = []
    for i in range(0, n - BLOQUE + 1, BLOQUE):
        lo = 65535
        hi = 0
        for j in range(i, i + BLOQUE):
            v = buf[j] * ESCALA
            if v < lo:
                lo = v
            if v > hi:
                hi = v
        res.append(hi - lo)
    return res


def recortes(buf, n):
    c = 0
    for i in range(n):
        v = buf[i] * ESCALA
        if v < CLIP_BAJO or v > CLIP_ALTO:
            c += 1
    return c


n = config.N_CAPTURA
utime.sleep_ms(300)

print("=" * 50)
print("1) SILENCIO (no hagas ruido)")
utime.sleep_ms(500)
buf, fs = hw.capturar(False)
media, lo, hi, desv = estadisticas(buf, n)
bloques = pp_por_bloques(buf, n)
ruido_pp = sorted(bloques)[len(bloques) // 2]
volt = media * 3.3 / 65535
print("  fs             : {:.1f} Hz".format(fs))
print("  nivel DC       : {:.0f} cuentas ({:.2f} V)".format(media, volt))
print("  min / max      : {} / {}".format(lo, hi))
print("  desviación     : {:.1f} cuentas".format(desv))
print("  ruido p-p (1ms): {} cuentas".format(ruido_pp))

print("=" * 50)
print("2) CHIRP ({}-{} Hz, {} ms, amplitud {:.2f})".format(
    config.F_INICIO, config.F_FIN, config.DURACION_CHIRP_MS, config.AMPLITUD))
utime.sleep_ms(300)
buf, fs = hw.capturar(True)
bloques = pp_por_bloques(buf, n)
chirp_pp = max(bloques)
n_rec = recortes(buf, n)
media2, lo2, hi2, _ = estadisticas(buf, n)
print("  min / max      : {} / {}".format(lo2, hi2))
print("  chirp p-p (1ms): {} cuentas".format(chirp_pp))
print("  muestras recortadas: {}".format(n_rec))
print()
print("  Envolvente (p-p cada ~1 ms):")
escala = max(bloques) / 40.0 + 1e-9
for i, v in enumerate(bloques):
    print("  {:3d} ms |{:<40}| {}".format(i, "#" * int(v / escala), v))

snr = chirp_pp / (ruido_pp + 1e-9)
print("=" * 50)
print("RESULTADO")
print("  Relación chirp/ruido: {:.1f} veces ({:.1f} dB)".format(
    snr, 20 * math.log10(snr + 1e-9)))
ok = True
if ruido_pp > 3000:
    print("  [!] Ruido en silencio muy alto ({} cuentas p-p).".format(ruido_pp))
    ok = False
if not (0.6 < volt < 2.4):
    print("  [!] Nivel DC fuera de zona ({:.2f} V). Revisa la polarización.".format(volt))
    ok = False
if n_rec > 0:
    print("  [!] La señal se recorta ({} muestras): baja AMPLITUD en config.py".format(n_rec))
    print("      o el volumen, o separa el parlante del micrófono.")
    ok = False
if chirp_pp < 3000:
    print("  [!] Chirp débil (< 3000 cuentas p-p). Sube AMPLITUD o el volumen.")
    ok = False
if ok:
    print("  Todo bien: señal fuerte, sin recortes y bien centrada.")
print("=" * 50)