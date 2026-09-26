from machine import ADC, Pin
import utime

# El ADC0 corresponde al GPIO26
mic_adc = ADC(Pin(26))

print("Prueba del Sensor de Sonido (AO)")
print("Emite el chirp o aplaude cerca del micrófono...")

while True:
    muestras = []
    # Capturar un paquete rápido de 100 muestras
    for _ in range(100): 
        muestras.append(mic_adc.read_u16())
        utime.sleep_us(100)  # Muestreo a ~10 kHz
    
    val_max = max(muestras)
    val_min = min(muestras)
    vpp = val_max - val_min  # Voltaje pico a pico aproximado
    
    # Barra en consola para visualizar la intensidad del audio
    nivel = int((vpp / 65535) * 40)
    barra = "█" * nivel
    
    print(f"Vpp: {vpp:5d} | Mín: {val_min:5d} | Máx: {val_max:5d} | {barra}")
    utime.sleep_ms(150)