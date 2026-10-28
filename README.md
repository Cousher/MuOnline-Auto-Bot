# 🛡️ MU Online AutoBot — Legend V20

Un bot automatizado avanzado para servidores de **MU Online**, construido en Python con interfaz gráfica oscura (Tkinter), visión artificial en tiempo real (`OpenCV` + `mss`), lectura de coordenadas por OCR (`Tesseract`), navegación inteligente por el mapa y control remoto bidireccional completo desde **Telegram**.

---

## 🚀 Características Principales (Legend V20)

### ⚡ 1. Motor de 5 Prioridades en Tiempo Real
Todos los módulos corren en hilos sincronizados bajo una jerarquía estricta para que ninguna acción interfiera con otra ni bloquee el mouse:

| Prioridad | Módulo | Comportamiento Inteligente |
| :---: | :--- | :--- |
| **1°** | **💎 Recolección (Pickup)** | Máxima prioridad. Hace que el ataque suelte el clic derecho en `<= 50ms`, prioriza joyas valiosas por encima del Zen, hace clic izquierdo con *Hover Trick* y calcula el **tiempo de espera dinámico (`0.35s` a `1.45s`)** según la distancia en píxeles desde el PJ hasta la joya. Incluye filtro anti-duplicados (`2.2s`). |
| **2°** | **🧭 Caminar (Coordenadas)** | Pausa el Buff, el Ataque y el Monitor mientras viaja hacia una coordenada `(X, Y)`. Si cae una joya en el camino (**Prioridad 1**), frena un instante, la recoge, actualiza su posición por OCR y continúa hacia el destino. |
| **3°** | **✨ Auto Buff & Party** | Cede ante Recolección y Caminar. Pausa brevemente el Ataque para seleccionar las auras (clic izquierdo) y buffear a los miembros de la Party (clic derecho), liberando el combate inmediatamente durante todo el *Cooldown*. |
| **4°** | **⚔️ Auto Ataque** | Escanea en milisegundos el color de los monstruos y mantiene el clic derecho en tajadas de `50ms`, soltando el botón instantáneamente apenas entra una prioridad superior (P1, P2, P3 o P5). |
| **5°** | **🎒 Foto de Inventario** | Espera en cola hasta que el PJ no esté recogiendo joyas, ni caminando, ni lanzando buffs. Recién entonces pausa el ataque, abre el inventario con clic físico en la UI del juego, envía la captura a Telegram y lo cierra. |

---

### 🧭 2. Lectura OCR de Coordenadas y Navegación Inteligente
- **Separador Geométrico Inteligente (`X | Y`)**: Limpieza automática de bordes y recorte de dígitos con `pytesseract` (`image_to_boxes`) para leer las coordenadas del juego sin errores.
- **Calibrador Visual OCR en Vivo**: Ventana interactiva para ajustar el umbral binario (*Threshold*) e inversión de color viendo en tiempo real qué números detecta el bot.
- **Auto-Calibración de Ejes (`🎯 Calibrar Ejes`)**: Da 2 pasos de prueba automáticos y aprende la orientación isométrica exacta del mapa para transformar cualquier `(ΔX, ΔY)` en la dirección precisa de pantalla.
- **Rodeo de Obstáculos**: Si detecta que la coordenada no cambia tras hacer clic (pared, árbol o esquina), aplica ángulos de desvío progresivos para destrabarse solo.
- **Guardado y Retorno al Spot**: Guarda tu coordenada de leveo y permite volver a ella con un toque desde la interfaz o desde Telegram.

---

### 📱 3. Control Remoto Total por Telegram (Panel de Botones + Comandos)
Incluye un **Teclado Interactivo Persistente** en Telegram y soporte completo de comandos:

| Comando / Botón | Descripción |
| :--- | :--- |
| `📊 Estado` / `/status` | Muestra estado general, tiempo activo, coordenadas actuales, Spot, módulos activos y joyas recogidas. |
| `⚔️ Ataque ON/OFF` / `/atacar` | Activa o desactiva el módulo de Auto Ataque en vivo (sincronizado con la interfaz). |
| `💎 Pickup ON/OFF` / `/pickup` | Activa o desactiva la recolección automática de ítems. |
| `✨ Buff ON/OFF` / `/buff` | Activa o desactiva la ronda automática de auras/party. |
| `/cooldown <seg>` | Cambia el tiempo de espera entre rondas de buffeo (ej. `/cooldown 120`). |
| `/items` o `/item <nombre> on/off` | Lista los ítems configurados o activa/desactiva uno específico (ej. `/item zen off`). |
| `📸 Foto Pantalla` / `/foto` | Toma y envía al instante una captura de la ventana del juego sin interrumpir el ataque. |
| `🎒 Foto Inventario` / `/inventario` | Abre el inventario en el juego (Prioridad 5), envía la foto a Telegram y lo vuelve a cerrar. |
| `/ir <X> <Y>` o `/move <X> <Y>` | Ordena al PJ caminar automáticamente hasta la coordenada indicada (ej. `/ir 142 125`). |
| `📍 Fijar Spot` / `/spot` | Guarda la posición actual del PJ como el nuevo Spot de caza. |
| `🏠 Volver al Spot` / `/volver` | Hace que el PJ regrese caminando a la coordenada guardada del Spot. |
| `⏹ Frenar Caminata` / `/stopmove` | Cancela inmediatamente cualquier movimiento por coordenadas en curso. |
| `⏸ Pausar` / `▶️ Reanudar` | Pausa o reanuda todas las acciones del bot remotamente (`/pausar` / `/reanudar`). |

---

### 🎨 4. Calibrador de Colores HSV, Perfiles y Bypass DirectX
- **Selector Cuentagotas en Pantalla**: Captura el color exacto de cualquier joya o monstruo directamente haciendo clic sobre el juego.
- **Calibrador Visual HSV con Máscara en Vivo**: Permite ver en blanco y negro exactamente qué píxeles está detectando el bot para cada ítem.
- **Gestor de Perfiles (`profiles.json`)**: Guarda y carga configuraciones completas según el mapa o personaje.
- **Bypass DirectX (*Hover Trick*)**: Micro-movimiento previo al clic (`moveTo(x, y)` → `moveTo(x+1, y+1)`) y pulsación realista para máxima compatibilidad con clientes de MU Online.

---

## 🛠️ Instalación (Desde Código Fuente)

1. Instala **Python 3.10+** y [**Tesseract-OCR**](https://github.com/UB-Mannheim/tesseract/wiki) (en `C:\Program Files\Tesseract-OCR\tesseract.exe`).
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta el bot (como **Administrador** para que el juego reciba los clics de `pydirectinput`):
   ```bash
   python helper_optimizado.py
   ```

## 📦 Compilación a Ejecutable (`.exe`)
El proyecto se puede compilar a un archivo `.exe` independiente usando PyInstaller:
```bash
pyinstaller --onefile --noconsole --name helper_v20 helper_optimizado.py
```

## 🎮 Atajos Rápidos en el Juego
- **`F5`**: Iniciar bot
- **`F6`**: Detener bot

## ⚠️ Advertencia
Este software fue creado con fines educativos. Asegúrate de revisar las reglas (TOS) de tu servidor antes de utilizar herramientas de automatización.
