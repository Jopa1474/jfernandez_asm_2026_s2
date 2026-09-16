import numpy as np
import matplotlib.pyplot as plt

# Función para generar un chirp lineal que detecta el eco de un objeto a cierta distancia
def generar_chirp(f0, f1, T, fs):

    t = np.linspace(0, T, int(fs * T), endpoint=False) # Tiempo de muestreo

    # Frecuencia instantanea lineal: f(t) = f0 + (f1 - f0) * t / (2 * T)
    chirp = np.sin(2 * np.pi * (f0 + (f1 - f0) * t / (2 * T)) * t)
    return t, chirp

# Función principal para simular un radar acústico usando un chirp y correlación cruzada
def simular_radar_acustico():

    # Parámetros del radar
    fs = 44100              # Frecuencia de muestreo de audio (44.1 kHz)
    f_inicio = 2000         # Frecuencia inicial del chirp (2 kHz)
    f_fin = 6000            # Frecuencia final del chirp (6 kHz)
    duracion_chirp = 0.010  # Duración del disparo: 10 ms
    v_sonido = 343.0        # Velocidad del sonido en el aire (m/s)
    
    # Distancia simulada del objeto (ejemplo: 1.5 metros)
    distancia_real = 1.5    # metros
    
    # Tiempo de vuelo real (ToF = 2 * d / v)
    tof_real = (2 * distancia_real) / v_sonido
    print(f"Distancia simulada: {distancia_real} m")
    print(f"Tiempo de vuelo real esperado (ToF): {tof_real * 1000:.3f} ms")
    
    # Generaramos la señal emitida (Chirp)
    t_chirp, emitido = generar_chirp(f_inicio, f_fin, duracion_chirp, fs)
    
    # Creamos buffer de señal recibida (0.025 segundos de escucha)
    duracion_escucha = 0.025
    t_recibido = np.linspace(0, duracion_escucha, int(fs * duracion_escucha), endpoint=False) # Tiempo de escucha
    recibido = np.zeros_like(t_recibido) # Buffer de señal recibida (inicialmente vacío)
    
    # Insertar el eco retrasado (ToF) con atenuación
    muestra_retraso = int(tof_real * fs)
    num_muestras_chirp = len(emitido)

    # Asegurarse de que el eco no exceda la longitud del buffer de escucha
    if muestra_retraso + num_muestras_chirp < len(recibido):
        recibido[muestra_retraso : muestra_retraso + num_muestras_chirp] += 0.4 * emitido
        
    # Agregar ruido ambiental blanco a la señal recibida
    ruido = np.random.normal(0, 0.2, size=len(recibido))
    recibido_con_ruido = recibido + ruido
    
    # Correlación Cruzada en la Frecuencia (Usando FFT)
    # Para la correlación en frecuencia: R_xy = IFFT( FFT(recibido) * conj(FFT(emitido)) )
    N_fft = len(recibido_con_ruido) + len(emitido) - 1
    
    X_recibido = np.fft.fft(recibido_con_ruido, n=N_fft)
    X_emitido  = np.fft.fft(emitido, n=N_fft)
    
    # Producto con el conjugado complejo
    correlacion_espectral = np.fft.ifft(X_recibido * np.conj(X_emitido))
    correlacion_magnitud = np.abs(correlacion_espectral)
    
    # Estimación del tiempo y distancia
    indice_pico = np.argmax(correlacion_magnitud)
    tof_estimado = indice_pico / fs
    distancia_estimada = (tof_estimado * v_sonido) / 2
    
    print("-" * 50)
    print(f"ToF Estimado por el pico: {tof_estimado * 1000:.3f} ms")
    print(f"Distancia Calculada: {distancia_estimada:.3f} m")
    print(f"Error absoluto: {abs(distancia_estimada - distancia_real) * 100:.2f} cm")
    
    # Graficar resultados 
    fig, axs = plt.subplots(3, 1, figsize=(10, 8))
    
    # Gráfica 1: Chirp Emitido
    axs[0].plot(t_chirp * 1000, emitido, color='blue')
    axs[0].set_title('Señal Transmitida: Chirp (2 kHz a 6 kHz)', fontsize=11)
    axs[0].set_xlabel('Tiempo (ms)')
    axs[0].set_ylabel('Amplitud')
    axs[0].grid(True, ls='--', alpha=0.6)
    
    # Gráfica 2: Señal Recibida en el Micrófono con Ruido
    axs[1].plot(t_recibido * 1000, recibido_con_ruido, color='gray', alpha=0.7, label='Ruido + Eco')
    axs[1].plot(t_recibido * 1000, recibido, color='red', linestyle='--', label='Eco Limpio')
    axs[1].set_title('Señal Capturada por el Micrófono (Eco con Ruido)', fontsize=11)
    axs[1].set_xlabel('Tiempo (ms)')
    axs[1].set_ylabel('Amplitud')
    axs[1].legend(loc='upper right')
    axs[1].grid(True, ls='--', alpha=0.6)
    
    # Gráfica 3: Pico de Correlación Cruzada (Identificación del ToF)
    eje_tiempo_corr = np.arange(N_fft) / fs
    axs[2].plot(eje_tiempo_corr * 1000, correlacion_magnitud, color='green')
    axs[2].axvline(x=tof_estimado * 1000, color='red', linestyle=':', label=f'Pico ToF ({tof_estimado*1000:.2f} ms)')
    axs[2].set_title('Resultado de la Correlación Cruzada (Identificación del Eco)', fontsize=11)
    axs[2].set_xlabel('Tiempo de Retardo (ms)')
    axs[2].set_ylabel('Magnitud de Correlación')
    axs[2].set_xlim(0, duracion_escucha * 1000)
    axs[2].legend(loc='upper right')
    axs[2].grid(True, ls='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig('simulacion_radar_chirp.png', dpi=300)
    print("\nGráfica guardada como 'simulacion_radar_chirp.png'")
    plt.show()

if __name__ == "__main__":
    simular_radar_acustico()