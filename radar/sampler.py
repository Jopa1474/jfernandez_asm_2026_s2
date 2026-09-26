from machine import Pin, ADC
import array
import math
import utime

# Configuración del ADC
MIC_PIN = 26
adc = ADC(Pin(MIC_PIN))

# Parámetros de muestreo
N_SAMPLES = 256
FS = 20000  # Frecuencia de muestreo meta (~20 kHz)
DELAY_US = int((1 / FS) * 1_000_000) - 10  # Descuento del tiempo de lectura ADC

# Precalcular la Ventana de Hann para ahorrar CPU durante la captura
HANN_WINDOW = [0.5 * (1 - math.cos(2 * math.pi * i / (N_SAMPLES - 1))) for i in range(N_SAMPLES)]

def capturar_ventana():
    """
    Lee 256 muestras del micrófono con un intervalo constante
    y retorna la señal limpia sin offset DC y ajustada por ventana Hann.
    """
    raw_buffer = array.array('f', (0.0 for _ in range(N_SAMPLES)))
    
    # Captura del buffer de tiempo
    for i in range(N_SAMPLES):
        raw_buffer[i] = float(adc.read_u16())
        utime.sleep_us(DELAY_US)
        
    # Remover Offset DC (promedio)
    mean_val = sum(raw_buffer) / N_SAMPLES
    
    # Aplicar ventana de Hann
    windowed_signal = [(raw_buffer[i] - mean_val) * HANN_WINDOW[i] for i in range(N_SAMPLES)]
    
    return windowed_signal

# Prueba del Muestreador
if __name__ == "__main__":
    print("Probando captura de ventana con filtrado DC + Hann")
    ventana = capturar_ventana()
    print(f"Ventana de {len(ventana)} muestras lista.")
    print("Primeras 5 muestras procesadas:", [round(x, 2) for x in ventana[:5]])