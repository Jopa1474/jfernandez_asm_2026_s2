from machine import Pin, I2C
import ssd1306
import utime

# Configuración I2C en GP16 (SDA) y GP17 (SCL)
i2c = I2C(0, sda=Pin(16), scl=Pin(17), freq=400000)

# Escaneo de bus I2C para verificar conexión
dispositivos = i2c.scan()
print("Dispositivos I2C encontrados:", [hex(d) for d in dispositivos])

if 0x3c in dispositivos or 0x3d in dispositivos:
    # Inicializar pantalla OLED (128x64)
    oled_addr = dispositivos[0]
    oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=oled_addr)
    
    # Mostrar pantalla de bienvenida
    oled.fill(0)
    oled.text("Radar Acustico", 8, 10)
    oled.text("Estado: OK", 24, 48)
    oled.show()
    print("Pantalla OLED inicializada correctamente.")
else:
    print("No se detectó la pantalla OLED. Revisa las conexiones.")