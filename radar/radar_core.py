# radar_core.py
# Correlación por FFT, promedio coherente, resta coherente del fondo y
# estimación de distancia.
#
# Como hw.py dispara el chirp y el ADC por hardware, TODAS las capturas quedan
# alineadas muestra a muestra. Eso permite:
#   1. Promediar las capturas directamente en el tiempo (el ruido baja y la
#      señal se mantiene).
#   2. Restar el fondo ANTES de correlacionar, en el espectro: D = X - F.
#      El sonido directo y los ecos fijos del cuarto se cancelan de verdad,
#      y queda solo lo que cambió (el objeto).
#   3. Correlacionar D con el chirp: c = IFFT(D · conj(R)), tomar la envolvente
#      con la señal analítica y buscar el pico del eco.
#   d = (v · Δt + separación) / 2, con Δt = eco - pico directo (de la calibración).

import math
import array
import utime
import micropython

import config
import hw
import fft_detector as fd


# ─── Utilidades ───────────────────────────────────────────────────────
def velocidad_sonido():
    """Velocidad del sonido en m/s según la temperatura."""
    return 331.3 + 0.606 * config.TEMPERATURA_C


def _pot2(n):
    p = 1
    while p < n:
        p <<= 1
    return p


def _muestras_para(dist_cm, fs):
    """Retardo (en muestras, respecto al pico directo) de un eco a dist_cm."""
    dt = (2.0 * dist_cm - config.SEPARACION_CM) / 100.0 / velocidad_sonido()
    return max(0, int(dt * fs))


# ─── Memoria reservada una sola vez ───────────────────────────────────
FS = hw.FS
N = config.N_CAPTURA
M = int(FS * config.DURACION_CHIRP_MS / 1000)
NFFT = _pot2(N + M - 1)          # evita la correlación circular
N_LAGS = N - M

_xr = array.array('f', [0.0] * NFFT)
_xi = array.array('f', [0.0] * NFFT)
_rr = array.array('f', [0.0] * NFFT)
_ri = array.array('f', [0.0] * NFFT)
_fr = array.array('f', [0.0] * NFFT)   # espectro del fondo
_fi = array.array('f', [0.0] * NFFT)
_acum = array.array('f', [0.0] * N)

_LARGO_MAX = _muestras_para(config.DIST_MAX_CM, FS) + 4
_perfil = array.array('f', [0.0] * _LARGO_MAX)
_largo = 0

_listo = False
_hay_fondo = False
_lag_dir = 0.0      # posición del pico directo (fraccional), de la calibración
_amp_dir = 1.0      # altura del pico directo, para normalizar


def _preparar_referencia():
    """conj(FFT(chirp de referencia)), igual al que emite hw.py."""
    for i in range(NFFT):
        _rr[i] = 0.0
        _ri[i] = 0.0
    T = M / FS
    k = (config.F_FIN - config.F_INICIO) / T
    f0 = config.F_INICIO
    for n in range(M):
        t = n / FS
        w = 0.5 - 0.5 * math.cos(2 * math.pi * n / (M - 1))
        _rr[n] = w * math.sin(2 * math.pi * (f0 * t + 0.5 * k * t * t))
    fd.fft(_rr, _ri)
    for i in range(NFFT):
        _ri[i] = -_ri[i]


def iniciar():
    global _listo
    if not _listo:
        _preparar_referencia()
        _listo = True
    return FS


def apagar():
    hw.apagar()


# ─── Adquisición ──────────────────────────────────────────────────────
@micropython.native
def _sumar(a, b, n):
    for i in range(n):
        a[i] += b[i]


def _promediar(K):
    """Promedio coherente de K capturas con chirp (quedan en _acum)."""
    a = _acum
    for i in range(N):
        a[i] = 0.0
    for _ in range(K):
        buf, fs = hw.capturar(True)
        _sumar(a, buf, N)
        utime.sleep_ms(config.PAUSA_MS)
    inv = 1.0 / K
    for i in range(N):
        a[i] *= inv
    return a


# ─── Procesamiento ────────────────────────────────────────────────────
def _espectro(a):
    """Quita DC, aplica el pasa-altas, rellena con ceros y calcula la FFT."""
    xr, xi = _xr, _xi
    media = 0.0
    for i in range(N):
        media += a[i]
    media /= N
    # Pasa-altas de 1er orden: y[n] = α·(y[n-1] + x[n] - x[n-1])
    alfa = 1.0 / (1.0 + 2.0 * math.pi * config.F_HPF / FS)
    x_ant = a[0] - media
    y = 0.0
    for i in range(N):
        x = a[i] - media
        y = alfa * (y + x - x_ant)
        x_ant = x
        xr[i] = y
        xi[i] = 0.0
    for i in range(N, NFFT):
        xr[i] = 0.0
        xi[i] = 0.0
    fd.fft(xr, xi)
    return fd.energia_en_banda(xr, xi, FS, config.F_INICIO, config.F_FIN)


