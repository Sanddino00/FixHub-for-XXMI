import os
import sys
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import json
import zipfile
import urllib.request

# -------------------------
# Configuration
# -------------------------
RESOURCE_FOLDER = "resources"
CONFIG_FILE = "config.json"
CURRENT_VERSION = "0.4.9"
GITHUB_LATEST_API = "https://api.github.com/repos/Sanddino00/FixHub-for-XXMI/releases/latest"

GAMES = {
    "Genshin Impact": ("gi", "GIMI"),
    "Honkai Star Rail": ("hsr", "SRMI"),
    "Wuthering Waves": ("wuwa", "WWMI"),
    "Zenless Zone Zero": ("zzz", "ZZMI"),
    "Honkai Impact 3rd": ("hi3", "HIMI"),
}

# -------------------------
# Python executable detection
# -------------------------
def get_python_executable():
    python_path = shutil.which("python")
    if python_path:
        return python_path
    embeddable_path = os.path.join(os.path.abspath("python-3.15.0a1-embed-amd64"), "python.exe")
    if os.path.exists(embeddable_path):
        return embeddable_path
    messagebox.showerror(
        "Python Not Found",
        "No system Python detected and python-3.15.0a1-embed-amd64 is missing!\n"
        "Please install Python or include the embeddable package."
    )
    return None

# -------------------------
# Version Comparison
# -------------------------
def compare_versions(v_local, v_online):
    def split(v):
        return list(map(int, v.split(".")))
    return split(v_online) > split(v_local)

# -------------------------
# Theme (Light/Dark)
# -------------------------
theme = {}

def load_theme():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                if data.get("mode") == "dark":
                    apply_dark_theme()
                else:
                    apply_light_theme()
        except Exception:
            apply_light_theme()
    else:
        apply_light_theme()

def save_theme(mode):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"mode": mode}, f)
    except Exception:
        pass

def apply_light_theme():
    global theme
    theme = {
        "bg": "white", "fg": "black",
        "button_bg": "#f0f0f0", "button_fg": "black",
        "listbox_bg": "white", "listbox_fg": "black"
    }
    update_theme()
    save_theme("light")

def apply_dark_theme():
    global theme
    theme = {
        "bg": "#2b2b2b", "fg": "white",
        "button_bg": "#444444", "button_fg": "white",
        "listbox_bg": "#333333", "listbox_fg": "white"
    }
    update_theme()
    save_theme("dark")

def update_theme():
    try:
        root.configure(bg=theme["bg"])
        for widget in all_widgets:
            cls = widget.__class__.__name__
            if cls in ("Button", "OptionMenu", "Frame", "Toplevel"):
                try:
                    widget.configure(bg=theme.get("button_bg","#f0f0f0"), fg=theme.get("button_fg","black"))
                except Exception:
                    pass
            elif cls == "Label":
                try:
                    widget.configure(bg=theme["bg"], fg=theme["fg"])
                except Exception:
                    pass
            elif cls == "Listbox":
                try:
                    widget.configure(bg=theme["listbox_bg"], fg=theme["listbox_fg"])
                except Exception:
                    pass
            elif cls == "Progressbar":
                try:
                    style = ttk.Style()
                    style.theme_use('default')
                    style.configure("TProgressbar", troughcolor=theme["bg"], background="#4caf50")
                except Exception:
                    pass
    except Exception:
        pass

# -------------------------
# GUI Setup
# -------------------------
root = tk.Tk()
root.title(f"FixHub_{CURRENT_VERSION}")
root.geometry("560x560")

target_folder = tk.StringVar()
status_text = tk.StringVar()
selected_game = tk.StringVar(value="Select Game")
all_widgets = []

# -------------------------
# Script list UI + logic
# -------------------------
script_listbox = tk.Listbox(root, width=60, height=12)
script_listbox.pack(pady=10)
all_widgets.append(script_listbox)

def populate_scripts(*args):
    script_listbox.delete(0, tk.END)
    game = selected_game.get()
    if game not in GAMES:
        validate_run_button()
        return
    subfolder, _ = GAMES[game]
    folder = os.path.join(RESOURCE_FOLDER, subfolder)
    if os.path.exists(folder):
        for script in sorted(os.listdir(folder)):
            if script.endswith(".py"):
                display_name = f"{script} [PY]"
                script_listbox.insert(tk.END, display_name)
            elif script.endswith(".exe"):
                display_name = f"{script} [EXE]"
                script_listbox.insert(tk.END, display_name)
    validate_run_button()

def select_target_folder():
    folder = filedialog.askdirectory(title="Select Target Folder")
    if folder:
        target_folder.set(folder)

def validate_run_button(*args):
    game = selected_game.get()
    folder = target_folder.get()
    if game not in GAMES:
        btn_run_script.config(state="disabled")
        return
    _, key = GAMES[game]
    btn_run_script.config(state="normal" if (folder and key in folder) else "disabled")

selected_game.trace("w", validate_run_button)
target_folder.trace("w", validate_run_button)

