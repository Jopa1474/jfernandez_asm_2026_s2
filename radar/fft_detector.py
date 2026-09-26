import math
import cmath

def fft_radix2_in_place(x_real, x_imag):
    """
    FFT Radix-2 optimizada para MicroPython (In-Place / Bit-Reversal)
    para evitar saturar la memoria RAM con llamadas recursivas.
    """
    n = len(x_real)
    
    # Reordenamiento por Bit-Reversal
    j = 0
    for i in range(n - 1):
        if i < j:
            x_real[i], x_real[j] = x_real[j], x_real[i]
            x_imag[i], x_imag[j] = x_imag[j], x_imag[i]
        k = n >> 1
        while k <= j:
            j -= k
            k >>= 1
        j += k

    # Mariposas Cooleys-Tukey (Iterativo)
    length = 2
    while length <= n:
        half_len = length // 2
        angle = -2.0 * math.pi / length
        w_step_real = math.cos(angle)
        w_step_imag = math.sin(angle)

        for i in range(0, n, length):
            w_real = 1.0
            w_imag = 0.0
            for k in range(half_len):
                idx1 = i + k
                idx2 = idx1 + half_len

                # Multiplicación compleja
                u_real = x_real[idx2] * w_real - x_imag[idx2] * w_imag
                u_imag = x_real[idx2] * w_imag + x_imag[idx2] * w_real

                x_real[idx2] = x_real[idx1] - u_real
                x_imag[idx2] = x_imag[idx1] - u_imag
                x_real[idx1] += u_real
                x_imag[idx1] += u_imag

                # Actualizar twiddle factor
                nxt_real = w_real * w_step_real - w_imag * w_step_imag
                w_imag = w_real * w_step_imag + w_imag * w_step_real
                w_real = nxt_real

        length <<= 1

def analizar_espectro(signal, fs=20000, f_min=2000, f_max=8000):
    """
    Calcula la magnitud del espectro con FFT y determina si la banda
    del chirp tiene energía predominante.
    """
    N = len(signal)
    x_real = list(signal)
    x_imag = [0.0] * N

    # Ejecutar FFT en tiempo real
    fft_radix2_in_place(x_real, x_imag)

    # Calcular espectro de magnitud (solo primera mitad N/2 por simetría)
    magnitudes = [math.sqrt(x_real[i]**2 + x_imag[i]**2) for i in range(N // 2)]

    # Mapeo de frecuencias a bins
    bin_min = int(f_min / (fs / N))
    bin_max = int(f_max / (fs / N))

    # Energía en la banda del chirp vs Energía Total
    energia_chirp = sum(magnitudes[bin_min:bin_max + 1])
    energia_total = sum(magnitudes) + 1e-6  # evitar div por cero

    ratio = energia_chirp / energia_total

    # Retorna magnitud, el ratio de energía y un flag si sobrepasa el umbral (ej: 40%)
    chirp_detectado = ratio > 0.35

    return magnitudes, ratio, chirp_detectado

# Prueba rápida del detector FFT
if __name__ == "__main__":
    from sampler import capturar_ventana
    
    print("Capturando y analizando espectro con FFT...")
    ventana = capturar_ventana()
    mags, ratio, detectado = analizar_espectro(ventana)
    
    print(f"Ratio de energía en banda (2-8 kHz): {ratio * 100:.1f}%")
    print(f"¿Chirp detectado por FFT?: {'SÍ' if detectado else 'NO'}")