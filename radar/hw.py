# hw.py
# Emisión del chirp y captura del micrófono sincronizadas POR HARDWARE.
#
#  - ADC: cada muestra se dispara a un ritmo exacto marcado por hardware.
#    Un canal DMA copia cada muestra de la FIFO del ADC a la RAM.
#  - Chirp: una senoidal precalculada. Otro canal DMA escribe el ciclo de
#    trabajo del PWM en cada período del PWM (~488 kHz): el PWM funciona como
#    un DAC y el filtro RC deja la senoidal.
#  - Reloj común: el ADC ya no usa su propio divisor (que arranca en una fase
#    al azar). Cada muestra la dispara un canal DMA en cada vuelta de otro PWM
#    (slice 0, a 33 333 Hz exactos). Los dos PWM (chirp y reloj del ADC) se
#    encienden con UNA sola escritura al registro EN, así que el chirp empieza
#    siempre en el mismo instante respecto a la primera muestra.
#
# Requiere MicroPython 1.23 o superior (módulo rp2.DMA).

import array
import math
import machine
import rp2
from machine import Pin, ADC, PWM, mem32
import config

# Fuente conmutada del Pico W en modo PWM: menos rizado, menos ruido en el ADC
try:
    Pin("WL_GPIO1", Pin.OUT, value=1)
except Exception:
    pass

# ─── Registros del RP2040 (datasheet, cap. 2.5, 4.5 y 4.9) ────────────
_ADC_BASE = 0x4004C000
_ADC_CS = _ADC_BASE + 0x00
_ADC_FCS = _ADC_BASE + 0x08
_ADC_FIFO = _ADC_BASE + 0x0C
_ADC_DIV = _ADC_BASE + 0x10
_DREQ_ADC = 36
_PWM_EN = 0x400500A0                # enciende varios slices a la vez

_CS_EN = 1
_CS_START_ONCE = 1 << 2
_CS_READY = 1 << 8
_AINSEL = (config.PIN_MIC - 26) << 12

_FCS_EN = 1
_FCS_DREQ_EN = 1 << 3
_FCS_UNDER = 1 << 10
_FCS_OVER = 1 << 11
_FCS_THRESH_1 = 1 << 24

# ─── ADC ──────────────────────────────────────────────────────────────
_adc = ADC(Pin(config.PIN_MIC))     # deja el pin como entrada analógica
_adc.read_u16()                     # enciende el ADC

# ─── Reloj de muestreo: slice 0 del PWM (sin pin; solo genera la cadencia) ─
_SL_ADC = 0
_ADC_PWM_BASE = 0x40050000 + 0x14 * _SL_ADC
_TOP_ADC = int(machine.freq() / config.FS_OBJETIVO + 0.5) - 1
FS = machine.freq() / (_TOP_ADC + 1)   # frecuencia de muestreo EXACTA
_DREQ_RELOJ = 24 + _SL_ADC
mem32[_ADC_PWM_BASE + 0x00] = 0        # CSR: detenido
mem32[_ADC_PWM_BASE + 0x04] = 1 << 4   # DIV = 1.0
mem32[_ADC_PWM_BASE + 0x10] = _TOP_ADC
mem32[_ADC_PWM_BASE + 0x08] = 0        # CTR
mem32[_ADC_PWM_BASE + 0x0C] = 0        # CC

# ─── PWM ──────────────────────────────────────────────────────────────
_pwm = PWM(Pin(config.PIN_PARLANTE))  # pone el pin en función PWM
_pwm.freq(400_000)
_pwm.duty_u16(0)
_SLICE = (config.PIN_PARLANTE >> 1) & 7
_SHIFT = 16 if (config.PIN_PARLANTE & 1) else 0   # canal B = mitad alta de CC
_PWM_BASE = 0x40050000 + 0x14 * _SLICE
_PWM_CSR = _PWM_BASE + 0x00
_PWM_DIV = _PWM_BASE + 0x04
_PWM_CTR = _PWM_BASE + 0x08
_PWM_CC = _PWM_BASE + 0x0C
_PWM_TOP = _PWM_BASE + 0x10
_DREQ_PWM = 24 + _SLICE             # DREQ_PWM_WRAP0..7
_TOP = 255                          # 8 bits de resolución

mem32[_PWM_CSR] = 0                 # detenido (lo enciende el disparo)
mem32[_PWM_DIV] = 1 << 4            # divisor 1.0
mem32[_PWM_TOP] = _TOP
mem32[_PWM_CTR] = 0
mem32[_PWM_CC] = 0
F_PWM = machine.freq() / (_TOP + 1)  # ~488 kHz con el reloj de 125 MHz


