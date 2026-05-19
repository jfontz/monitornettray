import threading
import urllib.request
from datetime import datetime
from PIL import Image, ImageDraw
import pystray
import tkinter as tk
from tkinter import scrolledtext
import queue
import time
import sys
import subprocess
import os

# ---------- CONFIG ----------
TARGET_URL = "https://www.google.com"
CHECK_INTERVAL = 5  # seconds
CONSECUTIVE_THRESHOLD = 2  # failed checks before offline

# ---------- GLOBALS ----------
last_status = None
went_offline_at = None
failure_count = 0
logs = []  # in-memory logs
gui_queue = queue.Queue()

log_window = None
log_text = None
tray_icon = None

# ---------- UTILITIES ----------
def check_internet():
    try:
        urllib.request.urlopen(TARGET_URL, timeout=3)
        return True
    except:
        return False

def format_duration(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s" if m > 0 else f"{s}s"

def create_icon(color):
    """Create a 64x64 circle icon of given color"""
    image = Image.new("RGB", (64, 64), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=color)
    return image

def show_notification(title, message):
    """Send Windows notification using PowerShell - works in EXE"""
    try:
        # Escape single quotes in message
        message = message.replace("'", "''")
        title = title.replace("'", "''")
        
        # PowerShell command to show Windows 10/11 toast notification
        ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$app_id = 'Internet Watchdog'

$template = @"
<toast>
    <visual>
        <binding template="ToastText02">
            <text id="1">{title}</text>
            <text id="2">{message}</text>
        </binding>
    </visual>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app_id).Show($toast)
"""
        
        # Run PowerShell in hidden window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        
        subprocess.Popen(
            ['powershell', '-WindowStyle', 'Hidden', '-Command', ps_script],
            startupinfo=startupinfo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        add_log(f"Notification error: {str(e)}")

# ---------- LOG WINDOW ----------
def show_logs(icon=None, item=None):
    gui_queue.put(_show_logs_gui)

def _show_logs_gui():
    global log_window, log_text

    def on_close():
        global log_window, log_text
        if log_window:
            log_window.destroy()
        log_window = None
        log_text = None

    if log_window is None or not tk.Tk.winfo_exists(log_window) if log_window else True:
        log_window = tk.Toplevel(root)
        log_window.title("Internet Watchdog Logs")
        log_window.geometry("500x400")
        log_text = scrolledtext.ScrolledText(log_window, state="disabled", wrap="word")
        log_text.pack(fill="both", expand=True)
        log_text.config(state="normal")
        for entry in reversed(logs):
            log_text.insert("1.0", entry + "\n")
        log_text.config(state="disabled")
        log_window.protocol("WM_DELETE_WINDOW", on_close)
        log_window.deiconify()
        log_window.lift()
        log_window.focus_force()
    else:
        log_window.deiconify()
        log_window.lift()
        log_window.focus_force()

def add_log(entry):
    logs.append(entry)
    gui_queue.put(lambda: _append_log_gui(entry))

def _append_log_gui(entry):
    if log_text and log_window and tk.Tk.winfo_exists(log_window):
        try:
            log_text.config(state="normal")
            log_text.insert("1.0", entry + "\n")
            log_text.config(state="disabled")
        except:
            pass

# ---------- NETWORK CHECK ----------
def update_status():
    global last_status, went_offline_at, failure_count, tray_icon
    
    # Initial log
    add_log(f"Internet Watchdog started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    add_log("Using native Windows notifications")
    
    while True:
        is_up = check_internet()
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if is_up:
            failure_count = 0
        else:
            failure_count += 1

        if not is_up and failure_count < CONSECUTIVE_THRESHOLD:
            time.sleep(CHECK_INTERVAL)
            continue

        if is_up != last_status:
            if is_up:
                if tray_icon:
                    tray_icon.icon = create_icon("green")
                if went_offline_at:
                    outage_seconds = (datetime.now() - went_offline_at).total_seconds()
                    duration_str = format_duration(outage_seconds)
                    log_entry = f"Internet back at {time_str} (Outage: {duration_str})"
                else:
                    log_entry = f"Internet back at {time_str}"
                add_log(log_entry)
                show_notification("INTERNET RESTORED", log_entry)
            else:
                if tray_icon:
                    tray_icon.icon = create_icon("red")
                went_offline_at = datetime.now()
                log_entry = f"Internet LOST at {time_str}"
                add_log(log_entry)
                show_notification("INTERNET LOST", log_entry)

            last_status = is_up

        time.sleep(CHECK_INTERVAL)

# ---------- GUI QUEUE PROCESS ----------
def process_gui_queue():
    try:
        while not gui_queue.empty():
            func = gui_queue.get_nowait()
            try:
                func()
            except Exception as e:
                print(f"GUI queue error: {e}")
    except:
        pass
    root.after(100, process_gui_queue)

# ---------- TRAY MENU ----------
def quit_action(icon, item):
    add_log(f"Internet Watchdog stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    icon.stop()
    root.quit()

# ---------- SETUP TRAY ICON ----------
def setup_tray():
    global tray_icon
    tray_icon = pystray.Icon(
        "Internet Watchdog",
        create_icon("gray"),
        menu=pystray.Menu(
            pystray.MenuItem("Show Logs", show_logs),
            pystray.MenuItem("Quit", quit_action),
        ),
    )
    tray_icon.run()

# ---------- TK ROOT ----------
root = tk.Tk()
root.title("Internet Watchdog")
root.withdraw()  # hide the window

# ---------- START THREADS ----------
# Start network monitoring thread
threading.Thread(target=update_status, daemon=True).start()

# Start tray icon in separate thread (not main thread)
threading.Thread(target=setup_tray, daemon=True).start()

# Start GUI queue processing
root.after(100, process_gui_queue)

# ---------- RUN TKINTER MAIN LOOP ----------
try:
    root.mainloop()
except KeyboardInterrupt:
    if tray_icon:
        tray_icon.stop()
    sys.exit()