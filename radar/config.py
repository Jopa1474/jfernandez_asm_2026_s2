# config.py
# Todos los parámetros del radar en un solo lugar, para que la emisión,
# la referencia de correlación y el análisis espectral siempre coincidan.

# ─── Pines ────────────────────────────────────────────────────────────
PIN_MIC = 26            # GP26 / ADC0 (pin físico 31)
PIN_PARLANTE = 15       # GP15 -> filtro RC (1k + 10nF) -> entrada del PAM8403

# ─── Muestreo ─────────────────────────────────────────────────────────
PERIODO_US = 30         # periodo de muestreo objetivo: 30 us ~ 33.3 kHz
N_CAPTURA = 1536        # muestras por medición (~46 ms a 33 kHz)

# ─── Chirp ────────────────────────────────────────────────────────────
F_INICIO = 3000         # Hz (3 x F_INICIO > F_FIN: el 3er armónico del PWM queda fuera de banda)
F_FIN = 8000            # Hz
DURACION_CHIRP_MS = 5   # duración del barrido
PASOS_CHIRP = 50        # escalones de frecuencia del PWM (uno cada 100 us)
RETARDO_INICIO_MS = 2   # espera antes de sonar, para que la grabación ya esté corriendo

# ─── Física y geometría ───────────────────────────────────────────────
TEMPERATURA_C = 25.0    # para la velocidad del sonido: v = 331.3 + 0.606*T
SEPARACION_CM = 5.0     # distancia entre el parlante y el micrófono
DIST_MIN_CM = 15.0      # distancia mínima a buscar (evita el pico directo)
DIST_MAX_CM = 300.0     # distancia máxima a buscar

# ─── Detección ────────────────────────────────────────────────────────
UMBRAL_ECO = 4.0        # el eco debe superar UMBRAL_ECO veces el nivel de ruido
USAR_CALIBRACION = True # restar el perfil del cuarto vacío (mesa, paredes, etc.)
N_CALIBRACION = 3       # mediciones promediadas para la calibración

# ─── Depuración ───────────────────────────────────────────────────────
GRAFICAR_PERFIL = False # True: imprime el perfil de correlación para el Graficador de Thonny