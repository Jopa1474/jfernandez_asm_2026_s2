import numpy as np
import matplotlib.pyplot as plt
from sim_parte2 import fft  # Importa tu función FFT limpia


# Función para analizar y graficar el espectro de una señal
def analizar_espectro():
    # Parámetros de la señal
    fs = 1000       # Frecuencia de muestreo (1000 Hz)
    N = 256         # Número de puntos (Potencia de 2)
    t = np.arange(N) / fs
    
    # Generar señal compuesta: 50 Hz y 120 Hz con diferente amplitud y fase
    f1, a1 = 50, 1.0
    f2, a2 = 120, 0.5
    signal = a1 * np.sin(2 * np.pi * f1 * t) + a2 * np.cos(2 * np.pi * f2 * t)
    
    # Calcular FFT usando tu función
    X = fft(signal)
    
    # Vector de frecuencias (Dominio de la frecuencia real)
    freqs = np.fft.fftfreq(N, 1/fs)
    
    # Tomar solo la mitad positiva del espectro (Nyquist)
    half_N = N // 2
    freqs_pos = freqs[:half_N]
    
    # Magnitud normalizada
    magnitud = np.abs(X[:half_N]) / N
    magnitud[1:] = 2 * magnitud[1:]  # Conservar energía al tomar solo mitad positiva
    
    # Fase en radianes (filtrando ruido numérico en componentes de magnitud despreciable)
    fase = np.angle(X[:half_N])
    fase[magnitud < 1e-4] = 0.0  # Limpiar fase de componentes casi nulas
    
    # Graficar
    fig, axs = plt.subplots(3, 1, figsize=(10, 8))
    
    # Señal Temporal
    axs[0].plot(t * 1000, signal, color='black')
    axs[0].set_title('Señal en el Dominio del Tiempo $x[t]$', fontsize=11)
    axs[0].set_xlabel('Tiempo (ms)')
    axs[0].set_ylabel('Amplitud')
    axs[0].grid(True, ls='--', alpha=0.6)
    
    # Espectro de Magnitud
    axs[1].stem(freqs_pos, magnitud, linefmt='b-', markerfmt='bo', basefmt='r-')
    axs[1].set_title('Espectro de Magnitud $|X[f]|$', fontsize=11)
    axs[1].set_xlabel('Frecuencia (Hz)')
    axs[1].set_ylabel('Magnitud')
    axs[1].grid(True, ls='--', alpha=0.6)
    
    # Espectro de Fase
    axs[2].stem(freqs_pos, fase, linefmt='g-', markerfmt='go', basefmt='r-')
    axs[2].set_title('Espectro de Fase $\\angle X[f]$', fontsize=11)
    axs[2].set_xlabel('Frecuencia (Hz)')
    axs[2].set_ylabel('Fase (rad)')
    axs[2].grid(True, ls='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig('espectro_magnitud_fase.png', dpi=300)
    print("Gráfica guardada como 'espectro_magnitud_fase.png'")
    plt.show()

if __name__ == "__main__":
    analizar_espectro()