# ⚔️ Crixus Mu Online Bot — Legend V21

Un bot automatizado avanzado para servidores de **MU Online**, construido en Python con interfaz gráfica oscura (Tkinter), visión artificial en tiempo real (`OpenCV` + `mss`), lectura de coordenadas por OCR (`Tesseract`), navegación inteligente por el mapa, guía interactiva integrada y control remoto bidireccional completo (con soporte **Multi-VPS**) desde **Telegram**.

---

## 🚀 Características Principales (Legend V21)

### ⚡ 1. Motor de 5 Prioridades en Tiempo Real y Control Seguro de Entrada
Todos los módulos corren en hilos sincronizados bajo una jerarquía estricta con exclusión mutua (`input_lock`) y liberación garantizada de botones (`held_mouse_button`) para que ninguna acción interfiera con otra ni deje clics bloqueados:

| Prioridad | Módulo | Comportamiento Inteligente |
| :---: | :--- | :--- |
| **1°** | **💎 Recolección (Pickup)** | Máxima prioridad. Hace que el ataque suelte el clic derecho en `<= 50ms`, prioriza joyas valiosas por encima del Zen, hace clic izquierdo con *Hover Trick* y calcula el **tiempo de espera dinámico (`0.35s` a `1.45s`)** según la distancia en píxeles desde el PJ hasta la joya. Incluye filtro anti-duplicados (`2.2s`). |
| **2°** | **🧭 Caminar (Coordenadas)** | Pausa el Buff, el Ataque y el Monitor mientras viaja hacia una coordenada `(X, Y)`. Si cae una joya en el camino (**Prioridad 1**), frena un instante, la recoge, actualiza su posición por OCR y continúa hacia el destino. Respeta `/pausa` y conserva tu Spot fijado. |
| **3°** | **✨ Auto Buff & Party** | Cede ante Recolección y Caminar. Pausa brevemente el Ataque para seleccionar las auras (clic izquierdo) y buffear a los miembros de la Party (clic derecho), liberando el combate inmediatamente durante todo el *Cooldown*. |
| **4°** | **⚔️ Auto Ataque** | Escanea en milisegundos el color de los monstruos, selecciona el objetivo **más cercano al centro del PJ** y mantiene el clic derecho en tajadas de `50ms`, soltando el botón instantáneamente apenas entra una prioridad superior (P1, P2, P3 o P5). |
| **5°** | **🎒 Foto de Inventario** | Espera en cola hasta que el PJ no esté recogiendo joyas, ni caminando, ni lanzando buffs, ni en pausa. Recién entonces pausa el ataque, abre el inventario con clic físico en la UI del juego, envía la captura a Telegram y lo cierra. |

---

### 🧭 2. Lectura OCR de Coordenadas y Navegación Inteligente
- **Separador Geométrico Inteligente (`X | Y`)**: Limpieza automática de bordes y recorte de dígitos con `pytesseract` (`image_to_boxes`) para leer las coordenadas del juego sin errores.
- **Filtro Estabilizador de Lecturas (`read_stable_coords`)**: Descarta saltos imposibles entre frames para evitar falsos positivos del OCR.
- **Calibrador Visual OCR en Vivo**: Ventana interactiva para ajustar el umbral binario (*Threshold*) e inversión de color viendo en tiempo real qué números detecta el bot.
- **Auto-Calibración de Ejes (`🎯 Calibrar Ejes`)**: Da 2 pasos de prueba automáticos y aprende la orientación isométrica exacta del mapa para transformar cualquier `(ΔX, ΔY)` en la dirección precisa de pantalla.
- **Rodeo de Obstáculos**: Si detecta que la coordenada no cambia tras hacer clic (pared, árbol o esquina), aplica ángulos de desvío progresivos para destrabarse solo.
- **Guardado y Retorno al Spot**: Guarda tu coordenada de caza (`📌 Fijar Spot`) y permite regresar a ella en cualquier momento (`🏠 Volver al Spot`) sin que un viaje temporal con `/ir X Y` sobrescriba tu Spot.

---

### 📱 3. Control Remoto por Telegram y Soporte Multi-VPS
Incluye un **Teclado Interactivo Persistente**, identificador de cliente/VPS (`🏷️ [VPS 1 - BK]`) en cada mensaje/foto y soporte completo de comandos:

