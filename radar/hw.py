# hw.py
# Emisión del chirp y captura del micrófono sincronizadas POR HARDWARE.
#
#  - ADC: muestrea solo, a una frecuencia exacta (reloj de 48 MHz / divisor).
#    Un canal DMA copia cada muestra de la FIFO del ADC a la RAM.
#  - Chirp: una senoidal precalculada. Otro canal DMA escribe el ciclo de
#    trabajo del PWM en cada período del PWM (~488 kHz): el PWM funciona como
#    un DAC y el filtro RC deja la senoidal.
#  - Arranque: dos canales DMA "disparadores" escriben a la vez el START del
#    ADC y el ENABLE del PWM, activados con UNA sola escritura al registro
#    MULTI_CHAN_TRIGGER. El chirp empieza siempre en el mismo instante respecto
#    a la primera muestra: sin delays, sin hilos, sin jitter del intérprete.
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
_DMA_MULTI_TRIG = 0x50000430

_CS_EN = 1
_CS_START_MANY = 1 << 3
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
F_ADC_CLK = 48_000_000
_DIV_INT = int(F_ADC_CLK / config.FS_OBJETIVO + 0.5) - 1
FS = F_ADC_CLK / (_DIV_INT + 1)     # frecuencia de muestreo EXACTA

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
    ciclo = w(t) · (medio + A·sin(2π(f0·t + ½·k·t²)))
    La ventana también sube y baja el nivel medio, así no hay "golpe".
    """
    M = int(F_PWM * config.DURACION_CHIRP_MS / 1000)
    tabla = array.array('I', [0] * (M + 1))
    T = M / F_PWM
    k = (config.F_FIN - config.F_INICIO) / T
    f0 = config.F_INICIO
    medio = _TOP / 2.0
    amp = medio * config.AMPLITUD
    dos_pi = 2.0 * math.pi
    for n in range(M):
        t = n / F_PWM
        w = 0.5 - 0.5 * math.cos(dos_pi * n / (M - 1))
        d = w * (medio + amp * math.sin(dos_pi * (f0 * t + 0.5 * k * t * t)))
        tabla[n] = int(d + 0.5) << _SHIFT
    tabla[M] = 0                    # termina con el PWM en cero
    return tabla


_tabla = _crear_tabla()

# ─── DMA ──────────────────────────────────────────────────────────────
_buf = array.array('H', [0] * config.N_CAPTURA)
_val_start_adc = array.array('I', [_CS_EN | _AINSEL | _CS_START_MANY])
_val_start_pwm = array.array('I', [1])          # CSR: EN

_dma_adc = rp2.DMA()        # FIFO del ADC -> _buf
_dma_pwm = rp2.DMA()        # _tabla -> CC del PWM
_dma_go_adc = rp2.DMA()     # escribe START_MANY en ADC_CS
_dma_go_pwm = rp2.DMA()     # escribe EN en PWM_CSR

_ctrl_adc = _dma_adc.pack_ctrl(size=1, inc_read=False, inc_write=True,
                               treq_sel=_DREQ_ADC)
_ctrl_pwm = _dma_pwm.pack_ctrl(size=2, inc_read=True, inc_write=False,
                               treq_sel=_DREQ_PWM)
_ctrl_go_adc = _dma_go_adc.pack_ctrl(size=2, inc_read=False, inc_write=False)
_ctrl_go_pwm = _dma_go_pwm.pack_ctrl(size=2, inc_read=False, inc_write=False)


def _vaciar_fifo():
    while (mem32[_ADC_FCS] >> 16) & 0xF:
        mem32[_ADC_FIFO]


def capturar(con_chirp=True):
    """
    Graba N_CAPTURA muestras (y emite el chirp si con_chirp=True).
    Retorna (buffer, FS). Valores de 12 bits (0-4095).
    """
    n = config.N_CAPTURA

    # 1) ADC quieto y FIFO vacía
    mem32[_ADC_CS] = _CS_EN | _AINSEL
    while not (mem32[_ADC_CS] & _CS_READY):
        pass
    mem32[_ADC_FCS] = 0
    _vaciar_fifo()
    mem32[_ADC_FCS] = (_FCS_EN | _FCS_DREQ_EN | _FCS_THRESH_1
                       | _FCS_OVER | _FCS_UNDER)
    mem32[_ADC_DIV] = _DIV_INT << 8

    # 2) PWM detenido, contador en cero
    mem32[_PWM_CSR] = 0
    mem32[_PWM_CTR] = 0
    mem32[_PWM_CC] = 0

    # 3) Canales que esperan su DREQ (quedan listos pero sin transferir)
    _dma_adc.config(read=_ADC_FIFO, write=_buf, count=n,
                    ctrl=_ctrl_adc, trigger=True)
    mascara = 0
    _dma_go_adc.config(read=_val_start_adc, write=_ADC_CS, count=1,
                       ctrl=_ctrl_go_adc, trigger=False)
    mascara |= 1 << _dma_go_adc.channel
    if con_chirp:
        _dma_pwm.config(read=_tabla, write=_PWM_CC, count=len(_tabla),
                        ctrl=_ctrl_pwm, trigger=True)
        _dma_go_pwm.config(read=_val_start_pwm, write=_PWM_CSR, count=1,
                           ctrl=_ctrl_go_pwm, trigger=False)
        mascara |= 1 << _dma_go_pwm.channel

    # 4) Disparo simultáneo de ADC y PWM
    mem32[_DMA_MULTI_TRIG] = mascara

    # 5) Esperar a que termine
    if con_chirp:
        while _dma_pwm.active():
            pass
        mem32[_PWM_CSR] = 0
        mem32[_PWM_CC] = 0
    while _dma_adc.active():
        pass
    mem32[_ADC_CS] = _CS_EN | _AINSEL
    mem32[_ADC_FCS] = 0
    _vaciar_fifo()
    return _buf, FS


def apagar():
    mem32[_PWM_CSR] = 0
    mem32[_PWM_CC] = 0


if __name__ == "__main__":
    import utime
    utime.sleep_ms(300)
    print("FS exacta: {:.2f} Hz | PWM: {:.0f} Hz | tabla: {} puntos".format(
        FS, F_PWM, len(_tabla)))
    b, fs = capturar(False)
    print("Silencio -> min {} max {} (12 bits)".format(min(b), max(b)))
    b, fs = capturar(True)
    print("Chirp    -> min {} max {} (12 bits)".format(min(b), max(b)))