def _crear_tabla():
    """
    Chirp lineal senoidal con ventana de Hann, muestreado a F_PWM.
    ciclo = A · w(t) · medio · (1 + sin(2π(f0·t + ½·k·t²)))
    La ventana sube y baja también el nivel medio. Ese nivel medio produce un
    "golpe" de baja frecuencia; al escalarlo con A (AMPLITUD), el golpe baja
    junto con el chirp y no satura el amplificador ni el preamp.
    """
    M = int(F_PWM * config.DURACION_CHIRP_MS / 1000)
    tabla = array.array('I', [0] * (M + 1))
    T = M / F_PWM
    k = (config.F_FIN - config.F_INICIO) / T
    f0 = config.F_INICIO
    escala = config.AMPLITUD * _TOP / 2.0
    dos_pi = 2.0 * math.pi
    for n in range(M):
        t = n / F_PWM
        w = 0.5 - 0.5 * math.cos(dos_pi * n / (M - 1))
        d = w * escala * (1.0 + math.sin(dos_pi * (f0 * t + 0.5 * k * t * t)))
        tabla[n] = int(d + 0.5) << _SHIFT
    tabla[M] = 0                    # termina con el PWM en cero
    return tabla


_tabla = _crear_tabla()

# ─── DMA ──────────────────────────────────────────────────────────────
_EXTRA = 4                          # disparos de sobra: el canal nunca queda ocioso
_buf = array.array('H', [0] * config.N_CAPTURA)
_val_start = array.array('I', [_CS_EN | _AINSEL | _CS_START_ONCE])

_dma_adc = rp2.DMA()        # FIFO del ADC -> _buf           (ritmo: ADC listo)
_dma_start = rp2.DMA()      # START_ONCE -> ADC_CS           (ritmo: reloj slice 0)
_dma_pwm = rp2.DMA()        # _tabla -> CC del PWM del chirp (ritmo: PWM del chirp)

_ctrl_adc = _dma_adc.pack_ctrl(size=1, inc_read=False, inc_write=True,
                               treq_sel=_DREQ_ADC)
_ctrl_start = _dma_start.pack_ctrl(size=2, inc_read=False, inc_write=False,
                                   treq_sel=_DREQ_RELOJ)
_ctrl_pwm = _dma_pwm.pack_ctrl(size=2, inc_read=True, inc_write=False,
                               treq_sel=_DREQ_PWM)


def _vaciar_fifo():
    while (mem32[_ADC_FCS] >> 16) & 0xF:
        mem32[_ADC_FIFO]


def capturar(con_chirp=True):
    """
    Graba N_CAPTURA muestras (y emite el chirp si con_chirp=True).
    Retorna (buffer, FS). Valores de 12 bits (0-4095).
    """
    n = config.N_CAPTURA

    # 1) Todo detenido: PWM apagados y en cero, ADC quieto, FIFO vacía
    mem32[_PWM_EN] = 0
    mem32[_ADC_PWM_BASE + 0x08] = 0
    mem32[_PWM_CTR] = 0
    mem32[_PWM_CC] = 0
    _dma_start.active(0)
    mem32[_ADC_CS] = _CS_EN | _AINSEL
    while not (mem32[_ADC_CS] & _CS_READY):
        pass
    mem32[_ADC_DIV] = 0                 # sin divisor propio: lo marca el slice 0
    mem32[_ADC_FCS] = 0
    _vaciar_fifo()
    mem32[_ADC_FCS] = (_FCS_EN | _FCS_DREQ_EN | _FCS_THRESH_1
                       | _FCS_OVER | _FCS_UNDER)

    # 2) Armar los canales (esperan su DREQ; con los PWM apagados no hay)
    _dma_adc.config(read=_ADC_FIFO, write=_buf, count=n,
                    ctrl=_ctrl_adc, trigger=True)
    _dma_start.config(read=_val_start, write=_ADC_CS, count=n + _EXTRA,
                      ctrl=_ctrl_start, trigger=True)
    en = 1 << _SL_ADC
    if con_chirp:
        _dma_pwm.config(read=_tabla, write=_PWM_CC, count=len(_tabla),
                        ctrl=_ctrl_pwm, trigger=True)
        en |= 1 << _SLICE

    # 3) Arranque simultáneo: una sola escritura enciende los dos PWM
    mem32[_PWM_EN] = en

    # 4) Esperar a que llegue la última muestra y apagar todo
    while _dma_adc.active():
        pass
    mem32[_PWM_EN] = 0
    mem32[_PWM_CC] = 0
    _dma_start.active(0)
    if con_chirp:
        _dma_pwm.active(0)
    mem32[_ADC_CS] = _CS_EN | _AINSEL
    mem32[_ADC_FCS] = 0
    _vaciar_fifo()
    return _buf, FS


def apagar():
    mem32[_PWM_EN] = 0
    mem32[_PWM_CC] = 0


# Una captura de "calentamiento": deja todo en el mismo estado inicial
# que tendrán todas las capturas siguientes.
capturar(True)


if __name__ == "__main__":
    import utime
    utime.sleep_ms(300)
    print("FS exacta: {:.2f} Hz | PWM: {:.0f} Hz | tabla: {} puntos".format(
        FS, F_PWM, len(_tabla)))
    b, fs = capturar(False)
    print("Silencio -> min {} max {} (12 bits)".format(min(b), max(b)))
    b, fs = capturar(True)
    print("Chirp    -> min {} max {} (12 bits)".format(min(b), max(b)))