#### 🖥️ Cómo usar 2 o más VPS al mismo tiempo:
1. En `@BotFather` crea **1 Bot para cada VPS** (`/newbot` → `Token 1` para el VPS 1, `Token 2` para el VPS 2) para evitar conflictos de lectura `getUpdates`.
2. En todos los VPS coloca **tu mismo `Chat ID` personal** (`@userinfobot`).
3. En la ventana `📱 Telegram` (o con el comando `/vps <nombre>`) asigna un alias a cada uno (ej. `VPS 1 - BK` y `VPS 2 - Elf`). Todas las notificaciones, reportes y fotos incluirán la etiqueta **`🏷️ [VPS 1 - BK]`** arriba y también se mostrará en el título de la ventana del bot.

| Comando / Botón | Descripción |
| :--- | :--- |
| `📊 Estado` / `/estado` (o `/status`) | Muestra estado general, tiempo activo, coordenadas actuales, Spot, módulos activos y joyas recogidas. |
| `/vps <nombre>` o `/nombre <alias>` | Asigna o cambia remotamente el identificador de este VPS/Personaje (ej. `/vps VPS 1 - BK`). |
| `⚔️ Ataque` / `/atacar [on\|off]` | Activa o desactiva el módulo de Auto Ataque en vivo (sincronizado con la interfaz). |
| `💎 Pickup` / `/pickup [on\|off]` | Activa o desactiva la recolección automática de ítems. |
| `✨ Buffs` / `/buff [on\|off]` | Activa o desactiva la ronda automática de auras/party. |
| `/cooldown <seg>` | Cambia el tiempo de espera entre rondas de buffeo (mínimo `5` segundos, ej. `/cooldown 120`). |
| `/items` o `/item <nombre> [on\|off]` | Lista los ítems configurados o activa/desactiva uno específico (ej. `/item zen off`). |
| `📸 Foto Pantalla` / `/foto` | Toma y envía al instante una captura de la ventana del juego sin interrumpir el ataque. |
| `🎒 Foto Inventario` / `/inventario` | Abre el inventario en el juego (Prioridad 5), envía la foto a Telegram y lo vuelve a cerrar. |
| `/ir <X> <Y>` o `/move <X> <Y>` | Ordena al PJ caminar automáticamente hasta la coordenada indicada (ej. `/ir 142 125`). |
| `📌 Fijar Spot` / `/fijarspot` | Guarda la posición actual del PJ como el nuevo Spot de caza. |
| `🏠 Volver al Spot` / `/volver` (o `/spot`) | Hace que el PJ regrese caminando a la coordenada guardada del Spot. |
| `/cancelar` o `/stopmove` | Cancela inmediatamente cualquier movimiento por coordenadas en curso. |
| `/pausa` / `/reanudar` | Pausa o reanuda todas las acciones del bot remotamente (incluyendo caminata, ataque, pickup y buffs). |

---

### 🎨 4. Forja de Colores HSV, Guía Interactiva Integrada y Compatibilidad DirectX
- **Manual Interactivo Integrado (`📖 Guía de Uso`)**: Ventana de ayuda por pestañas dentro de la aplicación (`HelpGuideWindow`) con instrucciones detalladas de calibración, prioridades, Multi-VPS y comandos.
- **Forja de Colores HSV (`ColorEditor`)**: Editor integrado con selector visual de color, vista previa en vivo y validación estricta de rangos (`H: 0..179`, `S/V: 0..255`).
- **Persistencia Atómica (`config.json`)**: Guardado protegido con `threading.Lock` y archivo temporal (`os.replace`) para evitar corrupción de datos.
- **Bypass DirectX (*Hover Trick*)**: Micro-movimiento previo al clic (`moveTo(x, y)` → `moveTo(x+1, y+1)`) y pulsación protegida con `try/finally` para máxima compatibilidad con clientes de MU Online.

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
pyinstaller --onefile --noconsole --name Crixus_Mu_Bot_v21 helper_optimizado.py
```

## 🎮 Atajos Rápidos en el Juego
- **`F5`**: Iniciar bot
- **`F6`**: Detener bot

## ⚠️ Advertencia
Este software fue creado con fines educativos. Asegúrate de revisar las reglas (TOS) de tu servidor antes de utilizar herramientas de automatización.
