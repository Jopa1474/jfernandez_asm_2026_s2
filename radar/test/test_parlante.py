from machine import Pin, PWM
import utime

PIN_PARLANTE = 15

# Inicializar el pin como PWM
parlante = PWM(Pin(PIN_PARLANTE))

print("=== Prueba de salida PWM en GP15 ===")
print("Generando tono de 1 kHz...")

# Configurar frecuencia a 1000 Hz
parlante.freq(1000)

# Activar PWM al 50% de ciclo de trabajo (32768 / 65535)
parlante.duty_u16(32768)

utime.sleep(3)

# Apagar PWM
parlante.duty_u16(0)
parlante.deinit()

print("Prueba finalizada.")