def _envolvente():
    """
    Con el espectro en _xr/_xi: multiplica por conj(R), anula las frecuencias
    negativas (señal analítica), hace la IFFT y deja |c| en _xr[0..N_LAGS-1].
    """
    xr, xi, rr, ri = _xr, _xi, _rr, _ri
    mitad = NFFT // 2
    for i in (0, mitad):
        a = xr[i]; b = xi[i]
        xr[i] = a * rr[i] - b * ri[i]
        xi[i] = a * ri[i] + b * rr[i]
    for i in range(1, mitad):
        a = xr[i]; b = xi[i]
        xr[i] = 2.0 * (a * rr[i] - b * ri[i])
        xi[i] = 2.0 * (a * ri[i] + b * rr[i])
    for i in range(mitad + 1, NFFT):
        xr[i] = 0.0
        xi[i] = 0.0
    fd.ifft(xr, xi)
    for i in range(N_LAGS):
        xr[i] = math.sqrt(xr[i] * xr[i] + xi[i] * xi[i])


def _pico_directo():
    """Máximo de la envolvente, con precisión sub-muestra. Retorna (pos, valor)."""
    env = _xr
    idx = 0
    vmax = 0.0
    for i in range(N_LAGS):
        if env[i] > vmax:
            vmax = env[i]
            idx = i
    frac = 0.0
    if 0 < idx < N_LAGS - 1:
        y0 = env[idx - 1]; y1 = env[idx]; y2 = env[idx + 1]
        den = y0 - 2.0 * y1 + y2
        if den != 0:
            frac = 0.5 * (y0 - y2) / den
    return idx + frac, vmax


def _llenar_perfil(pos0, norm):
    """_perfil[j] = envolvente en (pos0 + j) / norm, con interpolación lineal."""
    global _largo
    env = _xr
    largo = min(_LARGO_MAX, N_LAGS - int(pos0) - 2)
    inv = 1.0 / (norm + 1e-12)
    for j in range(largo):
        pos = pos0 + j
        k = int(pos)
        a = pos - k
        _perfil[j] = ((1.0 - a) * env[k] + a * env[k + 1]) * inv
    _largo = largo
    return largo


def perfil_actual():
    """Para graficar: (arreglo, largo) del último perfil."""
    return _perfil, _largo


# ─── Calibración y medición ───────────────────────────────────────────
def calibrar_fondo(n=config.N_CALIBRACION):
    """
    Promedia n chirps SIN objeto y guarda su espectro (el fondo).
    También guarda la posición del pico directo como referencia de tiempo.
    """
    global _hay_fondo, _lag_dir, _amp_dir
    iniciar()
    a = _promediar(n)
    _espectro(a)
    for i in range(NFFT):
        _fr[i] = _xr[i]
        _fi[i] = _xi[i]
    _envolvente()
    _lag_dir, _amp_dir = _pico_directo()
    _hay_fondo = True
    return _lag_dir


def medir(usar_fondo=True):
    """Una medición completa. Retorna un diccionario con los resultados."""
    iniciar()
    a = _promediar(config.N_PROMEDIO)
    ratio, f_pico = _espectro(a)

    restar = usar_fondo and _hay_fondo
    if restar:
        # Resta coherente: solo queda lo que cambió respecto al fondo
        for i in range(NFFT):
            _xr[i] -= _fr[i]
            _xi[i] -= _fi[i]
        _envolvente()
        pos0, norm = _lag_dir, _amp_dir
    else:
        _envolvente()
        pos0, norm = _pico_directo()

    largo = _llenar_perfil(pos0, norm)
    p = _perfil

    j_min = _muestras_para(config.DIST_MIN_CM, FS)
    res = {"detectado": False, "fs": FS, "ratio_banda": ratio,
           "f_pico": f_pico, "lag_directo": pos0, "snr": 0.0}

    if not restar:
        # Sin fondo: saltar la cola del pico directo
        while j_min < largo - 2 and p[j_min + 1] < p[j_min]:
            j_min += 1
    res["inicio_busqueda"] = j_min
    if j_min >= largo - 1:
        return res

    # Nivel de ruido (promedio de |perfil|) y pico del eco
    suma = 0.0
    j_eco = j_min
    pico = p[j_min]
    for j in range(j_min, largo):
        v = p[j]
        suma += v if v > 0 else -v
        if v > pico:
            pico = v
            j_eco = j
    ruido = suma / (largo - j_min) + 1e-12

    # Interpolación parabólica: precisión por debajo de una muestra
    delta = 0.0
    if j_min < j_eco < largo - 1:
        y0 = p[j_eco - 1]; y1 = p[j_eco]; y2 = p[j_eco + 1]
        den = y0 - 2.0 * y1 + y2
        if den != 0:
            delta = 0.5 * (y0 - y2) / den

    tau = (j_eco + delta) / FS
    v = velocidad_sonido()
    dist_cm = (v * tau * 100.0 + config.SEPARACION_CM) / 2.0

    res["detectado"] = pico > config.UMBRAL_ECO * ruido
    res["distancia_cm"] = dist_cm
    res["tof_ms"] = tau * 1000.0 + config.SEPARACION_CM / 100.0 / v * 1000.0
    res["lag_eco"] = j_eco
    res["snr"] = pico / ruido
    res["eco_rel"] = pico       # altura del eco relativa al directo
    return res


if __name__ == "__main__":
    print("fs:", iniciar())
    r = medir(usar_fondo=False)
    if r["detectado"]:
        print("Distancia: {:.1f} cm (SNR {:.1f})".format(r["distancia_cm"], r["snr"]))
    else:
        print("Sin eco claro")