# config.py
# Todos los parámetros del radar en un solo lugar, para que la emisión,
# la referencia de correlación y el análisis espectral siempre coincidan.

# ─── Pines ────────────────────────────────────────────────────────────
PIN_MIC = 26            # GP26 / ADC0 (pin físico 31)
PIN_PARLANTE = 15       # GP15 -> filtro RC (1k + 10nF) -> entrada del LM386

# ─── Muestreo (por hardware) ──────────────────────────────────────────
FS_OBJETIVO = 33333     # Hz. El ADC usa 48 MHz / divisor entero -> 33 333.3 Hz exactos
N_CAPTURA = 757         # muestras por chirp (~23 ms): con chirp de 8 ms la FFT queda de 1024

# ─── Chirp (senoidal generada por PWM + DMA) ──────────────────────────
F_INICIO = 3000         # Hz
F_FIN = 8000            # Hz
DURACION_CHIRP_MS = 8   # duración del barrido
AMPLITUD = 0.2          # 0.0 a 1.0: volumen del chirp desde el software
F_HPF = 2000            # pasa-altas digital antes de correlacionar (Hz)

# ─── Física y geometría ───────────────────────────────────────────────
TEMPERATURA_C = 25.0    # para la velocidad del sonido: v = 331.3 + 0.606*T
SEPARACION_CM = 0.0     # distancia entre el centro del parlante y el del micrófono
DIST_MIN_CM = 20.0      # zona ciega: no se buscan ecos más cerca
DIST_MAX_CM = 150.0     # distancia máxima a buscar (rango definido para el sistema)

# ─── Detección ────────────────────────────────────────────────────────
UMBRAL_ECO = 4.0        # el eco debe superar UMBRAL_ECO veces el nivel de ruido
USAR_CALIBRACION = False # restar el fondo (cuarto sin objeto) de forma coherente
N_CALIBRACION = 32      # chirps promediados para el fondo
N_PROMEDIO = 16          # chirps promediados en cada medición
PAUSA_MS = 150           # espera entre chirps para que se apague la reverberación

# ─── Depuración ───────────────────────────────────────────────────────
GRAFICAR_PERFIL = False # True: imprime el perfil de correlación para el Graficador de Thonny