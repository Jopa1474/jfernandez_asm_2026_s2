# sampler.py
# Adquisición del micrófono con periodo de muestreo uniforme.
# Guarda las muestras crudas (enteros) y mide la frecuencia de muestreo real.

from machine import Pin, ADC
import array
import utime
import config

import micropython

# Fuente conmutada del Pico W en modo PWM: menos rizado, menos ruido en el ADC
try:
    Pin("WL_GPIO1", Pin.OUT, value=1)
except Exception:
    pass

adc = ADC(Pin(config.PIN_MIC))

# Buffer reservado una sola vez (evita fragmentar la RAM)
_buffer = array.array('H', [0] * config.N_CAPTURA)


@micropython.native
def _capturar(buf, n, periodo, leer, ticks_us, ticks_add, ticks_diff):
    t0 = ticks_us()
    t = t0
    for i in range(n):
        buf[i] = leer()
        t = ticks_add(t, periodo)
        # Espera activa hasta el siguiente instante de muestreo.
        # Como t avanza siempre en pasos fijos, el jitter no se acumula.
        while ticks_diff(t, ticks_us()) > 0:
            pass
    return ticks_diff(ticks_us(), t0)


def capturar():
    """
    Captura N_CAPTURA muestras con periodo PERIODO_US.
    Retorna (buffer_crudo, fs_real). El buffer contiene enteros 0-65535;
    la componente DC se quita después, en el procesamiento.
    """
    n = config.N_CAPTURA
    dt_us = _capturar(_buffer, n, config.PERIODO_US, adc.read_u16,
                      utime.ticks_us, utime.ticks_add, utime.ticks_diff)
    fs_real = n * 1_000_000 / dt_us
    return _buffer, fs_real


if __name__ == "__main__":
    buf, fs = capturar()
    n = config.N_CAPTURA
    media = sum(buf) / n
    print("fs real: {:.1f} Hz (objetivo {:.1f} Hz)".format(fs, 1e6 / config.PERIODO_US))
    print("media: {:.0f} | min: {} | max: {} | p-p: {}".format(
        media, min(buf), max(buf), max(buf) - min(buf)))
    if fs < 0.98e6 / config.PERIODO_US:
        print("Aviso: el loop no alcanza el periodo pedido; sube PERIODO_US en config.py")