import machine
import utime
import math
from sampler import capturar_ventana, FS

# Configuración del parlante (PWM en GP15)
PIN_PARLANTE = 15  # Cambia al GPIO donde conectaste la entrada del LM386
pwm_parlante = machine.PWM(machine.Pin(PIN_PARLANTE))

# Constantes físicas
VELOCIDAD_SONIDO_CM_S = 34300.0  # 343 m/s = 34300 cm/s

def emitir_chirp(f_inicio=2000, f_fin=8000, duracion_ms=20):
    """
    Genera un barrido de frecuencia (chirp) por PWM en el parlante.
    """
    pasos = 50
    dt_us = int((duracion_ms * 1000) / pasos)
    
    # Activar ciclo de trabajo (50% onda cuadrada)
    pwm_parlante.duty_u16(32768)
    
    # Barrido lineal de frecuencias
    for i in range(pasos):
        freq = int(f_inicio + (f_fin - f_inicio) * (i / pasos))
        pwm_parlante.freq(freq)
        utime.sleep_us(dt_us)
        
    # Apagar el parlante al terminar
    pwm_parlante.duty_u16(0)

def correlacion_cruzada_manual(signal_recibida, signal_referencia):
    """
    Calcula la correlación cruzada entre la señal recibida y la de referencia.
    Retorna el desfase (lag) que maximiza la coincidencia.
    """
    N = len(signal_recibida)
    M = len(signal_referencia)
    
    max_corr = -1e9
    best_lag = 0
    
    # Buscar el desfase óptimo (dónde encaja mejor el patrón)
    for lag in range(N - M):
        suma = 0.0
        for k in range(M):
            suma += signal_recibida[lag + k] * signal_referencia[k]
        
        if suma > max_corr:
            max_corr = suma
            best_lag = lag
            
    return best_lag, max_corr

def calcular_distancia_tof(f_muestreo=FS):
    """
    Emite el chirp, captura la respuesta acústica y calcula la distancia al objeto.
    """
    # Emitir el chirp por el parlante
    emitir_chirp()
    
    # Capturar inmediatamente la respuesta del micrófono
    muestras = capturar_ventana()
    
    # Generar la referencia local del chirp teórico para comparar
    num_muestras_ref = int(f_muestreo * 0.02)  # 20 ms
    chirp_ref = [
        math.sin(2 * math.pi * (2000 + (6000 * n / num_muestras_ref)) * (n / f_muestreo)) 
        for n in range(num_muestras_ref)
    ]
    
    # Obtener el desfase (retardo en muestras)
    lag_muestras, _ = correlacion_cruzada_manual(muestras, chirp_ref)
    
    # Convertir muestras de retardo a tiempo y distancia
    tiempo_vuelo_seg = lag_muestras / f_muestreo
    distancia_cm = (tiempo_vuelo_seg * VELOCIDAD_SONIDO_CM_S) / 2.0
    
    return distancia_cm, lag_muestras

if __name__ == "__main__":
    print("Probando emisión de Chirp y medición de distancia")
    dist, lag = calcular_distancia_tof()
    print(f"Retardo detectado: {lag} muestras")
    print(f"Distancia calculada: {dist:.2f} cm")