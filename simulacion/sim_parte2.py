import numpy as np
import matplotlib.pyplot as plt
import time

"""
Parte 2: Puntos a y b
"""

# Implementación de la DFT
def dft(x):
    #Formula: X[k] = sum_{n=0}^{N-1} x[n] * exp(-j * 2*pi * k * n / N)
    
    N = len(x)
    X = np.zeros(N, dtype=complex)
    
    for k in range(N):
        suma = 0.0 + 0.0j
        for n in range(N):
            angulo = -2.0 * np.pi * k * n / N
            exponencial = np.cos(angulo) + 1j * np.sin(angulo) # e^(-j*theta)
            suma += x[n] * exponencial
        X[k] = suma
        
    return X

# Implementación de la FFT Radix-2 (Cooley-Tukey) 
def fft(x):
   
    N = len(x)
    
    # Caso base de la recursion
    if N <= 1:
        return np.asarray(x, dtype=complex)
    
    # Separar muestras pares e impares
    x_even = x[0::2]
    x_odd  = x[1::2]
    
    # Llamadas recursivas para resolver los dos sub-problemas de tamaño N/2
    X_even = fft(x_even)
    X_odd  = fft(x_odd)
    
    # Combinar los resultados de pares e impares 
    X = np.zeros(N, dtype=complex)
    half_N = N // 2
    
    for k in range(half_N):
        # Factor de giro (Twiddle factor): e^(-j * 2*pi * k / N)
        angulo = -2.0 * np.pi * k / N
        twiddle = np.cos(angulo) + 1j * np.sin(angulo)
        
        # Combinacion de mariposa (Butterfly operation)
        # Primera mitad: X[k] = X_even[k] + twiddle * X_odd[k]
        X[k] = X_even[k] + twiddle * X_odd[k]
        
        # Segunda mitad: X[k + N/2] = X_even[k] - twiddle * X_odd[k]
        X[k + half_N] = X_even[k] - twiddle * X_odd[k]
        
    return X

# Funcion para medir y comparar los tiempos de ejecución de DFT, FFT manual y FFT de NumPy
def benchmark_tiempos():

    # Usamos potencias de 4 a 9 (N de 16 a 512) para que los loops de Python no duren mucho
    potencias = np.arange(4, 10)  
    N_valores = 2 ** potencias
    
    tiempos_dft = []
    tiempos_fft_manual = []
    tiempos_numpy = []
    
    print("Iniciando benchmark con loops explicitos...")
    print("-" * 65)
    
    for N in N_valores:
        # Generar senal senoidal de prueba
        t = np.linspace(0, 1, N, endpoint=False)
        signal = np.sin(2 * np.pi * 5 * t) + 0.5 * np.cos(2 * np.pi * 12 * t)
        
        # Medir DFT manual 
        t0 = time.perf_counter()
        _ = dft(signal)
        t1 = time.perf_counter()
        tiempos_dft.append((t1 - t0) * 1000)  # Convertir a milisegundos
        
        # Medir FFT manual 
        t0 = time.perf_counter()
        _ = fft(signal)
        t1 = time.perf_counter()
        tiempos_fft_manual.append((t1 - t0) * 1000)  # Convertir a milisegundos
        
        # Medir NumPy FFT (Referencia optimizada en C)
        t0 = time.perf_counter()
        _ = np.fft.fft(signal)
        t1 = time.perf_counter()
        tiempos_numpy.append((t1 - t0) * 1000)  # Convertir a milisegundos
        
        print(f"N = {N:4d} | DFT : {tiempos_dft[-1]:8.2f} ms | FFT : {tiempos_fft_manual[-1]:6.2f} ms | NumPy: {tiempos_numpy[-1]:6.4f} ms")

    # Graficar comparativa de tiempos
    plt.figure(figsize=(9, 5))
    plt.plot(N_valores, tiempos_dft, 'o-', label=r'DFT Manual $\mathcal{O}(N^2)$', color='red')
    plt.plot(N_valores, tiempos_fft_manual, 's-', label=r'FFT Manual $\mathcal{O}(N \log_2 N)$', color='blue')
    plt.plot(N_valores, tiempos_numpy, '^--', label='NumPy FFT (C-Optimized)', color='green')
    
    plt.xscale('log', base=2)
    plt.yscale('log')
    plt.xlabel('Tamaño de muestra ($N$)', fontsize=11)
    plt.ylabel('Tiempo de ejecución (ms)', fontsize=11)
    plt.title('Comparativa de Rendimiento: DFT vs FFT', fontsize=12)
    plt.grid(True, which="both", ls="--", alpha=0.6)
    plt.legend(fontsize=10)
    plt.tight_layout()
    
    # Guardamos la imagen 
    plt.savefig('comparacion_tiempos_fft.png', dpi=300)
    print("-" * 65)
    print("Grafica guardada como 'comparacion_tiempos_fft.png'")
    plt.show()

if __name__ == "__main__":
    # Validacion de precision numerica con N = 8
    N = 8
    t = np.linspace(0, 1, N, endpoint=False)
    test_signal = np.sin(2 * np.pi * 2 * t)
    
    dft_res = dft(test_signal)
    fft_res = fft(test_signal)
    numpy_res = np.fft.fft(test_signal)
    
    print(f"Error DFT vs NumPy: {np.max(np.abs(dft_res - numpy_res)):.2e}")
    print(f"Error FFT vs NumPy: {np.max(np.abs(fft_res - numpy_res)):.2e}")
    print("=" * 65)
    
    # Ejecutar la comparativa de tiempos
    benchmark_tiempos()