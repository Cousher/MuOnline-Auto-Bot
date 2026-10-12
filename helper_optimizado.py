import tkinter as tk
from tkinter import messagebox, colorchooser, simpledialog
import threading, time, json, os
import cv2
import numpy as np
import pydirectinput
import keyboard
import mss
import requests

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
    "items": {}
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
                "key": "v",
                "area": None
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
        if "monitor" not in self.data: self.data["monitor"] = {"enabled": False, "interval_minutes": 30, "key": "v", "area": None}

    def load(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                loaded_data = json.load(f)
                self.data.update(loaded_data)

    def save(self):
        with open(self.config_file, "w") as f:
            json.dump(self.data, f, indent=4)

config = Config()

# ----- Funciones Telegram -----
def send_telegram_async(msg):
    token = config.data["telegram"]["token"]
    chat_id = config.data["telegram"]["chat_id"]
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=5)
        except:
            pass

def send_telegram(msg):
    threading.Thread(target=send_telegram_async, args=(msg,), daemon=True).start()

def send_telegram_photo_async(photo_path):
    token = config.data["telegram"]["token"]
    chat_id = config.data["telegram"]["chat_id"]
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            with open(photo_path, "rb") as f:
                requests.post(url, data={"chat_id": chat_id, "caption": "📸 Estado del Inventario."}, files={"photo": f}, timeout=15)
        except:
            pass
        finally:
            try: os.remove(photo_path)
            except: pass

