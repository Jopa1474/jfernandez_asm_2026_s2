# fft_detector.py
# FFT radix-2 iterativa (in-place, con bit-reversal), IFFT y análisis espectral.

import math
import array

import micropython

# Tablas de factores de giro (twiddle factors), calculadas una vez por tamaño N.
# Son más exactas y rápidas que actualizar w multiplicando en cada paso.
_tablas = {}


def _twiddles(n):
    if n not in _tablas:
        mitad = n // 2
        tw_r = array.array('f', [0.0] * mitad)
        tw_i = array.array('f', [0.0] * mitad)
        for k in range(mitad):
            ang = -2.0 * math.pi * k / n
            tw_r[k] = math.cos(ang)
            tw_i[k] = math.sin(ang)
        _tablas[n] = (tw_r, tw_i)
    return _tablas[n]


@micropython.native
def _fft_nucleo(xr, xi, tw_r, tw_i, n):
    # 1) Reordenamiento por inversión de bits
    j = 0
    for i in range(n - 1):
        if i < j:
            t = xr[i]; xr[i] = xr[j]; xr[j] = t
            t = xi[i]; xi[i] = xi[j]; xi[j] = t
        k = n >> 1
        while k <= j:
            j -= k
            k >>= 1
        j += k

    # 2) Mariposas de Cooley-Tukey, etapa por etapa
    largo = 2
    while largo <= n:
        mitad = largo >> 1
        paso = n // largo            # salto en la tabla de twiddles
        for inicio in range(0, n, largo):
            idx_w = 0
            for k in range(mitad):
                a = inicio + k
                b = a + mitad
                wr = tw_r[idx_w]
                wi = tw_i[idx_w]
                ur = xr[b] * wr - xi[b] * wi
                ui = xr[b] * wi + xi[b] * wr
                xr[b] = xr[a] - ur
                xi[b] = xi[a] - ui
                xr[a] = xr[a] + ur
                xi[a] = xi[a] + ui
                idx_w += paso
        largo <<= 1


def fft(xr, xi):
    """FFT in-place. xr, xi: arreglos de largo potencia de 2."""
    n = len(xr)
    tw_r, tw_i = _twiddles(n)
    _fft_nucleo(xr, xi, tw_r, tw_i, n)


def ifft(xr, xi):
    """
    IFFT in-place reutilizando la FFT:
    x = conj( FFT( conj(X) ) ) / N
    """
    n = len(xr)
    for i in range(n):
        xi[i] = -xi[i]
    fft(xr, xi)
    inv = 1.0 / n
    for i in range(n):
        xr[i] = xr[i] * inv
        xi[i] = -xi[i] * inv


def energia_en_banda(xr, xi, fs, f_min, f_max):
    """
    Con el espectro X[k] ya calculado, retorna:
      - ratio: energía (|X|^2) en la banda [f_min, f_max] / energía total
      - f_pico: frecuencia con mayor magnitud
    Solo se usa la primera mitad del espectro (simetría de señales reales)
    y se omite el bin de DC.
    """
    n = len(xr)
    df = fs / n
    k_min = int(f_min / df)
    k_max = int(f_max / df)
    e_banda = 0.0
    e_total = 1e-12
    k_pico = 1
    p_pico = 0.0
    for k in range(1, n // 2):
        p = xr[k] * xr[k] + xi[k] * xi[k]
        e_total += p
        if k_min <= k <= k_max:
            e_banda += p
        if p > p_pico:
            p_pico = p
            k_pico = k
    return e_banda / e_total, k_pico * df


if __name__ == "__main__":
    # Prueba en el Pico: espectro de lo que capta el micrófono
    # (reproduce un tono o el chirp cerca mientras corre).
    import sampler
    import config
    buf, fs = sampler.capturar()
    n = 1024
    media = sum(buf[i] for i in range(n)) / n
    xr = array.array('f', [buf[i] - media for i in range(n)])
    xi = array.array('f', [0.0] * n)
    # Ventana de Hann: solo para el análisis espectral (reduce la fuga espectral)
    for i in range(n):
        xr[i] *= 0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1))
    fft(xr, xi)
    ratio, f_pico = energia_en_banda(xr, xi, fs, config.F_INICIO, config.F_FIN)
    print("fs real: {:.1f} Hz".format(fs))
    print("Frecuencia dominante: {:.0f} Hz".format(f_pico))
    print("Energía en banda {}-{} Hz: {:.1f} %".format(
        config.F_INICIO, config.F_FIN, ratio * 100))
