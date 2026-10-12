# MU Online AutoBot V4

Un bot automatizado para servidores de MU Online, construido en Python con una interfaz gráfica amigable (Tkinter).

## 🚀 Características
- **Visión Artificial Ultrarrápida**: Utiliza `mss` y `OpenCV` para escanear colores en pantalla (HSV) en milisegundos.
- **Auto Pickup Personalizable**: Detecta el texto de los items en el suelo y los recoge de forma automática.
- **Auto Buff & Party**: Ejecuta clics izquierdos (skills) y derechos (buff a miembros de la party) con un cooldown configurable.
- **Auto Ataque Inteligente**: Mantiene presionado el clic derecho sobre el color configurado (ej. color de monstruos) y suelta cuando el color desaparece.
- **Editor Visual de Colores**: Interfaz incorporada con paleta de colores para ajustar los tonos HSV sin necesidad de tocar código ni archivos JSON manualmente.
- **Motor Anti-Bloqueo**: Utiliza `pydirectinput` para asegurar la compatibilidad con motores gráficos como DirectX/OpenGL, evitando bloqueos de entrada.

## 🛠️ Instalación (Desde Código Fuente)
1. Instala Python 3.10+
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta el bot:
   ```bash
   python helper_optimizado.py
   ```

## 📦 Ejecutable
El proyecto puede ser compilado a un archivo `.exe` independiente usando PyInstaller:
```bash
pyinstaller --onefile --noconsole helper_optimizado.py
```

## 🎮 Controles Rápidos
- **F5**: Iniciar bot
- **F6**: Detener bot

## ⚠️ Advertencia
Este software fue creado con fines educativos. Asegúrate de revisar las reglas (TOS) de tu servidor antes de utilizar herramientas de automatización.