# ----- Configuración de Telegram (UI) -----
class TelegramConfig(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📱 Notificaciones Telegram")
        self.geometry("450x350")
        self.configure(bg=MU_BG)
        self.grab_set()

        tk.Label(self, text="CONFIGURACIÓN DE TELEGRAM", font=MU_TITLE_FONT, bg=MU_BG, fg=MU_FG).pack(pady=10)
        
        info = "1. Busca a @BotFather en Telegram y crea un bot.\n2. Copia el Token aquí.\n3. Busca a @userinfobot para obtener tu Chat ID."
        tk.Label(self, text=info, bg=MU_BG, fg="#AAAAAA", justify=tk.LEFT).pack(pady=5)

        self.enabled_var = tk.BooleanVar(value=config.data["telegram"]["enabled"])
        tk.Checkbutton(self, text="Activar Notificaciones", variable=self.enabled_var, bg=MU_BG, fg=MU_FG, selectcolor=MU_ACCENT).pack(pady=5)

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
        
        create_mu_button(btn_frame, "Probar Mensaje", self.test_message, bg="#006400").pack(side=tk.LEFT, padx=10)
        create_mu_button(btn_frame, "Guardar", self.save_config).pack(side=tk.LEFT, padx=10)

    def test_message(self):
        token = self.token_entry.get().strip()
        chat_id = self.chatid_entry.get().strip()
        if not token or not chat_id:
            messagebox.showwarning("Faltan datos", "Completa el Token y el Chat ID.")
            return
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            res = requests.post(url, data={"chat_id": chat_id, "text": "¡Hola! 🤖 Las notificaciones de tu Bot de MU Online están funcionando correctamente."})
            if res.status_code == 200:
                messagebox.showinfo("Éxito", "Mensaje de prueba enviado. Revisa tu Telegram.")
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

# ----- Funciones en Hilos (Lógica del Bot) -----
running = False
bot_paused = False # Para el semáforo de las fotos

def buffing_process(log_widget, cooldown_label):
    global running, config, bot_paused
    while running:
        if bot_paused: 
            time.sleep(0.5); continue
        if not config.data.get("buff_enabled", True):
            time.sleep(0.5); continue
            
        start_time = time.time()
        if config.data["buff_skills"] and config.data["buff_players"]:
            for i, skill_area in enumerate(config.data["buff_skills"]):
                if not running or bot_paused: break
                cx = (skill_area["x1"] + skill_area["x2"]) // 2
                cy = (skill_area["y1"] + skill_area["y2"]) // 2
                pydirectinput.moveTo(cx, cy)
                time.sleep(0.05)
                pydirectinput.mouseDown(button='left')
                time.sleep(0.1)
                pydirectinput.mouseUp(button='left')
                log_message(f"Buff: Skill {i+1} lanzado", log_widget)
                time.sleep(0.1)
                for j, player_area in enumerate(config.data["buff_players"]):
                    if not running or bot_paused: break
                    cx_p = (player_area["x1"] + player_area["x2"]) // 2
                    cy_p = (player_area["y1"] + player_area["y2"]) // 2
                    pydirectinput.moveTo(cx_p, cy_p)
                    time.sleep(0.05)
                    pydirectinput.mouseDown(button='right')
                    time.sleep(0.1)
                    pydirectinput.mouseUp(button='right')
                    log_message(f"Buff: Jugador {j+1} buffeado", log_widget)
                    time.sleep(0.1)
            elapsed = time.time() - start_time
            cd = config.data["cooldown"]
            wait_time = max(5, cd - elapsed)
            remaining = int(wait_time)
            while remaining > 0 and running:
                cooldown_label.after(0, lambda r=remaining: cooldown_label.config(text=f"Cooldown: {r} s"))
                time.sleep(1)
                remaining -= 1
        else:
            time.sleep(1)

def pickup_process(log_widget):
    global running, config, stats, bot_paused
    with mss.mss() as sct:
        while running:
            if bot_paused: 
                time.sleep(0.5); continue
            if not config.data.get("pickup_area") or not config.data.get("pickup_enabled", False):
                time.sleep(1)
                continue
            area = config.data["pickup_area"]
            monitor = {"top": area["y1"], "left": area["x1"], "width": area["x2"] - area["x1"], "height": area["y2"] - area["y1"]}
            img = np.array(sct.grab(monitor))
            bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            clicks_to_make = []
            
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
                    clicks_to_make.append((center_x, center_y, obj_name))
            if clicks_to_make:
                for cx, cy, item in clicks_to_make:
                    if not running or bot_paused: break
                    pydirectinput.moveTo(cx, cy)
                    time.sleep(0.05)
                    pydirectinput.click(button='left')
                    log_message(f"Pickup: Recogiendo {item}", log_widget)
                    
                    if item not in stats["items"]: stats["items"][item] = 0
                    stats["items"][item] += 1
                    
                    if config.data["telegram"]["enabled"] and config.data["pickup_colors"][item].get("notify", False):
                        elapsed = int(time.time() - stats["start_time"])
                        hrs, rem = divmod(elapsed, 3600)
                        mins, secs = divmod(rem, 60)
                        time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
                        items_str = "\n".join([f"🔹 {k.capitalize()}: {v}" for k, v in stats["items"].items()])
                        msg = f"💎 ¡Nuevo ítem recogido: {item.capitalize()}!\n\n📊 REPORTE DE FARMEO:\n⏳ Tiempo: {time_str}\n{items_str}"
                        send_telegram(msg)
                        
                    time.sleep(0.1)
            else:
                time.sleep(0.1)

def attack_process(log_widget):
    global running, config, bot_paused
    with mss.mss() as sct:
        while running:
            if bot_paused: 
                time.sleep(0.5); continue
            if not config.data.get("attack_enabled", False) or not config.data.get("attack_area"):
                time.sleep(1)
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
                    x, y, w, h = cv2.boundingRect(cnt)
                    center_x = area["x1"] + x + w // 2
                    center_y = area["y1"] + y + h // 2
                    pydirectinput.moveTo(center_x, center_y)
                    time.sleep(0.05)
                    log_message(f"Batalla: Atacando enemigo!", log_widget)
                    pydirectinput.mouseDown(button='right')
                    time.sleep(1.0) 
                    pydirectinput.mouseUp(button='right')
                    target_found = True
                    break 
            if not target_found:
                time.sleep(0.1)

def monitor_process(log_widget):
    global running, bot_paused, config
    with mss.mss() as sct:
        while running:
            try:
                interval_mins = int(config.data["monitor"].get("interval_minutes", 30))
                enabled = config.data["monitor"].get("enabled", False)
                key = config.data["monitor"].get("key", "v")
            except:
                time.sleep(5)
                continue
                
            if not enabled or interval_mins <= 0:
                time.sleep(5)
                continue
            
            interval_secs = interval_mins * 60
            for _ in range(interval_secs):
                if not running: return
                time.sleep(1)
            
            if not running: break
            
            # --- SEMÁFORO EN ROJO ---
            log_message("🚦 Monitor: Pausando bot para abrir inventario...", log_widget)
            bot_paused = True
            time.sleep(1.5) 
            
            log_message("📸 Monitor: Tomando foto...", log_widget)
            
            # Aseguramos el foco de la ventana clickeando en el área de ataque o pickup
            area_focus = config.data.get("attack_area") or config.data.get("pickup_area") or config.data["monitor"].get("area")
            if area_focus:
                cx = (area_focus["x1"] + area_focus["x2"]) // 2
                cy = (area_focus["y1"] + area_focus["y2"]) // 2
                pydirectinput.moveTo(cx, cy)
                pydirectinput.click()
                time.sleep(0.5)
            
            # Usamos inyección a nivel de kernel con 'keyboard' en vez de pydirectinput
            keyboard.press(key)
            time.sleep(0.15)
            keyboard.release(key)
            time.sleep(1.5)
            
            filename = f"inventario_{int(time.time())}.png"
            area_conf = config.data["monitor"].get("area")
            
            if area_conf:
                mon_dict = {"top": area_conf["y1"], "left": area_conf["x1"], "width": area_conf["x2"] - area_conf["x1"], "height": area_conf["y2"] - area_conf["y1"]}
                img = np.array(sct.grab(mon_dict))
                cv2.imwrite(filename, cv2.cvtColor(img, cv2.COLOR_BGRA2BGR))
            else:
                sct.shot(mon=-1, output=filename)
            
            keyboard.press(key)
            time.sleep(0.15)
            keyboard.release(key)
            time.sleep(0.5)
            
            # --- SEMÁFORO EN VERDE ---
            bot_paused = False
            log_message("🚦 Monitor: Bot reanudado.", log_widget)
            
            threading.Thread(target=send_telegram_photo_async, args=(filename,), daemon=True).start()

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
        super().__init__()
        self.title("MU Online Helper - Legend V10 (Privacy Monitor)")
        self.geometry("950x850")
        self.configure(bg=MU_BG)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.buff_var = tk.BooleanVar(value=config.data.get("buff_enabled", True))
        self.pickup_var = tk.BooleanVar(value=config.data.get("pickup_enabled", False))
        self.attack_var = tk.BooleanVar(value=config.data.get("attack_enabled", False))
        
        self.create_widgets()
        keyboard.add_hotkey("F5", lambda: start_activity(self.log_text, self.cooldown_label))
        keyboard.add_hotkey("F6", lambda: stop_activity(self.log_text))
        
        self.update_stats_ui()

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

        # ---- ATTACK & COOLDOWN & MONITOR FRAME ----
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
        
        self.monitor_area_button = create_mu_button(monitor_frame, "Área de Foto", self.add_monitor_area)
        self.monitor_area_button.pack(pady=2)
        
        mon_inner = tk.Frame(monitor_frame, bg=MU_FRAME_BG)
        mon_inner.pack(pady=2)
        tk.Label(mon_inner, text="Mins:", bg=MU_FRAME_BG, fg=MU_FG).pack(side=tk.LEFT)
        self.mon_min_entry = tk.Entry(mon_inner, width=4, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG)
        self.mon_min_entry.pack(side=tk.LEFT, padx=2)
        self.mon_min_entry.insert(0, str(config.data["monitor"]["interval_minutes"]))
        
        tk.Label(mon_inner, text="Tecla:", bg=MU_FRAME_BG, fg=MU_FG).pack(side=tk.LEFT, padx=(5,0))
        self.mon_key_entry = tk.Entry(mon_inner, width=3, bg=MU_LIST_BG, fg=MU_FG, insertbackground=MU_FG)
        self.mon_key_entry.pack(side=tk.LEFT, padx=2)
        self.mon_key_entry.insert(0, config.data["monitor"]["key"])
        
        create_mu_button(monitor_frame, "Fijar", self.apply_monitor).pack(pady=5)
        
        # ---- ESTADÍSTICAS FRAME ----
        stats_frame = tk.LabelFrame(self, text=" 📊 Estadísticas de Farmeo ", **style_lf)
        stats_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self.time_lbl = tk.Label(stats_frame, text="⏳ Tiempo Farmeando: 00:00:00", bg=MU_FRAME_BG, fg="#00FFFF", font=("Consolas", 11, "bold"))
        self.time_lbl.pack(pady=2)
        
        self.items_lbl = tk.Label(stats_frame, text="Esperando inicio...", bg=MU_FRAME_BG, fg=MU_FG, font=("Consolas", 10))
        self.items_lbl.pack(pady=2)

        # ---- CONSOLA LOG ----
        self.log_text = tk.Text(self, height=8, bg=MU_LIST_BG, fg="#00FF00", font=("Consolas", 10), bd=2, relief="sunken")
        self.log_text.pack(fill=tk.BOTH, padx=15, pady=5, expand=True)
        self.log_text.insert(tk.END, ">>> Sistema en línea. Listo para la batalla.\n")
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

    def update_stats_ui(self):
        global stats, running
        if running and stats["start_time"]:
            elapsed = int(time.time() - stats["start_time"])
            hrs, rem = divmod(elapsed, 3600)
            mins, secs = divmod(rem, 60)
            self.time_lbl.config(text=f"⏳ Tiempo Farmeando: {hrs:02d}:{mins:02d}:{secs:02d}")
            
            if stats["items"]:
                items_str = " | ".join([f"{k.capitalize()}: {v}" for k, v in stats["items"].items()])
                self.items_lbl.config(text=items_str)
            else:
                self.items_lbl.config(text="Buscando joyas...")
        elif not running:
            self.time_lbl.config(text="⏳ Sistema Detenido")
            
        self.after(1000, self.update_stats_ui)

    def update_flags(self):
        config.data["buff_enabled"] = self.buff_var.get()
        config.data["pickup_enabled"] = self.pickup_var.get()
        config.data["attack_enabled"] = self.attack_var.get()
        self.update_config_status()

    def apply_monitor(self):
        try:
            config.data["monitor"]["enabled"] = self.monitor_var.get()
            config.data["monitor"]["interval_minutes"] = int(self.mon_min_entry.get())
            config.data["monitor"]["key"] = self.mon_key_entry.get().strip().lower()
            config.save()
            log_message(f"Monitor configurado: Cada {config.data['monitor']['interval_minutes']}m | Tecla: '{config.data['monitor']['key']}'", self.log_text)
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

    def apply_cooldown(self):
        try:
            config.data["cooldown"] = int(self.cooldown_entry.get())
            self.update_config_status()
            log_message(f"Cooldown actualizado a {config.data['cooldown']}s", self.log_text)
        except: pass

    def save_config(self):
        self.apply_monitor() # Forzar guardar config del monitor también
        config.save()
        log_message("Configuración guardada en el baúl (config.json)", self.log_text)

    def update_config_status(self):
        self.skill_button.config(bg="#006400" if config.data["buff_skills"] else MU_BTN_BG)
        self.player_button.config(bg="#006400" if config.data["buff_players"] else MU_BTN_BG)
        self.pickup_area_button.config(bg="#006400" if config.data.get("pickup_area") else MU_BTN_BG)
        self.attack_area_button.config(bg="#006400" if config.data.get("attack_area") else MU_BTN_BG)
        self.monitor_area_button.config(bg="#006400" if config.data["monitor"].get("area") else MU_BTN_BG)

    def on_close(self):
        stop_activity(self.log_text)
        self.destroy()

def start_activity(log_widget, cd_label):
    global running, buff_thread, pickup_thread, attack_thread, monitor_thread, stats, bot_paused
    if not running:
        running = True
        bot_paused = False
        stats["start_time"] = time.time()
        buff_thread = threading.Thread(target=buffing_process, args=(log_widget, cd_label), daemon=True); buff_thread.start()
        if config.data.get("pickup_enabled", False): pickup_thread = threading.Thread(target=pickup_process, args=(log_widget,), daemon=True); pickup_thread.start()
        if config.data.get("attack_enabled", False): attack_thread = threading.Thread(target=attack_process, args=(log_widget,), daemon=True); attack_thread.start()
        monitor_thread = threading.Thread(target=monitor_process, args=(log_widget,), daemon=True); monitor_thread.start()
        
        log_message("=== MACRO INICIADA (F5) ===", log_widget)
        if config.data["telegram"]["enabled"]: send_telegram("⚔️ Bot iniciado. Farmeo en curso...")

def stop_activity(log_widget):
    global running, bot_paused
    if running:
        running = False
        bot_paused = False
        log_message("=== MACRO DETENIDA (F6) ===", log_widget)
        if config.data["telegram"]["enabled"]: send_telegram("⏹ Bot detenido.")

if __name__ == "__main__":
    app = Application()
    app.mainloop()