def run_script_thread(script_name):
    python_exe = get_python_executable()
    game = selected_game.get()
    if game not in GAMES:
        messagebox.showwarning("Warning", "Please select a game.")
        return
    subfolder, required_key = GAMES[game]
    if required_key not in target_folder.get():
        messagebox.showerror("Error", f"Target folder must contain '{required_key}' for {game}")
        return

    src = os.path.join(RESOURCE_FOLDER, subfolder, script_name)
    dst = os.path.join(target_folder.get(), script_name)

    try:
        status_text.set(f"Copying {script_name}...")
        shutil.copy(src, dst)

        status_text.set(f"Running {script_name}...")

        if script_name.endswith(".py"):
            if python_exe is None:
                return
            proc = subprocess.Popen([python_exe, dst], cwd=target_folder.get())
        elif script_name.endswith(".exe"):
            proc = subprocess.Popen([dst], cwd=target_folder.get())
        else:
            messagebox.showwarning("Unsupported", f"Cannot run file type of '{script_name}'")
            return

        proc.wait()

        if proc.returncode == 0:
            messagebox.showinfo("Success", f"Script '{script_name}' finished successfully.")
        else:
            messagebox.showerror("Script Error", f"Script exited with code {proc.returncode}")

    finally:
        try:
            if os.path.exists(dst):
                os.remove(dst)
        except Exception:
            pass
        status_text.set("Ready")

def run_script():
    sel = script_listbox.curselection()
    if not sel:
        messagebox.showwarning("Warning", "Select a script first.")
        return
    script_name = script_listbox.get(sel[0])
    script_name = script_name.split(" [")[0]
    threading.Thread(target=run_script_thread, args=(script_name,), daemon=True).start()

# -------------------------
# Updater helpers
# -------------------------
def download_to_path(url, dest_path, progress_callback=None):
    try:
        with urllib.request.urlopen(url) as r:
            total = r.getheader("Content-Length")
            total = int(total) if total else None
            with open(dest_path, "wb") as f:
                downloaded = 0
                chunk_size = 8192
                while True:
                    chunk = r.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(downloaded, total)
        return True, None
    except Exception as e:
        return False, str(e)

def get_latest_release_info():
    with urllib.request.urlopen(GITHUB_LATEST_API) as response:
        data = json.loads(response.read().decode())
    return data

def smooth_progress_bar(bar, target_value):
    current = bar['value']
    step = (target_value - current) / 10
    if abs(step) < 0.1:
        bar['value'] = target_value
        return
    bar['value'] = current + step
    bar.after(20, smooth_progress_bar, bar, target_value)

# -------------------------
# Resource updater
# -------------------------
def download_resources_action():
    def thread_job():
        try:
            status_text.set("Checking latest release...")
            data = get_latest_release_info()
            asset = next((a for a in data.get("assets", []) if a.get("name")=="resources.zip"), None)
            if not asset:
                messagebox.showinfo("Update", "No resources.zip found in latest release.")
                status_text.set("Ready")
                return

            download_url = asset.get("browser_download_url")
            tmp_zip = os.path.join(os.path.abspath("."), "resource_new.tmp.zip")
            progress_bar_resources['value'] = 0

            def progress(downloaded, total):
                target = downloaded / total * 100
                smooth_progress_bar(progress_bar_resources, target)

            status_text.set("Downloading resources.zip...")
            ok, err = download_to_path(download_url, tmp_zip, progress)
            if not ok:
                messagebox.showerror("Download Failed", err or "Unknown")
                status_text.set("Ready")
                progress_bar_resources['value'] = 0
                return

            if os.path.exists(RESOURCE_FOLDER):
                shutil.rmtree(RESOURCE_FOLDER)
            with zipfile.ZipFile(tmp_zip, "r") as z:
                z.extractall(RESOURCE_FOLDER)
            os.remove(tmp_zip)
            progress_bar_resources['value'] = 100

            populate_scripts()
            status_text.set("Resources downloaded successfully!")
            messagebox.showinfo("Download Complete", "Resources updated successfully.")
            progress_bar_resources['value'] = 0

        except Exception as e:
            messagebox.showerror("Download Failed", str(e))
            status_text.set("Ready")
            progress_bar_resources['value'] = 0

    threading.Thread(target=thread_job, daemon=True).start()

