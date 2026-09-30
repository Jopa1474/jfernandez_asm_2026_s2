# main.py
# Radar acústico - Raspberry Pi Pico W (salida por terminal serial)

import gc
import utime
import config
import radar_core

print("=" * 56)
print("  RADAR ACÚSTICO PICO W - MODO CONSOLA")
print("  Chirp {}-{} Hz, {} ms | v = {:.1f} m/s".format(
    config.F_INICIO, config.F_FIN, config.DURACION_CHIRP_MS,
    radar_core.velocidad_sonido()))
print("=" * 56)

fs = radar_core.iniciar()
print("Frecuencia de muestreo real: {:.1f} Hz".format(fs))

if config.USAR_CALIBRACION:
    print("\nCalibración: deja el espacio frente al radar SIN objeto.")
    for s in (3, 2, 1):
        print("  ...{}".format(s))
        utime.sleep(1)
    radar_core.calibrar_fondo()
    print("Fondo registrado. Ya puedes poner el objeto.\n")

try:
    while True:
        try:
            t0 = utime.ticks_ms()
            gc.collect()
            r = radar_core.medir(config.USAR_CALIBRACION)
            t_proc = utime.ticks_diff(utime.ticks_ms(), t0)

            print("-" * 56)
            print("Energía en banda: {:5.1f} % | pico espectral: {:.0f} Hz".format(
                r["ratio_banda"] * 100, r["f_pico"]))

            if r["detectado"] and config.DIST_MIN_CM <= r["distancia_cm"] <= config.DIST_MAX_CM:
                print("ECO DETECTADO")
                print("  Distancia      : {:.1f} cm".format(r["distancia_cm"]))
                print("  Tiempo de vuelo: {:.2f} ms".format(r["tof_ms"]))
                print("  Muestras (eco - directo): {}".format(r["lag_eco"]))
                print("  SNR del eco    : {:.1f}".format(r["snr"]))
            elif "distancia_cm" in r:
                print("Sin eco claro: pico en {:.1f} cm (SNR {:.1f})".format(
                    r["distancia_cm"], r["snr"]))
            else:
                print("Sin eco claro (SNR {:.1f})".format(r.get("snr", 0.0)))
            print("  ({} ms de medición y procesamiento)".format(t_proc))

            if config.GRAFICAR_PERFIL:
                p, largo = radar_core.perfil_actual()
                for j in range(0, largo, 2):
                    print(p[j])

        except Exception as e:
            import sys
            print("Error durante el ciclo:")
            sys.print_exception(e)

        utime.sleep_ms(500)

except KeyboardInterrupt:
    print("\nDetenido.")
finally:
    radar_core.apagar()