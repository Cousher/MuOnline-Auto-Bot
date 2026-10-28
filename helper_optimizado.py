import tkinter as tk
from tkinter import messagebox, colorchooser, simpledialog
import threading, time, json, os, sys, re, shutil, math
import cv2
import numpy as np
import pydirectinput
import keyboard
import mss
import requests
import pytesseract

# --- CONFIGURACIÓN AUTOMÁTICA DE TESSERACT OCR ---
def setup_tesseract():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    candidates = [
        os.path.join(base_path, "Tesseract-OCR", "tesseract.exe"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tesseract-OCR", "tesseract.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
        shutil.which("tesseract")
    ]
    for path in candidates:
        if path and os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return path
    return None

TESSERACT_PATH = setup_tesseract()

# --- PALETA MU ONLINE ---
MU_BG = "#0A0A0A"          
MU_FRAME_BG = "#151515"    
MU_FG = "#E6CC80"          
MU_BTN_BG = "#4A0000"      
MU_BTN_FG = "#FFEA8C"      
MU_FONT = ("Helvetica", 10, "bold")
MU_TITLE_FONT = ("Georgia", 14, "bold") 
MU_LIST_BG = "#222222"
MU_ACCENT = "#2b0000"

# ----- Estadísticas de Farmeo -----
stats = {
    "start_time": None,
    "items": {},
    "current_coords": None,
    "spot_coords": None,
    "target_coords": None
}

# ----- Configuración y Guardado -----
class Config:
    def __init__(self):
        self.config_file = 'config.json'
        self.data = {
            "buff_enabled": True,
            "buff_skills": [],
            "buff_players": [],
            "cooldown": 15,
            "pickup_enabled": False,
            "pickup_area": None,
            "pickup_colors": {
                "zen": {"lower": [20, 100, 100], "upper": [40, 255, 255], "active": True, "notify": False},
                "firecracker": {"lower": [2, 160, 180], "upper": [22, 255, 255], "active": True, "notify": True},
                "heart_of_love": {"lower": [0, 150, 170], "upper": [10, 255, 255], "active": True, "notify": True},
                "medalla": {"lower": [20, 130, 170], "upper": [40, 230, 255], "active": True, "notify": True},
                "soul": {"lower": [140, 150, 160], "upper": [160, 255, 255], "active": True, "notify": True}
            },
            "attack_enabled": False,
            "attack_area": None,
            "attack_color": {
                "lower": [0, 200, 200], 
                "upper": [10, 255, 255]
            },
            "telegram": {
                "enabled": False,
                "token": "",
                "chat_id": ""
            },
            "monitor": {
                "enabled": False,
                "interval_minutes": 30,
                "button_area": None,
                "area": None
            },
            "coords": {
                "enabled": False,
                "area": None,
                "threshold": 150,
                "invert": True,
                "char_center": None,
                "calibration": None,
                "tolerance": 1
            }
        }
        self.load()
        
        if "pickup_colors" in self.data:
            for key, value in self.data["pickup_colors"].items():
                if "active" not in value: self.data["pickup_colors"][key]["active"] = True
                if "notify" not in value: self.data["pickup_colors"][key]["notify"] = (key != "zen")
                    
        if "attack_enabled" not in self.data: self.data["attack_enabled"] = False
        if "attack_area" not in self.data: self.data["attack_area"] = None
        if "attack_color" not in self.data: self.data["attack_color"] = {"lower": [0, 200, 200], "upper": [10, 255, 255]}
        if "telegram" not in self.data: self.data["telegram"] = {"enabled": False, "token": "", "chat_id": ""}
        if "monitor" not in self.data: self.data["monitor"] = {"enabled": False, "interval_minutes": 30, "button_area": None, "area": None}
        if "coords" not in self.data:
            self.data["coords"] = {"enabled": False, "area": None, "threshold": 150, "invert": True, "char_center": None, "calibration": None, "tolerance": 1}
        if "threshold" not in self.data["coords"]: self.data["coords"]["threshold"] = 150
        if "invert" not in self.data["coords"]: self.data["coords"]["invert"] = True
        if "char_center" not in self.data["coords"]: self.data["coords"]["char_center"] = None
        if "calibration" not in self.data["coords"]: self.data["coords"]["calibration"] = None
        if "tolerance" not in self.data["coords"]: self.data["coords"]["tolerance"] = 1
        
        # Limpiar key vieja si existe
        if "key" in self.data["monitor"]:
            del self.data["monitor"]["key"]

    def load(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                loaded_data = json.load(f)
                self.data.update(loaded_data)

    def save(self):
        with open(self.config_file, "w") as f:
            json.dump(self.data, f, indent=4)

config = Config()

# ----- Teclado Interactivo de Telegram -----
def get_telegram_keyboard():
    atk_icon = "🟢" if config.data.get("attack_enabled", False) else "🔴"
    pck_icon = "🟢" if config.data.get("pickup_enabled", False) else "🔴"
    buf_icon = "🟢" if config.data.get("buff_enabled", False) else "🔴"
    return {
        "keyboard": [
            [{"text": "▶ Iniciar Bot"}, {"text": "⏹ Detener Bot"}, {"text": "📊 Estado"}],
            [{"text": f"⚔️ Ataque {atk_icon}"}, {"text": f"💎 Pickup {pck_icon}"}, {"text": f"✨ Buffs {buf_icon}"}],
            [{"text": "📸 Foto Pantalla"}, {"text": "🎒 Foto Inventario"}, {"text": "📍 Posición"}],
            [{"text": "🏠 Volver al Spot"}, {"text": "📌 Fijar Spot"}, {"text": "❓ Ayuda"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

# ----- Funciones Telegram -----
def send_telegram_async(msg, with_keyboard=False):
    token = config.data["telegram"]["token"]
    chat_id = config.data["telegram"]["chat_id"]
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": msg}
        if with_keyboard:
            payload["reply_markup"] = json.dumps(get_telegram_keyboard())
        try:
            requests.post(url, data=payload, timeout=5)
        except:
            pass

def send_telegram(msg, with_keyboard=False):
    threading.Thread(target=send_telegram_async, args=(msg, with_keyboard), daemon=True).start()

def send_telegram_photo_async(photo_path, caption="📸 Estado del Inventario."):
    token = config.data["telegram"]["token"]
    chat_id = config.data["telegram"]["chat_id"]
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            with open(photo_path, "rb") as f:
                requests.post(url, data={"chat_id": chat_id, "caption": caption}, files={"photo": f}, timeout=15)
        except:
            pass
        finally:
            try: os.remove(photo_path)
            except: pass

# ----- Configuración de Telegram (UI) -----
class TelegramConfig(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📱 Notificaciones y Control Telegram")
        self.geometry("460x400")
        self.configure(bg=MU_BG)
        self.grab_set()

        tk.Label(self, text="CONFIGURACIÓN DE TELEGRAM", font=MU_TITLE_FONT, bg=MU_BG, fg=MU_FG).pack(pady=10)
        
        info = (
            "1. Busca a @BotFather en Telegram y crea un bot.\n"
            "2. Copia el Token aquí.\n"
            "3. Busca a @userinfobot para obtener tu Chat ID.\n"
            "4. Escribe /menu o /ayuda en Telegram para abrir el panel de botones."
        )
        tk.Label(self, text=info, bg=MU_BG, fg="#AAAAAA", justify=tk.LEFT).pack(pady=5)

        self.enabled_var = tk.BooleanVar(value=config.data["telegram"]["enabled"])
        tk.Checkbutton(self, text="Activar Notificaciones y Control por Telegram", variable=self.enabled_var, bg=MU_BG, fg=MU_FG, selectcolor=MU_ACCENT).pack(pady=5)

        tk.Label(self, text="Bot Token:", bg=MU_BG, fg=MU_FG).pack(anchor="w", padx=20)
        self.token_entry = tk.Entry(self, width=50, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG)
        self.token_entry.pack(padx=20, pady=2)
        self.token_entry.insert(0, config.data["telegram"]["token"])

        tk.Label(self, text="Tu Chat ID:", bg=MU_BG, fg=MU_FG).pack(anchor="w", padx=20)
        self.chatid_entry = tk.Entry(self, width=30, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG)
        self.chatid_entry.pack(padx=20, pady=2, anchor="w")
        self.chatid_entry.insert(0, config.data["telegram"]["chat_id"])

        btn_frame = tk.Frame(self, bg=MU_BG)
        btn_frame.pack(pady=20)
        
        create_mu_button(btn_frame, "Probar y Enviar Menú", self.test_message, bg="#006400").pack(side=tk.LEFT, padx=10)
        create_mu_button(btn_frame, "Guardar", self.save_config).pack(side=tk.LEFT, padx=10)

    def test_message(self):
        token = self.token_entry.get().strip()
        chat_id = self.chatid_entry.get().strip()
        if not token or not chat_id:
            messagebox.showwarning("Faltan datos", "Completa el Token y el Chat ID.")
            return
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            payload = {
                "chat_id": chat_id,
                "text": "¡Hola! 🤖 Panel de control remoto de MU Online activado.\nUsa los botones de abajo o escribe /ayuda para ver todos los comandos.",
                "reply_markup": json.dumps(get_telegram_keyboard())
            }
            res = requests.post(url, data=payload)
            if res.status_code == 200:
                messagebox.showinfo("Éxito", "Mensaje y teclado de control enviados. Revisa tu Telegram.")
            else:
                messagebox.showerror("Error", f"Fallo al enviar: {res.text}")
        except Exception as e:
            messagebox.showerror("Error", f"Error de conexión: {str(e)}")

    def save_config(self):
        config.data["telegram"]["enabled"] = self.enabled_var.get()
        config.data["telegram"]["token"] = self.token_entry.get().strip()
        config.data["telegram"]["chat_id"] = self.chatid_entry.get().strip()
        config.save()
        messagebox.showinfo("Guardado", "Configuración de Telegram guardada.")
        self.destroy()

# ----- Variables Globales de Control y Sistema de 5 Prioridades -----
# Jerarquía de Prioridades:
#   1° Recolección (pickup_active)
#   2° Caminar     (moving_to_coords)
#   3° Buff        (buff_active)
#   4° Ataque      (cede ante 1, 2, 3 y 5)
#   5° Foto Inv.   (photo_active: espera a que 1, 2 y 3 estén libres, y pausa 4 mientras saca la foto)
running = False
manual_pause = False     # Pausa manual solicitada desde Telegram (/pausa)
pickup_active = False    # Prioridad 1: Hay joyas en el suelo y el PJ las está levantando
moving_to_coords = False # Prioridad 2: El PJ está caminando hacia una coordenada
buff_active = False      # Prioridad 3: El PJ está lanzando la ronda de auras/buffs
photo_active = False     # Prioridad 5: Abriendo inventario para tomar captura
bot_paused = False       # Compatibilidad general
move_lock = threading.Lock()
app_instance = None      # Referencia a la ventana principal para sincronizar UI

def sync_ui_from_config():
    """Sincroniza los checkboxes y botones de la interfaz gráfica cuando se hacen cambios desde Telegram."""
    global app_instance
    if app_instance is not None:
        try:
            app_instance.after(0, app_instance.refresh_ui_from_config)
        except Exception:
            pass

# ----- Utilidades de Posición del PJ en Pantalla -----
def get_character_screen_center():
    """Obtiene el punto central (x, y) donde está parado el PJ en la pantalla."""
    char_area = config.data["coords"].get("char_center")
    if char_area:
        return (char_area["x1"] + char_area["x2"]) // 2, (char_area["y1"] + char_area["y2"]) // 2

    for key in ("attack_area", "pickup_area"):
        area = config.data.get(key)
        if area:
            return (area["x1"] + area["x2"]) // 2, (area["y1"] + area["y2"]) // 2

    mon_area = config.data["monitor"].get("area")
    if mon_area:
        return (mon_area["x1"] + mon_area["x2"]) // 2, (mon_area["y1"] + mon_area["y2"]) // 2 - 30

    return 400, 295

def get_playable_bounds():
    """Devuelve los límites seguros donde hacer click para caminar sin tocar el HUD."""
    for key in ("attack_area", "pickup_area"):
        area = config.data.get(key)
        if area:
            return area["x1"] + 25, area["y1"] + 25, area["x2"] - 25, area["y2"] - 25
    cx, cy = get_character_screen_center()
    return max(20, cx - 260), max(30, cy - 200), cx + 260, cy + 190

# ----- Funciones en Hilos (Lógica del Bot con 5 Prioridades) -----

# PRIORIDAD 1: RECOLECCIÓN (PICKUP)
def pickup_process(log_widget):
    global running, config, stats, pickup_active, manual_pause, photo_active
    last_counted_time = {}  # Evita contar o notificar doble si una joya lejana requiere 2 clicks mientras camina
    with mss.mss() as sct:
        while running:
            if manual_pause or photo_active:
                pickup_active = False
                time.sleep(0.3)
                continue
            if not config.data.get("pickup_area") or not config.data.get("pickup_enabled", False):
                pickup_active = False
                time.sleep(0.6)
                continue

            area = config.data["pickup_area"]
            monitor = {"top": area["y1"], "left": area["x1"], "width": area["x2"] - area["x1"], "height": area["y2"] - area["y1"]}
            img = np.array(sct.grab(monitor))
            bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            clicks_to_make = []
            char_x, char_y = get_character_screen_center()
            
            for obj_name, obj_conf in list(config.data["pickup_colors"].items()):
                if not obj_conf.get("active", True): continue
                lower = np.array(obj_conf["lower"], dtype=np.uint8)
                upper = np.array(obj_conf["upper"], dtype=np.uint8)
                mask = cv2.inRange(hsv, lower, upper)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    if cv2.contourArea(cnt) < 5: continue
                    x, y, w, h = cv2.boundingRect(cnt)
                    center_x = area["x1"] + x + w // 2
                    center_y = area["y1"] + y + h // 2
                    px_dist = math.hypot(center_x - char_x, center_y - char_y)
                    # Priorizamos joyas importantes (notify=True o != zen) por encima del zen, y luego las más cercanas al PJ
                    is_zen = (obj_name == "zen")
                    clicks_to_make.append((is_zen, px_dist, center_x, center_y, obj_name))

            if clicks_to_make:
                # Ordenar: primero joyas valiosas (is_zen=False), luego por cercanía al PJ
                clicks_to_make.sort(key=lambda item: (item[0], item[1]))

                if not pickup_active:
                    pickup_active = True
                    # Dar 70ms para que Ataque suelte el click derecho antes de hacer click izquierdo en la joya
                    time.sleep(0.07)

                for _, px_dist, cx, cy, item in clicks_to_make:
                    if not running or manual_pause or photo_active or not config.data.get("pickup_enabled", False):
                        break

                    # Click con micro-movimiento (hover trick) para asegurar que MU registre el click sobre el ítem
                    pydirectinput.moveTo(cx, cy)
                    time.sleep(0.04)
                    pydirectinput.moveTo(cx + 1, cy + 1)
                    time.sleep(0.04)
                    pydirectinput.mouseDown(button='left')
                    time.sleep(0.08)
                    pydirectinput.mouseUp(button='left')

                    # Tiempo de espera dinámico según qué tan lejos cayó la joya del PJ
                    if px_dist <= 70:
                        walk_wait = 0.35
                    elif px_dist <= 160:
                        walk_wait = 0.75
                    else:
                        walk_wait = min(1.45, 0.75 + (px_dist - 160) / 180.0)

                    log_message(f"Pickup [P1]: Recogiendo {item} (dist: {int(px_dist)}px, espera: {walk_wait:.2f}s)", log_widget)

                    now = time.time()
                    # Si la joya estaba lejos y toma más de 1 click llegar, solo sumamos a la estadística 1 vez cada 2.2s
                    if now - last_counted_time.get(item, 0) >= 2.2:
                        last_counted_time[item] = now
                        if item not in stats["items"]: stats["items"][item] = 0
                        stats["items"][item] += 1
                        
                        if config.data["telegram"]["enabled"] and config.data["pickup_colors"][item].get("notify", False):
                            elapsed = int(now - stats["start_time"]) if stats["start_time"] else 0
                            hrs, rem = divmod(elapsed, 3600)
                            mins, secs = divmod(rem, 60)
                            time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
                            items_str = "\n".join([f"🔹 {k.capitalize()}: {v}" for k, v in stats["items"].items()])
                            msg = f"💎 ¡Nuevo ítem recogido: {item.capitalize()}!\n\n📊 REPORTE DE FARMEO:\n⏳ Tiempo: {time_str}\n{items_str}"
                            send_telegram(msg)

                    # Esperar mientras el PJ camina hacia la joya (manteniendo pickup_active=True para que nadie le quite el mouse)
                    steps_sleep = max(1, int(walk_wait / 0.05))
                    for _ in range(steps_sleep):
                        if not running or manual_pause:
                            break
                        time.sleep(0.05)
                    # Si la joya estaba lejos, re-evaluamos la pantalla tras este click para ver si ya la levantó
                    if px_dist > 90:
                        break
            else:
                if pickup_active:
                    pickup_active = False
                time.sleep(0.1)

# PRIORIDAD 3: BUFFEO (AURAS & PARTY) — Cede ante P1 (Recolección) y P2 (Caminar)
def buffing_process(log_widget, cooldown_label):
    global running, config, pickup_active, moving_to_coords, buff_active, photo_active, manual_pause
    while running:
        if manual_pause or not config.data.get("buff_enabled", True):
            buff_active = False
            time.sleep(0.5)
            continue

        # Esperar si P1 (Pickup), P2 (Caminar) o P5 (Foto en curso) están activos
        if pickup_active or moving_to_coords or photo_active:
            buff_active = False
            time.sleep(0.2)
            continue
            
        start_time = time.time()
        if config.data["buff_skills"] and config.data["buff_players"]:
            buff_active = True
            # Dar 70ms para que P4 (Ataque) suelte el click derecho antes de seleccionar el skill
            time.sleep(0.07)

            for i, skill_area in enumerate(config.data["buff_skills"]):
                if not running or manual_pause or not config.data.get("buff_enabled", True):
                    break
                # Si cae una joya (P1) o llega orden de caminar (P2) a mitad del buffeo, esperar a que terminen
                while (pickup_active or moving_to_coords) and running and not manual_pause:
                    buff_active = False
                    time.sleep(0.1)
                buff_active = True

                cx = (skill_area["x1"] + skill_area["x2"]) // 2
                cy = (skill_area["y1"] + skill_area["y2"]) // 2
                pydirectinput.moveTo(cx, cy)
                time.sleep(0.05)
                pydirectinput.mouseDown(button='left')
                time.sleep(0.1)
                pydirectinput.mouseUp(button='left')
                log_message(f"Buff [P3]: Skill {i+1} seleccionado", log_widget)
                time.sleep(0.1)

                for j, player_area in enumerate(config.data["buff_players"]):
                    if not running or manual_pause or not config.data.get("buff_enabled", True):
                        break
                    while (pickup_active or moving_to_coords) and running and not manual_pause:
                        buff_active = False
                        time.sleep(0.1)
                    buff_active = True

                    cx_p = (player_area["x1"] + player_area["x2"]) // 2
                    cy_p = (player_area["y1"] + player_area["y2"]) // 2
                    pydirectinput.moveTo(cx_p, cy_p)
                    time.sleep(0.05)
                    pydirectinput.mouseDown(button='right')
                    time.sleep(0.1)
                    pydirectinput.mouseUp(button='right')
                    log_message(f"Buff [P3]: Jugador {j+1} buffeado", log_widget)
                    time.sleep(0.1)

            # Terminó de tirar los buffs: liberamos P3 para que P4 (Ataque) siga inmediatamente
            buff_active = False
            elapsed = time.time() - start_time
            cd = config.data["cooldown"]
            wait_time = max(5, cd - elapsed)
            remaining = int(wait_time)
            while remaining > 0 and running and config.data.get("buff_enabled", True):
                cooldown_label.after(0, lambda r=remaining: cooldown_label.config(text=f"Cooldown: {r} s"))
                time.sleep(1)
                remaining -= 1
        else:
            buff_active = False
            time.sleep(1)

# PRIORIDAD 4: ATAQUE (COMBATE) — Cede instantáneamente ante P1 (Pickup), P2 (Caminar), P3 (Buff) y P5 (Foto)
def attack_process(log_widget):
    global running, config, pickup_active, moving_to_coords, buff_active, photo_active, manual_pause
    with mss.mss() as sct:
        while running:
            if manual_pause or pickup_active or moving_to_coords or buff_active or photo_active:
                time.sleep(0.1)
                continue
            if not config.data.get("attack_enabled", False) or not config.data.get("attack_area"):
                time.sleep(0.6)
                continue

            area = config.data["attack_area"]
            monitor = {"top": area["y1"], "left": area["x1"], "width": area["x2"] - area["x1"], "height": area["y2"] - area["y1"]}
            img = np.array(sct.grab(monitor))
            bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            color_conf = config.data["attack_color"]
            lower = np.array(color_conf["lower"], dtype=np.uint8)
            upper = np.array(color_conf["upper"], dtype=np.uint8)
            mask = cv2.inRange(hsv, lower, upper)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            target_found = False

            for cnt in contours:
                if cv2.contourArea(cnt) > 5:
                    # Antes de presionar click derecho, verificar que no se haya activado una prioridad mayor
                    if pickup_active or moving_to_coords or buff_active or photo_active or manual_pause:
                        break
                    x, y, w, h = cv2.boundingRect(cnt)
                    center_x = area["x1"] + x + w // 2
                    center_y = area["y1"] + y + h // 2
                    pydirectinput.moveTo(center_x, center_y)
                    time.sleep(0.04)
                    log_message("Batalla [P4]: Atacando enemigo!", log_widget)
                    pydirectinput.mouseDown(button='right')
                    # Mantener click derecho hasta 1.0s, pero soltar en <= 50ms si entra P1 (Joya), P2 (Caminar) o P3 (Buff)
                    for _ in range(20):
                        if (not running or pickup_active or moving_to_coords or buff_active
                                or photo_active or manual_pause or not config.data.get("attack_enabled", False)):
                            break
                        time.sleep(0.05)
                    pydirectinput.mouseUp(button='right')
                    target_found = True
                    break 
            if not target_found:
                time.sleep(0.1)

# PRIORIDAD 5: FOTO DE INVENTARIO (MONITOR) — Espera a que P1, P2 y P3 estén libres
def capture_and_send_inventory(log_widget):
    """Abre el inventario con click inteligente, toma captura, lo cierra y envía la foto por Telegram."""
    global photo_active, pickup_active, moving_to_coords, buff_active
    btn_area = config.data["monitor"].get("button_area")
    if not btn_area:
        msg = "❌ Falta marcar el 'Botón Inventario' en la interfaz del bot."
        log_message(msg, log_widget)
        send_telegram(msg)
        return

    def _inv_worker():
        global photo_active
        # Esperar a que P1 (Recolección), P2 (Caminar) y P3 (Buff) estén libres antes de abrir el inventario
        while pickup_active or moving_to_coords or buff_active:
            time.sleep(0.25)

        log_message("🚦 Monitor [P5]: Pausando ataque para abrir inventario...", log_widget)
        photo_active = True
        time.sleep(1.0)
        try:
            cx = (btn_area["x1"] + btn_area["x2"]) // 2
            cy = (btn_area["y1"] + btn_area["y2"]) // 2

            pydirectinput.moveTo(cx, cy)
            time.sleep(0.2)
            pydirectinput.moveTo(cx + 1, cy + 1)
            time.sleep(0.4)

            pydirectinput.mouseDown(button='left')
            time.sleep(0.3)
            pydirectinput.mouseUp(button='left')
            time.sleep(1.5)

            filename = f"inventario_{int(time.time())}.png"
            area_conf = config.data["monitor"].get("area") or config.data.get("attack_area") or config.data.get("pickup_area")
            with mss.mss() as sct:
                if area_conf:
                    mon_dict = {"top": area_conf["y1"], "left": area_conf["x1"], "width": area_conf["x2"] - area_conf["x1"], "height": area_conf["y2"] - area_conf["y1"]}
                    img = np.array(sct.grab(mon_dict))
                    cv2.imwrite(filename, cv2.cvtColor(img, cv2.COLOR_BGRA2BGR))
                else:
                    sct.shot(mon=-1, output=filename)

            pydirectinput.mouseDown(button='left')
            time.sleep(0.3)
            pydirectinput.mouseUp(button='left')
            time.sleep(0.5)

            threading.Thread(target=send_telegram_photo_async, args=(filename, "🎒 Estado del Inventario"), daemon=True).start()
        finally:
            photo_active = False
            log_message("🚦 Monitor [P5]: Inventario cerrado y bot reanudado.", log_widget)

    threading.Thread(target=_inv_worker, daemon=True).start()

def capture_and_send_screen(log_widget):
    """Toma una foto instantánea de la pantalla/área del juego sin abrir el inventario ni interrumpir el bot."""
    def _scr_worker():
        filename = f"pantalla_{int(time.time())}.png"
        area_conf = config.data["monitor"].get("area") or config.data.get("attack_area") or config.data.get("pickup_area")
        with mss.mss() as sct:
            if area_conf:
                mon_dict = {"top": area_conf["y1"], "left": area_conf["x1"], "width": area_conf["x2"] - area_conf["x1"], "height": area_conf["y2"] - area_conf["y1"]}
                img = np.array(sct.grab(mon_dict))
                cv2.imwrite(filename, cv2.cvtColor(img, cv2.COLOR_BGRA2BGR))
            else:
                sct.shot(mon=-1, output=filename)
        coords_str = f" | Pos: {stats['current_coords']}" if stats.get("current_coords") else ""
        log_message("📸 Enviando captura de pantalla a Telegram...", log_widget)
        send_telegram_photo_async(filename, caption=f"📸 Vista actual del juego{coords_str}")

    threading.Thread(target=_scr_worker, daemon=True).start()

def monitor_process(log_widget):
    global running, config
    while running:
        try:
            interval_mins = int(config.data["monitor"].get("interval_minutes", 30))
            enabled = config.data["monitor"].get("enabled", False)
            btn_area = config.data["monitor"].get("button_area")
        except:
            time.sleep(5)
            continue
            
        if not enabled or interval_mins <= 0 or not btn_area:
            time.sleep(3)
            continue
        
        interval_secs = interval_mins * 60
        for _ in range(interval_secs):
            if not running or not config.data["monitor"].get("enabled", False):
                break
            time.sleep(1)
        
        if not running or not config.data["monitor"].get("enabled", False):
            continue
        
        capture_and_send_inventory(log_widget)
        time.sleep(5)

# ----- Lector de Coordenadas OCR (V17) -----
def preprocess_coords_image(img, thresh_val=150, invert=True):
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    if invert:
        gray = cv2.bitwise_not(gray)
    _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
    return thresh

def find_split_x_and_clean(thresh):
    h, w = thresh.shape
    cleaned = thresh.copy()
    fg = 255 - cleaned
    num_labels, labels, stats_cc, centroids = cv2.connectedComponentsWithStats(fg, connectivity=8)
    
    valid_boxes = []
    for i in range(1, num_labels):
        x, y, bw, bh, area = stats_cc[i]
        touches_border = (x <= 2) or (y <= 2) or (x + bw >= w - 2) or (y + bh >= h - 2)
        if touches_border or area < 15 or bh < h * 0.25 or bw > w * 0.35:
            cleaned[labels == i] = 255
        else:
            valid_boxes.append((x, y, bw, bh))
            
    valid_boxes.sort(key=lambda b: b[0])
    
    if len(valid_boxes) >= 2:
        max_gap = -999
        split_x = w // 2
        curr_right = valid_boxes[0][0] + valid_boxes[0][2]
        for idx in range(len(valid_boxes) - 1):
            curr_right = max(curr_right, valid_boxes[idx][0] + valid_boxes[idx][2])
            next_left = valid_boxes[idx + 1][0]
            gap = next_left - curr_right
            if gap > max_gap:
                max_gap = gap
                split_x = (curr_right + next_left) // 2
        if max_gap >= 4:
            return cleaned, split_x

    c_start = int(w * 0.25)
    c_end = int(w * 0.75)
    if c_end > c_start:
        col_ink = np.sum(cleaned[:, c_start:c_end] == 0, axis=0)
        split_x = c_start + int(np.argmin(col_ink))
        return cleaned, split_x
    else:
        split_x = w // 2
        return cleaned, split_x

def read_coords_from_screen(sct):
    area = config.data["coords"].get("area")
    if not area or not TESSERACT_PATH:
        return None, "", None, None, None
        
    mon_dict = {
        "top": area["y1"],
        "left": area["x1"],
        "width": max(1, area["x2"] - area["x1"]),
        "height": max(1, area["y2"] - area["y1"])
    }
    img = np.array(sct.grab(mon_dict), dtype=np.uint8)
    thresh_val = int(config.data["coords"].get("threshold", 150))
    invert = bool(config.data["coords"].get("invert", True))
    raw_thresh = preprocess_coords_image(img, thresh_val, invert)
    
    thresh, split_x = find_split_x_and_clean(raw_thresh)
    custom_config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
    
    try:
        boxes_str = pytesseract.image_to_boxes(raw_thresh, config=custom_config).strip()
        left_chars = []
        right_chars = []
        for line in boxes_str.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].isdigit():
                ch = parts[0]
                x1, x2 = int(parts[1]), int(parts[3])
                center_x = (x2 - 5) if x1 <= 2 else ((x1 + 5) if x2 >= raw_thresh.shape[1] - 2 else (x1 + x2) // 2)
                if center_x < split_x:
                    left_chars.append(ch)
                else:
                    right_chars.append(ch)
                    
        digits_x = "".join(left_chars)
        digits_y = "".join(right_chars)
        
        if not (digits_x and digits_y):
            left_part = cv2.copyMakeBorder(thresh[:, :split_x], 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
            right_part = cv2.copyMakeBorder(thresh[:, split_x:], 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
            if not digits_x:
                digits_x = "".join(re.findall(r'\d+', pytesseract.image_to_string(left_part, config=custom_config)))
            if not digits_y:
                digits_y = "".join(re.findall(r'\d+', pytesseract.image_to_string(right_part, config=custom_config)))
                
        raw_text = f"{digits_x} | {digits_y}"
        if digits_x and digits_y:
            cx, cy = int(digits_x), int(digits_y)
            if 0 <= cx <= 255 and 0 <= cy <= 255:
                return (cx, cy), raw_text, img, thresh, split_x
        return None, raw_text, img, thresh, split_x
    except Exception:
        return None, "", img, thresh, split_x

def read_stable_coords(sct, retries=3, prev_coords=None, max_jump=30):
    """Lee las coordenadas filtrando posibles lecturas erróneas de 1 frame de OCR."""
    readings = []
    for _ in range(retries):
        coords, _, _, _, _ = read_coords_from_screen(sct)
        if coords is not None:
            if prev_coords is not None:
                jump = math.hypot(coords[0] - prev_coords[0], coords[1] - prev_coords[1])
                if jump <= max_jump:
                    return coords
            readings.append(coords)
            if len(readings) >= 2 and readings[-1] == readings[-2]:
                return coords
        time.sleep(0.12)
    return readings[-1] if readings else None

def coords_process(log_widget):
    global running, photo_active, config, stats, moving_to_coords
    last_logged = None
    with mss.mss() as sct:
        while running:
            if moving_to_coords:
                time.sleep(0.5)
                continue
            if photo_active or not config.data["coords"].get("enabled", False) or not config.data["coords"].get("area"):
                time.sleep(1.0)
                continue
            if not TESSERACT_PATH:
                log_message("❌ OCR Error: No se encontró Tesseract-OCR instalado.", log_widget)
                time.sleep(5.0)
                continue
                
            coords, raw_text, _, _, _ = read_coords_from_screen(sct)
            if coords:
                stats["current_coords"] = coords
                if stats["spot_coords"] is None:
                    stats["spot_coords"] = coords
                    log_message(f"🧭 Spot fijado en coordenadas: X={coords[0]}, Y={coords[1]}", log_widget)
                elif coords != last_logged:
                    dx = coords[0] - stats["spot_coords"][0]
                    dy = coords[1] - stats["spot_coords"][1]
                    dist = int((dx**2 + dy**2)**0.5)
                    log_message(f"🧭 Coordenadas: ({coords[0]}, {coords[1]}) | Dist. del Spot: {dist} pasos (ΔX:{dx:+d}, ΔY:{dy:+d})", log_widget)
                    last_logged = coords
            time.sleep(1.5)

def calibrate_coords_window(log_widget):
    area = config.data["coords"].get("area")
    if not area:
        messagebox.showwarning("Falta Zona", "Primero marca la 'Zona Coordenadas' en la pantalla del juego.")
        return
    if not TESSERACT_PATH:
        messagebox.showerror("Error Tesseract", "No se encontró Tesseract-OCR en el sistema.")
        return

    def _run_calibrator():
        win_name = "Lector MU - Calibracion OCR (Presiona 'q' o ESC para salir)"
        cv2.namedWindow(win_name, cv2.WINDOW_AUTOSIZE)
        init_thresh = int(config.data["coords"].get("threshold", 150))
        init_inv = 1 if config.data["coords"].get("invert", True) else 0
        
        cv2.createTrackbar("Umbral", win_name, init_thresh, 255, lambda x: None)
        cv2.createTrackbar("Invertir", win_name, init_inv, 1, lambda x: None)
        
        log_message("🔍 Calibrador OCR abierto. Ajusta las barras y presiona 'q' en la ventana para guardar.", log_widget)
        
        with mss.mss() as sct:
            while True:
                try:
                    if cv2.getWindowProperty(win_name, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except:
                    break
                    
                t_val = cv2.getTrackbarPos("Umbral", win_name)
                inv_val = bool(cv2.getTrackbarPos("Invertir", win_name))
                
                config.data["coords"]["threshold"] = t_val
                config.data["coords"]["invert"] = inv_val
                
                coords, raw_text, img, thresh, split_x = read_coords_from_screen(sct)
                
                if img is not None and thresh is not None:
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    img_resized = cv2.resize(img_bgr, (thresh.shape[1], thresh.shape[0]))
                    thresh_bgr = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
                    
                    if split_x is not None:
                        cv2.line(img_resized, (split_x, 0), (split_x, img_resized.shape[0]), (255, 200, 0), 2)
                        cv2.line(thresh_bgr, (split_x, 0), (split_x, thresh_bgr.shape[0]), (255, 0, 0), 2)
                        
                    combined = np.vstack([img_resized, thresh_bgr])
                    info_panel = np.zeros((75, max(combined.shape[1], 380), 3), dtype=np.uint8)
                    if combined.shape[1] < info_panel.shape[1]:
                        pad = info_panel.shape[1] - combined.shape[1]
                        combined = cv2.copyMakeBorder(combined, 0, 0, 0, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0))
                        
                    status_color = (0, 255, 0) if coords else (0, 165, 255)
                    parsed_str = f"X={coords[0]} | Y={coords[1]}" if coords else "Sin detectar (Ajusta Umbral)"
                    
                    cv2.putText(info_panel, f"OCR Mitades: '{raw_text}'", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
                    cv2.putText(info_panel, f"Detectado: {parsed_str}", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)
                    
                    final_view = np.vstack([combined, info_panel])
                    cv2.imshow(win_name, final_view)
                    
                key = cv2.waitKey(250) & 0xFF
                if key == ord('q') or key == 27:
                    break
                    
        cv2.destroyAllWindows()
        config.save()
        log_message(f"✅ Calibración OCR guardada (Umbral: {config.data['coords']['threshold']}, Invertir: {config.data['coords']['invert']}).", log_widget)

    threading.Thread(target=_run_calibrator, daemon=True).start()

# ----- PRIORIDAD 2: MÓDULO DE MOVIMIENTO POR COORDENADAS (Cede ante P1 Recolección, Pausa P3/P4/P5) -----
def perform_walk_click(click_x, click_y):
    """Realiza un click izquierdo compatible con DirectX/MU Online para caminar."""
    x1, y1, x2, y2 = get_playable_bounds()
    cx = max(x1, min(x2, int(click_x)))
    cy = max(y1, min(y2, int(click_y)))
    pydirectinput.moveTo(cx, cy)
    time.sleep(0.04)
    pydirectinput.moveTo(cx + 1, cy + 1)
    time.sleep(0.05)
    pydirectinput.mouseDown(button='left')
    time.sleep(0.12)
    pydirectinput.mouseUp(button='left')

def world_delta_to_screen_unit(dx, dy):
    """
    Convierte el vector deseado de coordenadas del juego (dx, dy) en un vector
    unitario de dirección en pantalla (ux, uy), usando la calibración guardada
    o la proyección isométrica estándar de MU Online.
    """
    calib = config.data["coords"].get("calibration")
    if calib and "v_right" in calib and "v_up" in calib:
        rx, ry = calib["v_right"]
        ux_w, uy_w = calib["v_up"]
        a, b = rx, -ux_w
        c, d = ry, -uy_w
        det = a * d - b * c
        if abs(det) > 1e-4:
            sx = (d * dx - b * dy) / det
            sy = (-c * dx + a * dy) / det
            norm = math.hypot(sx, sy)
            if norm > 1e-5:
                return sx / norm, sy / norm

    sx = float(dx + dy)
    sy = float(dx - dy) * 0.78
    norm = math.hypot(sx, sy)
    if norm < 1e-5:
        return 0.0, 0.0
    return sx / norm, sy / norm

def calibrate_movement_axes(log_widget, notify_telegram=False):
    """
    Realiza 2 clicks de prueba (Derecha y Arriba del PJ) y lee las coordenadas
    por OCR para aprender automáticamente la orientación exacta de los ejes X/Y.
    """
    global moving_to_coords
    if not config.data["coords"].get("area"):
        msg = "❌ Primero marca la 'Zona Coords' antes de calibrar el movimiento."
        log_message(msg, log_widget)
        if notify_telegram: send_telegram(msg)
        return False

    if not move_lock.acquire(blocking=False):
        msg = "⚠️ Ya hay un movimiento o calibración en curso."
        log_message(msg, log_widget)
        if notify_telegram: send_telegram(msg)
        return False

    def _calib_worker():
        global moving_to_coords
        moving_to_coords = True
        try:
            log_message("🎯 Iniciando auto-calibración de ejes de movimiento...", log_widget)
            if notify_telegram:
                send_telegram("🎯 Calibrando ejes de movimiento (2 pasos de prueba)...")

            time.sleep(0.6)
            cx_scr, cy_scr = get_character_screen_center()

            with mss.mss() as sct:
                p0 = read_stable_coords(sct, retries=5)
                if not p0:
                    msg = "❌ No se pudieron leer las coordenadas actuales por OCR. Revisa el Calibrador OCR."
                    log_message(msg, log_widget)
                    if notify_telegram: send_telegram(msg)
                    return

                perform_walk_click(cx_scr + 95, cy_scr)
                time.sleep(1.3)
                p1 = read_stable_coords(sct, retries=5, prev_coords=p0, max_jump=15)
                if not p1 or p1 == p0:
                    perform_walk_click(cx_scr - 95, cy_scr)
                    time.sleep(1.3)
                    p1 = read_stable_coords(sct, retries=5, prev_coords=p0, max_jump=15)
                    if not p1 or p1 == p0:
                        msg = "⚠️ El PJ no se movió en el paso horizontal. Asegúrate de estar en una zona libre de obstáculos."
                        log_message(msg, log_widget)
                        if notify_telegram: send_telegram(msg)
                        return
                    v_right = [-(p1[0] - p0[0]), -(p1[1] - p0[1])]
                else:
                    v_right = [p1[0] - p0[0], p1[1] - p0[1]]

                perform_walk_click(cx_scr, cy_scr - 85)
                time.sleep(1.3)
                p2 = read_stable_coords(sct, retries=5, prev_coords=p1, max_jump=15)
                if not p2 or p2 == p1:
                    perform_walk_click(cx_scr, cy_scr + 85)
                    time.sleep(1.3)
                    p2 = read_stable_coords(sct, retries=5, prev_coords=p1, max_jump=15)
                    if not p2 or p2 == p1:
                        msg = "⚠️ El PJ no se movió en el paso vertical. Intenta calibrar en un espacio abierto."
                        log_message(msg, log_widget)
                        if notify_telegram: send_telegram(msg)
                        return
                    v_up = [-(p2[0] - p1[0]), -(p2[1] - p1[1])]
                else:
                    v_up = [p2[0] - p1[0], p2[1] - p1[1]]

                det = v_right[0] * (-v_up[1]) - v_right[1] * (-v_up[0])
                if abs(det) < 0.1:
                    msg = f"⚠️ Calibración ambigua (Derecha={v_right}, Arriba={v_up}). Inténtalo en una zona despejada."
                    log_message(msg, log_widget)
                    if notify_telegram: send_telegram(msg)
                    return

                config.data["coords"]["calibration"] = {
                    "v_right": v_right,
                    "v_up": v_up
                }
                config.save()
                stats["current_coords"] = p2
                msg = f"✅ Ejes calibrados con éxito: Derecha -> Δ({v_right[0]:+d}, {v_right[1]:+d}), Arriba -> Δ({v_up[0]:+d}, {v_up[1]:+d})"
                log_message(msg, log_widget)
                if notify_telegram:
                    send_telegram(msg)
        finally:
            moving_to_coords = False
            move_lock.release()

    threading.Thread(target=_calib_worker, daemon=True).start()
    return True

def move_to_coordinates(target_x, target_y, log_widget, notify_telegram=True):
    """
    Prioridad 2: Mueve el PJ haciendo clicks en pantalla hasta llegar a (target_x, target_y).
    Si en el camino detecta una joya en el piso (Prioridad 1: pickup_active), espera a que la levante y luego continúa.
    """
    global moving_to_coords, pickup_active, stats

    if not config.data["coords"].get("area"):
        msg = "❌ No está marcada la 'Zona Coords' para leer las coordenadas."
        log_message(msg, log_widget)
        if notify_telegram: send_telegram(msg)
        return False

    if not TESSERACT_PATH:
        msg = "❌ No se encontró Tesseract-OCR instalado."
        log_message(msg, log_widget)
        if notify_telegram: send_telegram(msg)
        return False

    stats["target_coords"] = (int(target_x), int(target_y))
    if moving_to_coords:
        msg = f"🧭 Destino actualizado en caliente a ({target_x}, {target_y})."
        log_message(msg, log_widget)
        if notify_telegram: send_telegram(msg)
        return True

    if not move_lock.acquire(blocking=False):
        return False

    def _move_worker():
        global moving_to_coords, pickup_active, stats
        moving_to_coords = True
        tolerance = int(config.data["coords"].get("tolerance", 1))
        angle_correction = 0.0
        stuck_count = 0
        ocr_fail_count = 0
        max_steps = 80
        detour_angles = [0.95, -0.95, 1.55, -1.55, 2.3, -2.3]

        try:
            tx, ty = stats["target_coords"]
            log_message(f"🚶 [P2] Iniciando movimiento hacia X={tx}, Y={ty}...", log_widget)
            if notify_telegram:
                send_telegram(f"🚶 En camino hacia ({tx}, {ty})...")

            with mss.mss() as sct:
                curr = read_stable_coords(sct, retries=4, prev_coords=stats.get("current_coords"))
                if not curr:
                    msg = "❌ No se pudo leer la coordenada inicial en pantalla. Verifica que el juego esté visible."
                    log_message(msg, log_widget)
                    if notify_telegram: send_telegram(msg)
                    return

                stats["current_coords"] = curr

                for step in range(1, max_steps + 1):
                    if not moving_to_coords:
                        log_message("⏹ Movimiento por coordenadas cancelado.", log_widget)
                        if notify_telegram: send_telegram("⏹ Movimiento cancelado.")
                        return

                    # Ceder ante Prioridad 1 (Recolección): si ve una joya en el camino, espera a levantarla
                    if pickup_active:
                        log_message("💎 [P1 > P2] Pausando caminata un instante para recoger ítem...", log_widget)
                        while pickup_active and moving_to_coords:
                            time.sleep(0.1)
                        # Actualizar posición actual tras haber caminado hacia la joya
                        after_pickup = read_stable_coords(sct, retries=3, prev_coords=curr, max_jump=25)
                        if after_pickup:
                            curr = after_pickup
                            stats["current_coords"] = curr

                    tx, ty = stats["target_coords"]
                    dx = tx - curr[0]
                    dy = ty - curr[1]
                    dist = math.hypot(dx, dy)

                    if abs(dx) <= tolerance and abs(dy) <= tolerance:
                        time.sleep(0.35)
                        confirm = read_stable_coords(sct, retries=3, prev_coords=curr, max_jump=10)
                        if confirm:
                            curr = confirm
                            stats["current_coords"] = curr
                        if abs(tx - curr[0]) <= tolerance and abs(ty - curr[1]) <= tolerance:
                            stats["spot_coords"] = curr
                            stats["target_coords"] = None
                            msg = f"✅ ¡Llegamos al destino! Coordenada actual: ({curr[0]}, {curr[1]}). Spot actualizado."
                            log_message(msg, log_widget)
                            if notify_telegram: send_telegram(msg, with_keyboard=True)
                            return

                    ux, uy = world_delta_to_screen_unit(dx, dy)

                    rot = angle_correction
                    if stuck_count > 0:
                        detour_idx = (stuck_count - 1) % len(detour_angles)
                        rot += detour_angles[detour_idx]
                        log_message(f"⚠️ Obstáculo detectado en ({curr[0]}, {curr[1]}), intentando rodeo #{stuck_count}...", log_widget)

                    cos_r = math.cos(rot)
                    sin_r = math.sin(rot)
                    rx_u = ux * cos_r - uy * sin_r
                    ry_u = ux * sin_r + uy * cos_r

                    if dist >= 6:
                        radius = 115
                    elif dist >= 3:
                        radius = 78
                    elif dist >= 2:
                        radius = 55
                    else:
                        radius = 38

                    if stuck_count > 0:
                        radius = max(radius, 95)

                    cx_scr, cy_scr = get_character_screen_center()
                    click_x = cx_scr + int(rx_u * radius)
                    click_y = cy_scr + int(ry_u * radius)

                    perform_walk_click(click_x, click_y)

                    wait_t = 0.85 if dist >= 4 else 0.65
                    # Dormir en intervalos cortos por si aparece una joya (P1) durante el paso
                    for _ in range(int(wait_t / 0.05)):
                        if not moving_to_coords or pickup_active:
                            break
                        time.sleep(0.05)

                    if pickup_active:
                        continue

                    new_coords = read_stable_coords(sct, retries=3, prev_coords=curr, max_jump=20)
                    if not new_coords:
                        ocr_fail_count += 1
                        if ocr_fail_count >= 6:
                            msg = f"❌ Se perdió la lectura OCR de coordenadas camino a ({tx}, {ty}). Última pos: {curr}"
                            log_message(msg, log_widget)
                            if notify_telegram: send_telegram(msg)
                            return
                        continue

                    ocr_fail_count = 0
                    stats["current_coords"] = new_coords

                    step_dx = new_coords[0] - curr[0]
                    step_dy = new_coords[1] - curr[1]
                    step_dist = math.hypot(step_dx, step_dy)

                    if step_dist < 0.5:
                        stuck_count += 1
                        if stuck_count >= 12:
                            msg = f"⚠️ No se pudo avanzar más hacia ({tx}, {ty}) por obstáculos. Posición actual: ({curr[0]}, {curr[1]})."
                            log_message(msg, log_widget)
                            if notify_telegram: send_telegram(msg)
                            return
                    else:
                        if stuck_count == 0 and not config.data["coords"].get("calibration") and 1.0 <= step_dist <= 10.0:
                            desired_ang = math.atan2(dy, dx)
                            actual_ang = math.atan2(step_dy, step_dx)
                            err_ang = math.atan2(math.sin(desired_ang - actual_ang), math.cos(desired_ang - actual_ang))
                            if abs(err_ang) > 0.35:
                                angle_correction -= err_ang * 0.6

                        stuck_count = 0
                        curr = new_coords
                        new_dist = int(math.hypot(tx - curr[0], ty - curr[1]))
                        log_message(f"🚶 [P2] Caminando: ({curr[0]}, {curr[1]}) -> Destino ({tx}, {ty}) [Faltan ~{new_dist} pasos]", log_widget)

                msg = f"⏳ Tiempo/pasos agotados intentando llegar a ({tx}, {ty}). Posición actual: ({curr[0]}, {curr[1]})."
                log_message(msg, log_widget)
                if notify_telegram: send_telegram(msg)
        finally:
            stats["target_coords"] = None
            moving_to_coords = False
            move_lock.release()

    threading.Thread(target=_move_worker, daemon=True).start()
    return True

def cancel_coordinate_movement():
    global moving_to_coords
    moving_to_coords = False

# ----- Listener de Comandos de Telegram en Segundo Plano -----
telegram_listener_started = False

def start_telegram_listener(log_widget):
    global telegram_listener_started
    if telegram_listener_started:
        return
    telegram_listener_started = True
    threading.Thread(target=telegram_listener_process, args=(log_widget,), daemon=True).start()

def telegram_listener_process(log_widget):
    global running, moving_to_coords, stats
    last_update_id = None

    while True:
        token = config.data["telegram"].get("token", "").strip()
        chat_id = str(config.data["telegram"].get("chat_id", "")).strip()
        if not token or not chat_id:
            time.sleep(3)
            continue

        url = f"https://api.telegram.org/bot{token}/getUpdates"
        params = {"timeout": 10}
        if last_update_id is not None:
            params["offset"] = last_update_id + 1

        try:
            res = requests.get(url, params=params, timeout=15)
            if res.status_code != 200:
                time.sleep(3)
                continue

            data = res.json()
            if not data.get("ok"):
                time.sleep(3)
                continue

            for update in data.get("result", []):
                update_id = update.get("update_id")
                if update_id is not None:
                    if last_update_id is None:
                        last_update_id = update_id
                        continue
                    last_update_id = update_id

                msg_obj = update.get("message") or update.get("edited_message")
                if not msg_obj:
                    continue

                sender_chat_id = str(msg_obj.get("chat", {}).get("id", ""))
                if sender_chat_id != chat_id:
                    continue

                text = (msg_obj.get("text") or "").strip()
                if not text:
                    continue

                handle_telegram_command(text, log_widget)

            if last_update_id is None:
                last_update_id = 0

        except Exception:
            time.sleep(3)

def parse_toggle_arg(cmd_lower, current_val):
    """Determina si el comando pide encender (on/1/si), apagar (off/0/no) o alternar el valor actual."""
    parts = cmd_lower.split()
    if len(parts) >= 2:
        arg = parts[-1]
        if arg in ("on", "1", "si", "sí", "activar", "true"):
            return True
        if arg in ("off", "0", "no", "desactivar", "false"):
            return False
    return not current_val

def ensure_bot_running_if_needed(log_widget):
    """Si el usuario activa una función desde Telegram y el bot estaba detenido, lo inicia automáticamente."""
    global running, app_instance
    if not running and app_instance is not None:
        app_instance.after(0, lambda: start_activity(app_instance.log_text, app_instance.cooldown_label))
        return True
    return False

def handle_telegram_command(text, log_widget):
    global running, manual_pause, stats, app_instance
    cmd_lower = text.lower().strip()
    log_message(f"📱 Comando Telegram: {text}", log_widget)

    # 1. Menú y Ayuda
    if cmd_lower in ("/start", "/ayuda", "/help", "ayuda", "/menu", "menu", "❓ ayuda"):
        help_msg = (
            "🤖 PANEL DE CONTROL — BOT MU MENDOZA\n\n"
            "⚡ PRIORIDAD INTELIGENTE ACTIVA:\n"
            "1° Recolección > 2° Caminar > 3° Buff > 4° Ataque > 5° Foto\n\n"
            "🎮 CONTROL GENERAL:\n"
            "• /iniciar — Inicia el bot (F5)\n"
            "• /detener — Detiene el bot (F6)\n"
            "• /pausa / /reanudar — Pausa o reanuda acciones\n"
            "• /estado — Reporte completo en vivo\n\n"
            "⚔️ MÓDULOS (puedes usar on/off o alternar):\n"
            "• /atacar [on|off] — Activa/desactiva Combate\n"
            "• /pickup [on|off] — Activa/desactiva Recolección\n"
            "• /buff [on|off] — Activa/desactiva Magias/Auras\n"
            "• /cooldown N — Fija segundos de espera de Auras\n"
            "• /items — Lista joyas activas en Pickup\n"
            "• /item <nombre> [on|off] — Activa/desactiva joya\n\n"
            "📸 CÁMARA Y MONITOR:\n"
            "• /foto — Captura instantánea de la pantalla\n"
            "• /inventario — Abre inventario, saca foto y cierra\n"
            "• /monitor [on|off|minutos] — Configura el monitor\n\n"
            "🧭 MOVIMIENTO POR COORDENADAS:\n"
            "• /ir X Y — Camina haciendo clicks hasta (X, Y)\n"
            "• /pos — Lee las coordenadas actuales\n"
            "• /volver — Camina de regreso al Spot fijado\n"
            "• /fijarspot — Guarda posición actual como Spot\n"
            "• /calibrar — Auto-calibra los ejes en 2 pasos\n"
            "• /cancelar — Detiene la caminata actual"
        )
        send_telegram(help_msg, with_keyboard=True)
        return

    # 2. Iniciar / Detener / Pausar Bot General
    if cmd_lower in ("/iniciar", "/startbot", "/f5", "iniciar", "▶ iniciar bot"):
        if running:
            manual_pause = False
            send_telegram("⚔️ El bot ya está en marcha.", with_keyboard=True)
        else:
            if app_instance is not None:
                app_instance.after(0, lambda: start_activity(app_instance.log_text, app_instance.cooldown_label))
        return

    if cmd_lower in ("/detener", "/stopbot", "/f6", "detener", "⏹ detener bot"):
        if running:
            if app_instance is not None:
                app_instance.after(0, lambda: stop_activity(app_instance.log_text))
        else:
            send_telegram("⏹ El bot ya se encuentra detenido.", with_keyboard=True)
        return

    if cmd_lower in ("/pausa", "/pausar", "pausa", "pausar"):
        manual_pause = True
        log_message("⏸ Bot pausado desde Telegram.", log_widget)
        send_telegram("⏸ Bot en PAUSA. Usa /reanudar para continuar.", with_keyboard=True)
        return

    if cmd_lower in ("/reanudar", "/continuar", "reanudar", "continuar"):
        manual_pause = False
        log_message("▶ Bot reanudado desde Telegram.", log_widget)
        send_telegram("▶ Bot REANUDADO.", with_keyboard=True)
        return

    # 3. Control de Ataque (Combate)
    if cmd_lower.startswith("/atacar") or cmd_lower.startswith("/ataque") or cmd_lower.startswith("⚔️ ataque"):
        new_state = parse_toggle_arg(cmd_lower, config.data.get("attack_enabled", False))
        if new_state and not config.data.get("attack_area"):
            send_telegram("❌ No puedes activar Ataque porque falta marcar la 'Zona de Caza' en la PC.", with_keyboard=True)
            return
        config.data["attack_enabled"] = new_state
        config.save()
        sync_ui_from_config()
        auto_started = ensure_bot_running_if_needed(log_widget) if new_state else False
        estado_str = "ACTIVADO 🟢" if new_state else "DESACTIVADO 🔴"
        extra = " (Bot iniciado automáticamente)" if auto_started else ""
        log_message(f"⚔️ Combate {estado_str} desde Telegram.", log_widget)
        send_telegram(f"⚔️ Modo Combate: {estado_str}{extra}", with_keyboard=True)
        return

    # 4. Control de Pickup (Recolección)
    if cmd_lower.startswith("/pickup") or cmd_lower.startswith("/loot") or cmd_lower.startswith("💎 pickup"):
        new_state = parse_toggle_arg(cmd_lower, config.data.get("pickup_enabled", False))
        if new_state and not config.data.get("pickup_area"):
            send_telegram("❌ No puedes activar Pickup porque falta marcar la 'Zona de Suelo' en la PC.", with_keyboard=True)
            return
        config.data["pickup_enabled"] = new_state
        config.save()
        sync_ui_from_config()
        auto_started = ensure_bot_running_if_needed(log_widget) if new_state else False
        estado_str = "ACTIVADO 🟢" if new_state else "DESACTIVADO 🔴"
        extra = " (Bot iniciado automáticamente)" if auto_started else ""
        log_message(f"💎 Recolección (Pickup) {estado_str} desde Telegram.", log_widget)
        send_telegram(f"💎 Recolección (Pickup): {estado_str}{extra}", with_keyboard=True)
        return

    # 5. Control de Items individuales de Pickup (/items y /item <nombre> [on|off])
    if cmd_lower in ("/items", "/joyas", "items", "joyas"):
        lines = []
        for k, v in config.data["pickup_colors"].items():
            icon = "🟢" if v.get("active", True) else "🔴"
            lines.append(f"{icon} {k}: {'Activo' if v.get('active', True) else 'Inactivo'}")
        send_telegram("💎 ITEMS EN PICKUP:\n" + "\n".join(lines) + "\n\nUsa `/item nombre on` o `/item nombre off` para cambiar.", with_keyboard=True)
        return

    if cmd_lower.startswith("/item "):
        parts = cmd_lower.split()
        if len(parts) >= 2:
            item_name = parts[1]
            if item_name not in config.data["pickup_colors"]:
                send_telegram(f"⚠️ El item '{item_name}' no existe. Usa /items para ver la lista.", with_keyboard=True)
                return
            curr_active = config.data["pickup_colors"][item_name].get("active", True)
            new_active = parse_toggle_arg(cmd_lower, curr_active) if len(parts) >= 3 else (not curr_active)
            config.data["pickup_colors"][item_name]["active"] = new_active
            config.save()
            sync_ui_from_config()
            send_telegram(f"💎 Item '{item_name.capitalize()}': {'ACTIVADO 🟢' if new_active else 'DESACTIVADO 🔴'}", with_keyboard=True)
            return

    # 6. Control de Buffs / Magias y Cooldown
    if cmd_lower.startswith("/buff") or cmd_lower.startswith("/auras") or cmd_lower.startswith("✨ buffs"):
        new_state = parse_toggle_arg(cmd_lower, config.data.get("buff_enabled", False))
        config.data["buff_enabled"] = new_state
        config.save()
        sync_ui_from_config()
        auto_started = ensure_bot_running_if_needed(log_widget) if new_state else False
        estado_str = "ACTIVADAS 🟢" if new_state else "DESACTIVADAS 🔴"
        extra = " (Bot iniciado automáticamente)" if auto_started else ""
        log_message(f"✨ Magias/Buffs {estado_str} desde Telegram.", log_widget)
        send_telegram(f"✨ Magias/Auras: {estado_str}{extra}", with_keyboard=True)
        return

    if cmd_lower.startswith("/cooldown"):
        parts = cmd_lower.split()
        if len(parts) >= 2 and parts[1].isdigit():
            cd_val = max(5, int(parts[1]))
            config.data["cooldown"] = cd_val
            config.save()
            sync_ui_from_config()
            log_message(f"⏱ Cooldown actualizado a {cd_val}s desde Telegram.", log_widget)
            send_telegram(f"⏱ Cooldown de Auras fijado en {cd_val} segundos.", with_keyboard=True)
        else:
            send_telegram(f"⏱ Cooldown actual: {config.data['cooldown']}s. Usa `/cooldown 20` para cambiarlo.", with_keyboard=True)
        return

    # 7. Fotos bajo demanda (/foto y /inventario) y Monitor
    if cmd_lower in ("/foto", "/pantalla", "foto", "📸 foto pantalla"):
        capture_and_send_screen(log_widget)
        return

    if cmd_lower in ("/inventario", "/inv", "/baul", "🎒 foto inventario"):
        capture_and_send_inventory(log_widget)
        return

    if cmd_lower.startswith("/monitor"):
        parts = cmd_lower.split()
        if len(parts) >= 2 and parts[1].isdigit():
            mins = max(1, int(parts[1]))
            config.data["monitor"]["interval_minutes"] = mins
            config.data["monitor"]["enabled"] = True
            config.save()
            sync_ui_from_config()
            send_telegram(f"📸 Monitor automático ACTIVADO cada {mins} minutos.", with_keyboard=True)
        else:
            new_state = parse_toggle_arg(cmd_lower, config.data["monitor"].get("enabled", False))
            config.data["monitor"]["enabled"] = new_state
            config.save()
            sync_ui_from_config()
            send_telegram(f"📸 Monitor automático: {'ACTIVADO 🟢' if new_state else 'DESACTIVADO 🔴'} (Intervalo: {config.data['monitor']['interval_minutes']} min).", with_keyboard=True)
        return

    if cmd_lower.startswith("/ocr") or cmd_lower.startswith("/lector"):
        new_state = parse_toggle_arg(cmd_lower, config.data["coords"].get("enabled", False))
        config.data["coords"]["enabled"] = new_state
        config.save()
        sync_ui_from_config()
        send_telegram(f"🧭 Lector continuo de coordenadas: {'ACTIVADO 🟢' if new_state else 'DESACTIVADO 🔴'}", with_keyboard=True)
        return

    # 8. Consultar posición / estado general
    if cmd_lower in ("/pos", "/coords", "pos", "coords", "📍 posición"):
        with mss.mss() as sct:
            live_coords = read_stable_coords(sct, retries=2)
            if live_coords:
                stats["current_coords"] = live_coords
        curr_str = f"({stats['current_coords'][0]}, {stats['current_coords'][1]})" if stats["current_coords"] else "Sin detectar"
        spot_str = f"({stats['spot_coords'][0]}, {stats['spot_coords'][1]})" if stats["spot_coords"] else "No fijado"
        send_telegram(f"📍 Coordenada actual: {curr_str}\n📌 Spot fijado: {spot_str}", with_keyboard=True)
        return

    if cmd_lower in ("/estado", "estado", "📊 estado"):
        with mss.mss() as sct:
            if config.data["coords"].get("area"):
                live_coords = read_stable_coords(sct, retries=2)
                if live_coords:
                    stats["current_coords"] = live_coords
        curr_str = f"({stats['current_coords'][0]}, {stats['current_coords'][1]})" if stats["current_coords"] else "Sin detectar"
        spot_str = f"({stats['spot_coords'][0]}, {stats['spot_coords'][1]})" if stats["spot_coords"] else "No fijado"
        if pickup_active:
            estado_bot = "Levantando Joya [P1] 💎"
        elif moving_to_coords:
            estado_bot = f"Caminando hacia {stats.get('target_coords')} [P2] 🚶"
        elif buff_active:
            estado_bot = "Lanzando Buffs [P3] ✨"
        elif not running:
            estado_bot = "Detenido ⏹"
        elif manual_pause:
            estado_bot = "Pausado ⏸"
        else:
            estado_bot = "Activo Farmeando [P4] ⚔️"

        elapsed = int(time.time() - stats["start_time"]) if (running and stats["start_time"]) else 0
        hrs, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

        atk_s = "🟢 ON" if config.data.get("attack_enabled") else "🔴 OFF"
        pck_s = "🟢 ON" if config.data.get("pickup_enabled") else "🔴 OFF"
        buf_s = "🟢 ON" if config.data.get("buff_enabled") else "🔴 OFF"
        mon_s = f"🟢 ({config.data['monitor']['interval_minutes']}m)" if config.data["monitor"].get("enabled") else "🔴 OFF"

        items_str = "\n".join([f"🔹 {k.capitalize()}: {v}" for k, v in stats["items"].items()]) or "Ninguno aún"
        send_telegram(
            f"📊 ESTADO DEL BOT MU MENDOZA\n"
            f"🤖 Estado: {estado_bot}\n"
            f"⏳ Tiempo activo: {time_str}\n"
            f"📍 Posición: {curr_str} | Spot: {spot_str}\n\n"
            f"⚙️ MÓDULOS:\n"
            f"⚔️ Ataque: {atk_s} | 💎 Pickup: {pck_s}\n"
            f"✨ Buffs: {buf_s} | 📸 Monitor: {mon_s}\n\n"
            f"🎒 ITEMS RECOLECTADOS:\n{items_str}",
            with_keyboard=True
        )
        return

    # 9. Cancelar movimiento
    if cmd_lower in ("/cancelar", "/stopmove", "cancelar"):
        if moving_to_coords:
            cancel_coordinate_movement()
        else:
            send_telegram("ℹ️ El PJ no se está moviendo en este momento.", with_keyboard=True)
        return

    # 10. Calibrar ejes
    if cmd_lower in ("/calibrar", "calibrar"):
        calibrate_movement_axes(log_widget, notify_telegram=True)
        return

    # 11. Fijar spot actual
    if cmd_lower in ("/fijarspot", "/setspot", "fijarspot", "📌 fijar spot"):
        with mss.mss() as sct:
            c = read_stable_coords(sct, retries=3)
        if c:
            stats["current_coords"] = c
            stats["spot_coords"] = c
            send_telegram(f"📌 Nuevo Spot fijado en ({c[0]}, {c[1]}).", with_keyboard=True)
            log_message(f"📌 Spot actualizado desde Telegram: ({c[0]}, {c[1]})", log_widget)
        else:
            send_telegram("❌ No se pudo leer la coordenada actual en pantalla.", with_keyboard=True)
        return

    # 12. Volver al spot
    if cmd_lower in ("/volver", "/spot", "volver", "🏠 volver al spot"):
        if stats["spot_coords"]:
            sx, sy = stats["spot_coords"]
            move_to_coordinates(sx, sy, log_widget, notify_telegram=True)
        else:
            send_telegram("⚠️ Aún no hay un Spot guardado.", with_keyboard=True)
        return

    # 13. Mover a coordenadas: soporta "/ir 125 130", "/move 125,130", "ir 125 130" o directamente "125 130"
    m = re.match(r'^(?:/ir|/move|/goto|ir|move|goto)?\s*(\d{1,3})\s*[,;:\s]\s*(\d{1,3})$', cmd_lower)
    if m:
        tx, ty = int(m.group(1)), int(m.group(2))
        if 0 <= tx <= 255 and 0 <= ty <= 255:
            move_to_coordinates(tx, ty, log_widget, notify_telegram=True)
        else:
            send_telegram("⚠️ Las coordenadas de MU deben estar entre 0 y 255 (ej: `/ir 125 130`).", with_keyboard=True)
        return

    send_telegram("❓ Comando no reconocido. Usa los botones del panel o escribe `/ayuda`.", with_keyboard=True)

# ----- Lector de Coordenadas (OCR) -----
def preprocess_coords_image(img, thresh_val=150, invert=True):
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    if invert:
        gray = cv2.bitwise_not(gray)
    _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
    return thresh

def find_split_x_and_clean(thresh):
    """
    Limpia manchas de los bordes y encuentra el punto exacto de separación (canal blanco)
    entre la coordenada X (izquierda) y la coordenada Y (derecha).
    """
    h, w = thresh.shape
    cleaned = thresh.copy()
    
    # En la imagen binarizada de Tesseract: fondo = 255 (blanco), dígitos = 0 (negro)
    fg = (255 - cleaned)
    num_labels, labels, stats_cc, centroids = cv2.connectedComponentsWithStats(fg, connectivity=8)
    
    valid_boxes = []
    for i in range(1, num_labels):
        x, y, bw, bh, area = stats_cc[i]
        touches_border = (x <= 2) or (y <= 2) or (x + bw >= w - 2) or (y + bh >= h - 2)
        # Si toca el borde, o no tiene altura/ancho de dígito normal, lo borramos a blanco
        if touches_border or area < 15 or bh < h * 0.25 or bw > w * 0.35:
            cleaned[labels == i] = 255
        else:
            valid_boxes.append((x, y, bw, bh))
            
    valid_boxes.sort(key=lambda b: b[0])
    
    # Si hay al menos 2 bloques de dígitos, buscamos el espacio horizontal más grande entre ellos
    if len(valid_boxes) >= 2:
        max_gap = -999
        split_x = w // 2
        curr_right = valid_boxes[0][0] + valid_boxes[0][2]
        for idx in range(len(valid_boxes) - 1):
            curr_right = max(curr_right, valid_boxes[idx][0] + valid_boxes[idx][2])
            next_left = valid_boxes[idx + 1][0]
            gap = next_left - curr_right
            if gap > max_gap:
                max_gap = gap
                split_x = (curr_right + next_left) // 2
        if max_gap >= 4:
            return cleaned, split_x

    # Fallback: buscar la columna más blanca en el tercio central de la imagen
    c_start = int(w * 0.25)
    c_end = int(w * 0.75)
    if c_end > c_start:
        col_ink = np.sum(cleaned[:, c_start:c_end] == 0, axis=0)
        split_x = c_start + int(np.argmin(col_ink))
    else:
        split_x = w // 2
    return cleaned, split_x

def read_coords_from_screen(sct):
    area = config.data["coords"].get("area")
    if not area or not TESSERACT_PATH:
        return None, "", None, None, None
    mon_dict = {
        "top": area["y1"],
        "left": area["x1"],
        "width": max(1, area["x2"] - area["x1"]),
        "height": max(1, area["y2"] - area["y1"])
    }
    img = np.array(sct.grab(mon_dict), dtype=np.uint8)
    thresh_val = int(config.data["coords"].get("threshold", 150))
    invert = bool(config.data["coords"].get("invert", True))
    raw_thresh = preprocess_coords_image(img, thresh_val, invert)
    
    thresh, split_x = find_split_x_and_clean(raw_thresh)
    
    custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
    try:
        # 1. Pasamos la imagen completa a Tesseract (mejor contexto de línea) y separamos cada dígito según su posición respecto a split_x
        boxes_str = pytesseract.image_to_boxes(raw_thresh, config=custom_config).strip()
        left_chars = []
        right_chars = []
        for line in boxes_str.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].isdigit():
                ch = parts[0]
                x1, x2 = int(parts[1]), int(parts[3])
                # Para el primer o último dígito que Tesseract suele expandir al borde, usamos el borde interno
                center_x = x2 - 5 if x1 <= 2 else (x1 + 5 if x2 >= raw_thresh.shape[1] - 2 else (x1 + x2) // 2)
                if center_x < split_x:
                    left_chars.append(ch)
                else:
                    right_chars.append(ch)
                    
        digits_x = "".join(left_chars)
        digits_y = "".join(right_chars)
        
        # 2. Fallback por mitades separadas si image_to_boxes no detectó ambos lados
        if not (digits_x and digits_y):
            left_part = cv2.copyMakeBorder(thresh[:, :split_x], 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
            right_part = cv2.copyMakeBorder(thresh[:, split_x:], 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
            if not digits_x:
                digits_x = "".join(re.findall(r'\d+', pytesseract.image_to_string(left_part, config=custom_config)))
            if not digits_y:
                digits_y = "".join(re.findall(r'\d+', pytesseract.image_to_string(right_part, config=custom_config)))
                
        raw_text = f"{digits_x} | {digits_y}"
        
        if digits_x and digits_y:
            cx, cy = int(digits_x), int(digits_y)
            if 0 <= cx <= 255 and 0 <= cy <= 255:
                return (cx, cy), raw_text, img, thresh, split_x
        return None, raw_text, img, thresh, split_x
    except Exception:
        return None, "", img, thresh, split_x

def coords_process(log_widget):
    global running, bot_paused, config, stats
    last_logged = None
    with mss.mss() as sct:
        while running:
            if bot_paused or not config.data["coords"].get("enabled", False) or not config.data["coords"].get("area"):
                time.sleep(1.0)
                continue
            if not TESSERACT_PATH:
                log_message("❌ OCR Error: No se encontró Tesseract-OCR instalado.", log_widget)
                time.sleep(5.0)
                continue
                
            coords, raw_text, _, _, _ = read_coords_from_screen(sct)
            if coords:
                stats["current_coords"] = coords
                if stats["spot_coords"] is None:
                    stats["spot_coords"] = coords
                    log_message(f"🧭 Spot fijado en coordenadas: X={coords[0]}, Y={coords[1]}", log_widget)
                elif coords != last_logged:
                    dx = coords[0] - stats["spot_coords"][0]
                    dy = coords[1] - stats["spot_coords"][1]
                    dist = int((dx**2 + dy**2)**0.5)
                    log_message(f"🧭 Coordenadas: ({coords[0]}, {coords[1]}) | Dist. del Spot: {dist} pasos (ΔX:{dx:+d}, ΔY:{dy:+d})", log_widget)
                    last_logged = coords
            time.sleep(1.5)

def calibrate_coords_window(log_widget):
    area = config.data["coords"].get("area")
    if not area:
        messagebox.showwarning("Falta Zona", "Primero marca la 'Zona Coordenadas' en la pantalla del juego.")
        return
    if not TESSERACT_PATH:
        messagebox.showerror("Error Tesseract", "No se encontró Tesseract-OCR en el sistema.")
        return

    def _run_calibrator():
        win_name = "Lector MU - Calibracion OCR (Presiona 'q' o ESC para salir)"
        cv2.namedWindow(win_name, cv2.WINDOW_AUTOSIZE)
        init_thresh = int(config.data["coords"].get("threshold", 150))
        init_inv = 1 if config.data["coords"].get("invert", True) else 0
        
        cv2.createTrackbar("Umbral", win_name, init_thresh, 255, lambda v: None)
        cv2.createTrackbar("Invertir", win_name, init_inv, 1, lambda v: None)
        
        log_message("🔍 Calibrador OCR abierto. Ajusta las barras y presiona 'q' en la ventana para guardar.", log_widget)
        
        with mss.mss() as sct:
            while True:
                try:
                    if cv2.getWindowProperty(win_name, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except:
                    break
                    
                t_val = cv2.getTrackbarPos("Umbral", win_name)
                inv_val = bool(cv2.getTrackbarPos("Invertir", win_name))
                
                config.data["coords"]["threshold"] = t_val
                config.data["coords"]["invert"] = inv_val
                
                coords, raw_text, img, thresh, split_x = read_coords_from_screen(sct)
                
                if img is not None and thresh is not None:
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    img_resized = cv2.resize(img_bgr, (thresh.shape[1], thresh.shape[0]))
                    thresh_bgr = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
                    
                    # Dibujamos la línea divisoria inteligente entre X e Y
                    if split_x is not None:
                        cv2.line(img_resized, (split_x, 0), (split_x, img_resized.shape[0]), (255, 200, 0), 2)
                        cv2.line(thresh_bgr, (split_x, 0), (split_x, thresh_bgr.shape[0]), (255, 0, 0), 2)
                    
                    combined = np.vstack([img_resized, thresh_bgr])
                    
                    # Panel inferior para mostrar el resultado de lectura
                    info_panel = np.zeros((75, max(combined.shape[1], 380), 3), dtype=np.uint8)
                    if combined.shape[1] < info_panel.shape[1]:
                        pad = info_panel.shape[1] - combined.shape[1]
                        combined = cv2.copyMakeBorder(combined, 0, 0, 0, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0))
                    
                    status_color = (0, 255, 0) if coords else (0, 165, 255)
                    parsed_str = f"X={coords[0]} | Y={coords[1]}" if coords else "Sin detectar (Ajusta Umbral)"
                    
                    cv2.putText(info_panel, f"OCR Mitades: '{raw_text}'", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
                    cv2.putText(info_panel, f"Detectado: {parsed_str}", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)
                    
                    final_view = np.vstack([combined, info_panel])
                    cv2.imshow(win_name, final_view)
                
                key = cv2.waitKey(250) & 0xFF
                if key == ord('q') or key == 27:
                    break
                    
        cv2.destroyAllWindows()
        config.save()
        log_message(f"✅ Calibración OCR guardada (Umbral: {config.data['coords']['threshold']}, Invertir: {config.data['coords']['invert']}).", log_widget)

    threading.Thread(target=_run_calibrator, daemon=True).start()

# ----- Editor de Colores -----
class ColorEditor(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Forja de Colores (HSV)")
        self.geometry("700x500")
        self.configure(bg=MU_BG)
        self.grab_set() 
        
        self.entries = {}
        
        title_lbl = tk.Label(self, text="🛡️ FORJA DE COLORES 🛡️", font=MU_TITLE_FONT, bg=MU_BG, fg=MU_FG)
        title_lbl.pack(pady=10)
        
        canvas = tk.Canvas(self, bg=MU_FRAME_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=MU_FRAME_BG)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)
        
        row = 0
        headers = ["Item", "Preview", "Mínimo (H,S,V)", "Máximo (H,S,V)", "Acción"]
        for col, text in enumerate(headers):
            tk.Label(scrollable_frame, text=text, font=MU_FONT, bg=MU_FRAME_BG, fg="#FFFFFF").grid(row=row, column=col, padx=5, pady=5)
        row += 1
        
        self.items_to_edit = {}
        for k, v in config.data["pickup_colors"].items():
            self.items_to_edit[f"Joya: {k}"] = (k, v)
        self.items_to_edit["Enemigo (Ataque)"] = ("attack_color", config.data["attack_color"])
        
        for name, (dict_key, conf) in self.items_to_edit.items():
            frame_name = tk.Frame(scrollable_frame, bg=MU_FRAME_BG)
            frame_name.grid(row=row, column=0, padx=5, pady=2, sticky="w")
            tk.Label(frame_name, text=name, font=MU_FONT, bg=MU_FRAME_BG, fg=MU_FG).pack(anchor="w")
            
            notify_var = None
            if "Pickup" in dict_key or "Joya" in name:
                notify_var = tk.BooleanVar(value=conf.get("notify", False))
                tk.Checkbutton(frame_name, text="📱 Telegram", variable=notify_var, bg=MU_FRAME_BG, fg="#00FF00", selectcolor=MU_ACCENT).pack(anchor="w")
            
            preview = tk.Label(scrollable_frame, text="      ", relief="sunken", width=6, borderwidth=2)
            preview.grid(row=row, column=1, padx=5, pady=2)
            
            frame_lower = tk.Frame(scrollable_frame, bg=MU_FRAME_BG)
            frame_lower.grid(row=row, column=2, padx=5, pady=2)
            hl = tk.Entry(frame_lower, width=4, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG); hl.insert(0, str(conf["lower"][0])); hl.pack(side=tk.LEFT)
            sl = tk.Entry(frame_lower, width=4, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG); sl.insert(0, str(conf["lower"][1])); sl.pack(side=tk.LEFT)
            vl = tk.Entry(frame_lower, width=4, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG); vl.insert(0, str(conf["lower"][2])); vl.pack(side=tk.LEFT)
            
            frame_upper = tk.Frame(scrollable_frame, bg=MU_FRAME_BG)
            frame_upper.grid(row=row, column=3, padx=5, pady=2)
            hu = tk.Entry(frame_upper, width=4, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG); hu.insert(0, str(conf["upper"][0])); hu.pack(side=tk.LEFT)
            su = tk.Entry(frame_upper, width=4, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG); su.insert(0, str(conf["upper"][1])); su.pack(side=tk.LEFT)
            vu = tk.Entry(frame_upper, width=4, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG); vu.insert(0, str(conf["upper"][2])); vu.pack(side=tk.LEFT)
            
            btn = tk.Button(scrollable_frame, text="🎨 Elegir", font=MU_FONT, bg=MU_BTN_BG, fg=MU_BTN_FG, activebackground=MU_ACCENT, activeforeground=MU_FG,
                            command=lambda n=name, l=(hl,sl,vl), u=(hu,su,vu), p=preview: self.pick_color(n, l, u, p))
            btn.grid(row=row, column=4, padx=5, pady=2)
            
            self.entries[name] = {"lower": (hl,sl,vl), "upper": (hu,su,vu), "preview": preview, "conf_ref": conf, "notify_var": notify_var}
            
            for e in (hl,sl,vl,hu,su,vu):
                e.bind("<KeyRelease>", lambda event, p=preview, l=(hl,sl,vl), u=(hu,su,vu): self.update_preview(p, l, u))
            self.update_preview(preview, (hl,sl,vl), (hu,su,vu))
            row += 1
            
        bottom_frame = tk.Frame(self, bg=MU_BG)
        bottom_frame.pack(side="bottom", fill="x", pady=10)
        tk.Button(bottom_frame, text="Guardar en el Baúl (Cerrar)", font=("Georgia", 11, "bold"), bg="#556B2F", fg="#FFFFFF", activebackground="#6B8E23", command=self.save_and_close).pack(pady=5)
        
    def update_preview(self, preview_label, lower_entries, upper_entries):
        try:
            h = (int(lower_entries[0].get()) + int(upper_entries[0].get())) // 2
            s = (int(lower_entries[1].get()) + int(upper_entries[1].get())) // 2
            v = (int(lower_entries[2].get()) + int(upper_entries[2].get())) // 2
            hsv = np.uint8([[[h, s, v]]])
            bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]
            hex_color = f"#{bgr[2]:02x}{bgr[1]:02x}{bgr[0]:02x}"
            preview_label.config(bg=hex_color)
        except ValueError:
            pass 
            
    def pick_color(self, name, lower_entries, upper_entries, preview_label):
        color = colorchooser.askcolor(title=f"Forjar color para {name}")
        if color[0] is not None:
            r, g, b = int(color[0][0]), int(color[0][1]), int(color[0][2])
            hsv = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0][0]
            h = hsv[0]
            h_low = max(0, int(h) - 10)
            h_up = min(179, int(h) + 10)
            
            lower_entries[0].delete(0, tk.END); lower_entries[0].insert(0, str(h_low))
            lower_entries[1].delete(0, tk.END); lower_entries[1].insert(0, "100")
            lower_entries[2].delete(0, tk.END); lower_entries[2].insert(0, "100")
            
            upper_entries[0].delete(0, tk.END); upper_entries[0].insert(0, str(h_up))
            upper_entries[1].delete(0, tk.END); upper_entries[1].insert(0, "255")
            upper_entries[2].delete(0, tk.END); upper_entries[2].insert(0, "255")
            self.update_preview(preview_label, lower_entries, upper_entries)

    def save_and_close(self):
        try:
            for name, data in self.entries.items():
                hl, sl, vl = int(data["lower"][0].get()), int(data["lower"][1].get()), int(data["lower"][2].get())
                hu, su, vu = int(data["upper"][0].get()), int(data["upper"][1].get()), int(data["upper"][2].get())
                data["conf_ref"]["lower"] = [hl, sl, vl]
                data["conf_ref"]["upper"] = [hu, su, vu]
                if data["notify_var"]:
                    data["conf_ref"]["notify"] = data["notify_var"].get()
            config.save()
            messagebox.showinfo("Guardado", "¡Colores forjados exitosamente!")
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Los valores deben ser números enteros.")

# ----- Utilidades de UI -----
def create_mu_button(parent, text, command, bg=MU_BTN_BG):
    return tk.Button(parent, text=text, command=command, font=MU_FONT, bg=bg, fg=MU_BTN_FG, 
                     activebackground=MU_ACCENT, activeforeground=MU_FG, relief="raised", bd=3)

def select_area(parent):
    selection = {}
    top = tk.Toplevel(parent)
    top.attributes('-fullscreen', True)
    top.attributes('-alpha', 0.4)
    canvas = tk.Canvas(top, cursor="cross", bg="black")
    canvas.pack(fill=tk.BOTH, expand=True)

    start_x = None; start_y = None; rect = None

    def on_button_press(event):
        nonlocal start_x, start_y, rect
        start_x = event.x; start_y = event.y
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='#FF0000', width=3)

    def on_move(event):
        if rect: canvas.coords(rect, start_x, start_y, event.x, event.y)

    def on_button_release(event):
        nonlocal selection
        selection = {"x1": min(start_x, event.x), "y1": min(start_y, event.y), "x2": max(start_x, event.x), "y2": max(start_y, event.y)}
        top.destroy()

    canvas.bind("<ButtonPress-1>", on_button_press)
    canvas.bind("<B1-Motion>", on_move)
    canvas.bind("<ButtonRelease-1>", on_button_release)
    top.grab_set()
    top.wait_window()
    return selection

def log_message(msg, log_widget):
    timestamp = time.strftime('%H:%M:%S')
    log_widget.after(0, lambda: update_log(log_widget, f"[{timestamp}] {msg}\n"))

def update_log(widget, msg):
    widget.config(state=tk.NORMAL)
    widget.insert(tk.END, msg)
    widget.see(tk.END)
    widget.config(state=tk.DISABLED)

# ----- Ventana Principal -----
class Application(tk.Tk):
    def __init__(self):
        global app_instance
        super().__init__()
        app_instance = self
        self.title("MU Online Helper - Legend V20 (5-Priority Engine & Telegram Remote)")
        self.geometry("980x890")
        self.configure(bg=MU_BG)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.buff_var = tk.BooleanVar(value=config.data.get("buff_enabled", True))
        self.pickup_var = tk.BooleanVar(value=config.data.get("pickup_enabled", False))
        self.attack_var = tk.BooleanVar(value=config.data.get("attack_enabled", False))
        self.coords_var = tk.BooleanVar(value=config.data["coords"].get("enabled", False))
        
        self.create_widgets()
        keyboard.add_hotkey("F5", lambda: start_activity(self.log_text, self.cooldown_label))
        keyboard.add_hotkey("F6", lambda: stop_activity(self.log_text))
        
        start_telegram_listener(self.log_text)
        self.update_stats_ui()

    def refresh_ui_from_config(self):
        """Actualiza los controles visuales cuando un comando de Telegram modifica config.data."""
        self.buff_var.set(config.data.get("buff_enabled", True))
        self.pickup_var.set(config.data.get("pickup_enabled", False))
        self.attack_var.set(config.data.get("attack_enabled", False))
        self.coords_var.set(config.data["coords"].get("enabled", False))
        self.monitor_var.set(config.data["monitor"].get("enabled", False))
        self.cooldown_entry.delete(0, tk.END)
        self.cooldown_entry.insert(0, str(config.data.get("cooldown", 15)))
        self.mon_min_entry.delete(0, tk.END)
        self.mon_min_entry.insert(0, str(config.data["monitor"].get("interval_minutes", 30)))
        self.create_pickup_objects_ui()
        self.update_config_status()

    def create_widgets(self):
        title_lbl = tk.Label(self, text="⚔️ MU ONLINE AUTO-HELPER ⚔️", font=("Georgia", 16, "bold"), bg=MU_BG, fg=MU_FG)
        title_lbl.pack(pady=10)

        config_frame = tk.Frame(self, bg=MU_BG)
        config_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=5)

        style_lf = {"bg": MU_FRAME_BG, "fg": MU_FG, "font": MU_FONT, "bd": 2, "relief": "ridge"}
        style_cb = {"bg": MU_FRAME_BG, "fg": MU_FG, "font": MU_FONT, "selectcolor": MU_ACCENT, "activebackground": MU_FRAME_BG, "activeforeground": MU_FG}

        # ---- BUFF FRAME ----
        buff_frame = tk.LabelFrame(config_frame, text=" Aura & Party ", **style_lf)
        buff_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        
        tk.Checkbutton(buff_frame, text="Activar Magias", variable=self.buff_var, command=self.update_flags, **style_cb).pack(pady=5)
        self.skill_button = create_mu_button(buff_frame, "Marcar Skill", self.add_skill_area)
        self.skill_button.pack(pady=2)
        
        self.skill_listbox = tk.Listbox(buff_frame, height=3, bg=MU_LIST_BG, fg=MU_FG, bd=0)
        self.skill_listbox.pack(pady=2, fill=tk.BOTH, expand=True, padx=5)
        
        self.player_button = create_mu_button(buff_frame, "Marcar Party", self.add_player_area)
        self.player_button.pack(pady=2)
        self.player_listbox = tk.Listbox(buff_frame, height=3, bg=MU_LIST_BG, fg=MU_FG, bd=0)
        self.player_listbox.pack(pady=2, fill=tk.BOTH, expand=True, padx=5)

        # ---- PICKUP FRAME ----
        pickup_frame = tk.LabelFrame(config_frame, text=" Loot (Joyas) ", **style_lf)
        pickup_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        
        tk.Checkbutton(pickup_frame, text="Activar Recolección", variable=self.pickup_var, command=self.update_flags, **style_cb).pack(pady=5)
        self.pickup_area_button = create_mu_button(pickup_frame, "Zona de Suelo", self.add_pickup_area)
        self.pickup_area_button.pack(pady=5)
        
        self.pickup_objects_frame = tk.LabelFrame(pickup_frame, text=" Inventario a buscar ", **style_lf)
        self.pickup_objects_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        self.create_pickup_objects_ui()

        # ---- ATTACK & COOLDOWN & MONITOR & COORDS FRAME ----
        right_frame = tk.Frame(config_frame, bg=MU_BG)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)

        attack_frame = tk.LabelFrame(right_frame, text=" Batalla ", **style_lf)
        attack_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Checkbutton(attack_frame, text="Activar Combate", variable=self.attack_var, command=self.update_flags, **style_cb).pack(pady=2)
        self.attack_area_button = create_mu_button(attack_frame, "Zona de Caza", self.add_attack_area)
        self.attack_area_button.pack(pady=5)

        cooldown_frame = tk.LabelFrame(right_frame, text=" Cooldown Auras ", **style_lf)
        cooldown_frame.pack(fill=tk.X, pady=(0, 5))
        cd_inner = tk.Frame(cooldown_frame, bg=MU_FRAME_BG)
        cd_inner.pack(pady=2)
        self.cooldown_entry = tk.Entry(cd_inner, width=5, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG, font=MU_FONT)
        self.cooldown_entry.pack(side=tk.LEFT, padx=5)
        self.cooldown_entry.insert(0, str(config.data["cooldown"]))
        create_mu_button(cd_inner, "Fijar", self.apply_cooldown).pack(side=tk.LEFT)
        self.cooldown_label = tk.Label(cooldown_frame, text="Espera: --", bg=MU_FRAME_BG, fg="#00FF00", font=MU_FONT)
        self.cooldown_label.pack(pady=2)

        # ---- MONITOR FRAME ----
        monitor_frame = tk.LabelFrame(right_frame, text=" 📸 Monitor Telegram ", **style_lf)
        monitor_frame.pack(fill=tk.X)
        self.monitor_var = tk.BooleanVar(value=config.data["monitor"]["enabled"])
        tk.Checkbutton(monitor_frame, text="Activar Monitor", variable=self.monitor_var, command=self.apply_monitor, **style_cb).pack(pady=2)
        
        btn_frames = tk.Frame(monitor_frame, bg=MU_FRAME_BG)
        btn_frames.pack(pady=2)
        
        self.monitor_btn_button = create_mu_button(btn_frames, "Botón Inventario", self.add_monitor_btn_area)
        self.monitor_btn_button.pack(side=tk.LEFT, padx=2)
        
        self.monitor_area_button = create_mu_button(btn_frames, "Área de Foto", self.add_monitor_area)
        self.monitor_area_button.pack(side=tk.LEFT, padx=2)
        
        mon_inner = tk.Frame(monitor_frame, bg=MU_FRAME_BG)
        mon_inner.pack(pady=2)
        tk.Label(mon_inner, text="Intervalo (Minutos):", bg=MU_FRAME_BG, fg=MU_FG).pack(side=tk.LEFT)
        self.mon_min_entry = tk.Entry(mon_inner, width=4, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG)
        self.mon_min_entry.pack(side=tk.LEFT, padx=5)
        self.mon_min_entry.insert(0, str(config.data["monitor"]["interval_minutes"]))
        
        create_mu_button(monitor_frame, "Fijar Intervalo", self.apply_monitor).pack(pady=5)

        # ---- COORDS & GPS FRAME ----
        coords_frame = tk.LabelFrame(right_frame, text=" 🧭 Coordenadas & Movimiento (OCR) ", **style_lf)
        coords_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Checkbutton(coords_frame, text="Activar Lector", variable=self.coords_var, command=self.update_flags, **style_cb).pack(pady=2)

        coords_btns = tk.Frame(coords_frame, bg=MU_FRAME_BG)
        coords_btns.pack(pady=2)
        self.coords_area_button = create_mu_button(coords_btns, "Zona Coords", self.add_coords_area)
        self.coords_area_button.pack(side=tk.LEFT, padx=2)
        self.char_center_button = create_mu_button(coords_btns, "📍 Centro PJ", self.add_char_center_area)
        self.char_center_button.pack(side=tk.LEFT, padx=2)
        create_mu_button(coords_btns, "🔍 Calibrar OCR", lambda: calibrate_coords_window(self.log_text), bg="#8B6508").pack(side=tk.LEFT, padx=2)

        walk_frame = tk.Frame(coords_frame, bg=MU_FRAME_BG)
        walk_frame.pack(pady=4)
        tk.Label(walk_frame, text="X:", bg=MU_FRAME_BG, fg=MU_FG).pack(side=tk.LEFT)
        self.goto_x_entry = tk.Entry(walk_frame, width=4, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG)
        self.goto_x_entry.pack(side=tk.LEFT, padx=2)
        tk.Label(walk_frame, text="Y:", bg=MU_FRAME_BG, fg=MU_FG).pack(side=tk.LEFT)
        self.goto_y_entry = tk.Entry(walk_frame, width=4, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG)
        self.goto_y_entry.pack(side=tk.LEFT, padx=2)
        create_mu_button(walk_frame, "🚶 Ir", self.gui_move_to_coords, bg="#006400").pack(side=tk.LEFT, padx=3)
        create_mu_button(walk_frame, "⏹", cancel_coordinate_movement, bg="#8B0000").pack(side=tk.LEFT, padx=2)
        create_mu_button(walk_frame, "🎯 Calibrar Ejes", lambda: calibrate_movement_axes(self.log_text, False), bg="#1d5f8c").pack(side=tk.LEFT, padx=3)
        
        # ---- ESTADÍSTICAS FRAME ----
        stats_frame = tk.LabelFrame(self, text=" 📊 Estadísticas de Farmeo ", **style_lf)
        stats_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self.time_lbl = tk.Label(stats_frame, text="⏳ Tiempo Farmeando: 00:00:00", bg=MU_FRAME_BG, fg="#00FFFF", font=("Consolas", 11, "bold"))
        self.time_lbl.pack(pady=2)

        self.coords_lbl = tk.Label(stats_frame, text="📍 Coordenadas: -- | Spot: --", bg=MU_FRAME_BG, fg="#FFA500", font=("Consolas", 10, "bold"))
        self.coords_lbl.pack(pady=2)
        
        self.coords_lbl = tk.Label(stats_frame, text="📍 Coordenadas: -- | Spot: --", bg=MU_FRAME_BG, fg="#FFA500", font=("Consolas", 10, "bold"))
        self.coords_lbl.pack(pady=2)
        
        self.items_lbl = tk.Label(stats_frame, text="Esperando inicio...", bg=MU_FRAME_BG, fg=MU_FG, font=("Consolas", 10))
        self.items_lbl.pack(pady=2)

        # ---- CONSOLA LOG ----
        self.log_text = tk.Text(self, height=8, bg=MU_LIST_BG, fg="#00FF00", font=("Consolas", 10), bd=2, relief="sunken")
        self.log_text.pack(fill=tk.BOTH, padx=15, pady=5, expand=True)
        self.log_text.insert(tk.END, ">>> Sistema V20 en línea. Prioridades: 1° Pickup > 2° Caminar > 3° Buff > 4° Ataque > 5° Foto.\n")
        self.log_text.config(state=tk.DISABLED)

        # ---- BOTONES GLOBALES ----
        bottom_frame = tk.Frame(self, bg=MU_BG)
        bottom_frame.pack(side=tk.BOTTOM, pady=10)
        
        create_mu_button(bottom_frame, "💾 Guardar Perfil", self.save_config).pack(side=tk.LEFT, padx=5)
        create_mu_button(bottom_frame, "🎨 Forja de Colores", lambda: ColorEditor(self), bg="#8B6508").pack(side=tk.LEFT, padx=5)
        create_mu_button(bottom_frame, "📱 Telegram", lambda: TelegramConfig(self), bg="#1d5f8c").pack(side=tk.LEFT, padx=5)
        create_mu_button(bottom_frame, "▶ INICIAR (F5)", lambda: start_activity(self.log_text, self.cooldown_label), bg="#006400").pack(side=tk.LEFT, padx=5)
        create_mu_button(bottom_frame, "⏹ DETENER (F6)", lambda: stop_activity(self.log_text), bg="#8B0000").pack(side=tk.LEFT, padx=5)

        self.update_config_status()

    def gui_move_to_coords(self):
        try:
            tx = int(self.goto_x_entry.get().strip())
            ty = int(self.goto_y_entry.get().strip())
            if not (0 <= tx <= 255 and 0 <= ty <= 255):
                raise ValueError
            move_to_coordinates(tx, ty, self.log_text, notify_telegram=False)
        except ValueError:
            messagebox.showerror("Coordenadas inválidas", "Ingresa valores enteros entre 0 y 255 para X e Y.")

    def update_stats_ui(self):
        global stats, running
        if running and stats["start_time"]:
            elapsed = int(time.time() - stats["start_time"])
            hrs, rem = divmod(elapsed, 3600)
            mins, secs = divmod(rem, 60)
            pause_tag = " [PAUSADO]" if manual_pause else ""
            self.time_lbl.config(text=f"⏳ Tiempo Farmeando: {hrs:02d}:{mins:02d}:{secs:02d}{pause_tag}")
            
            if stats["current_coords"]:
                cx, cy = stats["current_coords"]
                sx, sy = stats["spot_coords"] if stats["spot_coords"] else (cx, cy)
                self.coords_lbl.config(text=f"📍 Coordenadas: ({cx}, {cy}) | Spot Fijado: ({sx}, {sy})")
            else:
                self.coords_lbl.config(text="📍 Coordenadas: -- | Spot: --")
            
            if stats["items"]:
                items_str = " | ".join([f"{k.capitalize()}: {v}" for k, v in stats["items"].items()])
                self.items_lbl.config(text=items_str)
            else:
                self.items_lbl.config(text="Buscando joyas...")
        elif not running:
            self.time_lbl.config(text="⏳ Sistema Detenido")

        if stats["current_coords"]:
            cx, cy = stats["current_coords"]
            sx, sy = stats["spot_coords"] if stats["spot_coords"] else (cx, cy)
            target_str = f" | 🚶 Ir a: {stats['target_coords']}" if stats.get("target_coords") else ""
            self.coords_lbl.config(text=f"📍 Coordenadas: ({cx}, {cy}) | Spot Fijado: ({sx}, {sy}){target_str}")
        else:
            self.coords_lbl.config(text="📍 Coordenadas: -- | Spot: --")
            
        self.after(1000, self.update_stats_ui)

    def update_flags(self):
        config.data["buff_enabled"] = self.buff_var.get()
        config.data["pickup_enabled"] = self.pickup_var.get()
        config.data["attack_enabled"] = self.attack_var.get()
        config.data["coords"]["enabled"] = self.coords_var.get()
        config.save()
        self.update_config_status()

    def apply_monitor(self):
        try:
            config.data["monitor"]["enabled"] = self.monitor_var.get()
            config.data["monitor"]["interval_minutes"] = int(self.mon_min_entry.get())
            config.save()
            log_message(f"Monitor configurado: Cada {config.data['monitor']['interval_minutes']}m", self.log_text)
        except ValueError:
            messagebox.showerror("Error", "Los minutos deben ser un número.")

    def create_pickup_objects_ui(self):
        for widget in self.pickup_objects_frame.winfo_children(): widget.destroy()
            
        list_frame = tk.Frame(self.pickup_objects_frame, bg=MU_FRAME_BG)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        for obj_name, obj_conf in config.data["pickup_colors"].items():
            var = tk.BooleanVar(value=obj_conf.get("active", True))
            cb = tk.Checkbutton(list_frame, text=obj_name.capitalize(), variable=var,
                                bg=MU_FRAME_BG, fg=MU_FG, selectcolor=MU_ACCENT, activebackground=MU_FRAME_BG, activeforeground=MU_FG,
                                command=lambda name=obj_name, v=var: self.update_pickup_object(name, v))
            cb.pack(anchor="w")
            
        create_mu_button(self.pickup_objects_frame, "➕ Nuevo Item", self.add_new_item, bg="#333333").pack(pady=5)

    def add_new_item(self):
        new_item = simpledialog.askstring("Forjar Item", "Nombre de la Joya/Item (ej: bless):")
        if new_item:
            new_item = new_item.strip().lower()
            if not new_item: return
            if new_item in config.data["pickup_colors"]:
                messagebox.showwarning("Atención", "Esa joya ya existe en tu inventario.")
                return
            config.data["pickup_colors"][new_item] = {"lower": [0, 100, 100], "upper": [179, 255, 255], "active": True, "notify": True}
            config.save()
            self.create_pickup_objects_ui()
            log_message(f"Item '{new_item}' agregado.", self.log_text)

    def update_pickup_object(self, name, var):
        config.data["pickup_colors"][name]["active"] = var.get()
        config.save()

    def add_skill_area(self):
        sel = select_area(self)
        if sel:
            config.data["buff_skills"].append(sel)
            self.skill_listbox.insert(tk.END, f"Skill {len(config.data['buff_skills'])}")
            self.update_config_status()

    def add_player_area(self):
        sel = select_area(self)
        if sel:
            config.data["buff_players"].append(sel)
            self.player_listbox.insert(tk.END, f"Party {len(config.data['buff_players'])}")
            self.update_config_status()

    def add_pickup_area(self):
        sel = select_area(self)
        if sel: config.data["pickup_area"] = sel; self.update_config_status()
            
    def add_attack_area(self):
        sel = select_area(self)
        if sel: config.data["attack_area"] = sel; self.update_config_status()

    def add_monitor_area(self):
        sel = select_area(self)
        if sel: config.data["monitor"]["area"] = sel; self.update_config_status()

    def add_monitor_btn_area(self):
        sel = select_area(self)
        if sel: 
            config.data["monitor"]["button_area"] = sel
            self.update_config_status()
            log_message("Botón de inventario marcado.", self.log_text)

    def add_coords_area(self):
        sel = select_area(self)
        if sel:
            config.data["coords"]["area"] = sel
            self.update_config_status()
            log_message("🧭 Zona de coordenadas marcada.", self.log_text)

    def add_char_center_area(self):
        sel = select_area(self)
        if sel:
            config.data["coords"]["char_center"] = sel
            self.update_config_status()
            cx = (sel["x1"] + sel["x2"]) // 2
            cy = (sel["y1"] + sel["y2"]) // 2
            log_message(f"📍 Centro del PJ marcado en pantalla: ({cx}, {cy}).", self.log_text)

    def apply_cooldown(self):
        try:
            config.data["cooldown"] = int(self.cooldown_entry.get())
            config.save()
            self.update_config_status()
            log_message(f"Cooldown actualizado a {config.data['cooldown']}s", self.log_text)
        except: pass

    def save_config(self):
        self.apply_monitor() 
        config.save()
        log_message("Configuración guardada en el baúl (config.json)", self.log_text)

    def update_config_status(self):
        self.skill_button.config(bg="#006400" if config.data["buff_skills"] else MU_BTN_BG)
        self.player_button.config(bg="#006400" if config.data["buff_players"] else MU_BTN_BG)
        self.pickup_area_button.config(bg="#006400" if config.data.get("pickup_area") else MU_BTN_BG)
        self.attack_area_button.config(bg="#006400" if config.data.get("attack_area") else MU_BTN_BG)
        self.monitor_area_button.config(bg="#006400" if config.data["monitor"].get("area") else MU_BTN_BG)
        self.monitor_btn_button.config(bg="#006400" if config.data["monitor"].get("button_area") else MU_BTN_BG)
        self.coords_area_button.config(bg="#006400" if config.data["coords"].get("area") else MU_BTN_BG)
        self.char_center_button.config(bg="#006400" if config.data["coords"].get("char_center") else MU_BTN_BG)

    def on_close(self):
        cancel_coordinate_movement()
        stop_activity(self.log_text)
        self.destroy()

def start_activity(log_widget, cd_label):
    global running, buff_thread, pickup_thread, attack_thread, monitor_thread, coords_thread, stats
    global pickup_active, moving_to_coords, buff_active, photo_active, manual_pause
    
    if config.data["monitor"].get("enabled", False) and not config.data["monitor"].get("button_area"):
        log_message("❌ Error: Monitor activado pero falta marcar el 'Botón Inventario'.", log_widget)
        return

    if config.data["coords"].get("enabled", False) and not config.data["coords"].get("area"):
        log_message("❌ Error: Lector de coordenadas activado pero falta marcar la 'Zona Coords'.", log_widget)
        return
        
    if not running:
        running = True
        pickup_active = False
        buff_active = False
        photo_active = False
        manual_pause = False
        stats["start_time"] = time.time()
        stats["spot_coords"] = None
        stats["current_coords"] = None
        buff_thread = threading.Thread(target=buffing_process, args=(log_widget, cd_label), daemon=True); buff_thread.start()
        pickup_thread = threading.Thread(target=pickup_process, args=(log_widget,), daemon=True); pickup_thread.start()
        attack_thread = threading.Thread(target=attack_process, args=(log_widget,), daemon=True); attack_thread.start()
        monitor_thread = threading.Thread(target=monitor_process, args=(log_widget,), daemon=True); monitor_thread.start()
        coords_thread = threading.Thread(target=coords_process, args=(log_widget,), daemon=True); coords_thread.start()
        
        log_message("=== MACRO INICIADA (F5) [Motor de 5 Prioridades Activo] ===", log_widget)
        if config.data["telegram"]["enabled"]:
            send_telegram("⚔️ Bot iniciado (Prioridades: 1° Pickup > 2° Caminar > 3° Buff > 4° Ataque > 5° Foto).", with_keyboard=True)

def stop_activity(log_widget):
    global running, pickup_active, buff_active, photo_active, manual_pause
    cancel_coordinate_movement()
    if running:
        running = False
        pickup_active = False
        buff_active = False
        photo_active = False
        manual_pause = False
        log_message("=== MACRO DETENIDA (F6) ===", log_widget)
        if config.data["telegram"]["enabled"]:
            send_telegram("⏹ Bot detenido.", with_keyboard=True)

if __name__ == "__main__":
    app = Application()
    app.mainloop()