# -------------------------
# Program updater
# -------------------------
def update_program_action():
    if sys.platform != "win32":
        messagebox.showerror("Unsupported", "Program update only works on Windows EXE.")
        return

    def thread_job():
        try:
            status_text.set("Checking latest release...")
            data = get_latest_release_info()
            exe_asset = next((a for a in data.get("assets", []) if a.get("name","").lower().endswith(".exe")), None)
            if not exe_asset:
                messagebox.showinfo("Update", "No EXE found in latest release.")
                status_text.set("Ready")
                return

            download_url = exe_asset.get("browser_download_url")
            cur_dir = os.path.dirname(os.path.abspath(sys.executable))
            exe_name_online = exe_asset.get("name")
            tmp_new_exe = os.path.join(cur_dir, exe_name_online+".new")
            final_exe_path = os.path.join(cur_dir, exe_name_online)
            progress_bar_exe['value'] = 0

            def progress(downloaded, total):
                target = downloaded / total * 100
                smooth_progress_bar(progress_bar_exe, target)

            status_text.set("Downloading new executable...")
            ok, err = download_to_path(download_url, tmp_new_exe, progress)
            if not ok:
                messagebox.showerror("Download Failed", err or "Unknown")
                status_text.set("Ready")
                progress_bar_exe['value'] = 0
                return

            bat_path = os.path.join(cur_dir, "fixhub_updater.bat")
            running_exe = os.path.basename(sys.executable)
            bat_content = f"""@echo off
cd /d "{cur_dir}"
:loop
del "{running_exe}" >nul 2>&1
if exist "{running_exe}" (
    timeout /t 1 >nul
    goto loop
)
move /Y "{os.path.basename(tmp_new_exe)}" "{os.path.basename(final_exe_path)}" >nul 2>&1
start "" "{os.path.basename(final_exe_path)}"
del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as bat:
                bat.write(bat_content)

            subprocess.Popen(['cmd', '/c', 'start', '', bat_path], shell=False, close_fds=True)
            progress_bar_exe['value'] = 100
            status_text.set("Updater launched — exiting to allow update.")
            root.destroy()
            os._exit(0)
        except Exception as e:
            messagebox.showerror("Update Failed", str(e))
            status_text.set("Ready")
            progress_bar_exe['value'] = 0

    threading.Thread(target=thread_job, daemon=True).start()

# -------------------------
# Check latest version
# -------------------------
def check_latest_version():
    def thread_check():
        try:
            data = get_latest_release_info()
            tag = data.get("tag_name","").strip()
            online_version = None
            if tag.lower().startswith("version_"):
                online_version = tag.split("_",1)[1]
            if online_version and compare_versions(CURRENT_VERSION, online_version):
                lbl_update_badge.config(text="🔴 Update Available!", fg="red")
            else:
                lbl_update_badge.config(text="✔ Up to Date", fg="green")
        except Exception:
            pass
    threading.Thread(target=thread_check, daemon=True).start()

# -------------------------
# Tooltip class
# -------------------------
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=5, ipady=3)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

# -------------------------
# Settings window
# -------------------------
def open_settings():
    settings_win = tk.Toplevel(root)
    settings_win.title("Settings")
    settings_win.geometry("360x250")
    settings_win.resizable(False, False)
    settings_win.transient(root)
    settings_win.grab_set()

    btn_theme = tk.Button(settings_win, text="Toggle Light/Dark Mode",
                          command=lambda: apply_dark_theme() if theme.get("bg","white")=="white" else apply_light_theme())
    btn_theme.pack(pady=6)
    all_widgets.append(btn_theme)

    btn_download_resources = tk.Button(settings_win, text="Download Resources", command=download_resources_action)
    btn_download_resources.pack(pady=6)
    all_widgets.append(btn_download_resources)

    global progress_bar_resources
    progress_bar_resources = ttk.Progressbar(settings_win, length=300, mode='determinate')
    progress_bar_resources.pack(pady=2)
    all_widgets.append(progress_bar_resources)

    btn_update_program = tk.Button(settings_win, text="Update Program (EXE)", command=update_program_action)
    btn_update_program.pack(pady=6)
    all_widgets.append(btn_update_program)

    global progress_bar_exe
    progress_bar_exe = ttk.Progressbar(settings_win, length=300, mode='determinate')
    progress_bar_exe.pack(pady=2)
    all_widgets.append(progress_bar_exe)

    btn_check_updates = tk.Button(settings_win, text="Check for Updates", command=check_latest_version)
    btn_check_updates.pack(pady=6)
    all_widgets.append(btn_check_updates)

# -------------------------
# GUI Controls
# -------------------------
gear_button = tk.Button(root, text="⚙️", command=open_settings)
gear_button.place(x=5, y=5)
all_widgets.append(gear_button)
Tooltip(gear_button, "Settings")

game_menu = tk.OptionMenu(root, selected_game, *GAMES.keys(), command=populate_scripts)
game_menu.pack(pady=40); all_widgets.append(game_menu)

btn_select_folder = tk.Button(root, text="Select Target Folder", command=select_target_folder)
btn_select_folder.pack(pady=5); all_widgets.append(btn_select_folder)

lbl_target = tk.Label(root, textvariable=target_folder)
lbl_target.pack(pady=5); all_widgets.append(lbl_target)

btn_run_script = tk.Button(root, text="Run Script", command=run_script, state="disabled")
btn_run_script.pack(pady=8); all_widgets.append(btn_run_script)

btn_refresh = tk.Button(root, text="Refresh Scripts", command=populate_scripts)
btn_refresh.pack(pady=5); all_widgets.append(btn_refresh)

lbl_update_badge = tk.Label(root, text="", font=("Arial", 10, "bold"))
lbl_update_badge.pack(pady=6); all_widgets.append(lbl_update_badge)

status_label = tk.Label(root, textvariable=status_text, fg="blue")
status_label.pack(pady=10); all_widgets.append(status_label)
status_text.set("Ready")

# -------------------------
# Start
# -------------------------
load_theme()
check_latest_version()
populate_scripts()
root.mainloop()
