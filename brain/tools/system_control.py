import os
import time
import threading
import subprocess
import urllib.parse
import urllib.request
import re
import logging
import ctypes
from brain.core.memory import memory

logger = logging.getLogger("NILA.Tools.SystemControl")

def focus_browser_window() -> bool:
    """Finds and activates Chrome, Edge, or Firefox window to prevent terminal focus leakage."""
    try:
        import pygetwindow as gw
        for title in ["YouTube", "Chrome", "Edge", "Firefox"]:
            wins = gw.getWindowsWithTitle(title)
            if wins:
                win = wins[0]
                if win.isMinimized:
                    win.restore()
                win.activate()
                time.sleep(0.2)
                return True
    except Exception as e:
        logger.warning(f"Could not switch window focus: {e}")
    return False

def youtube_control(action: str, count: int = 1) -> dict:
    act = action.lower().strip()
    count = max(1, min(10, int(count)))
    
    focus_browser_window()
    
    try:
        import pyautogui
        for _ in range(count):
            if act in ["fast_forward", "forward", "seek_forward"]:
                pyautogui.press('l')
            elif act in ["rewind", "back", "seek_backward"]:
                pyautogui.press('j')
            elif act in ["speed_up", "faster", "increase_speed"]:
                pyautogui.hotkey('shift', '>')
            elif act in ["speed_down", "slower", "decrease_speed"]:
                pyautogui.hotkey('shift', '<')
            elif act in ["mute", "unmute"]:
                pyautogui.press('m')
            elif act in ["fullscreen"]:
                pyautogui.press('f')
            else:
                return {"ok": False, "error": f"Unknown YouTube action '{action}'"}
            time.sleep(0.1)

        return {"ok": True, "data": f"Executed YouTube control '{act}' ({count}x)"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to execute YouTube control: {str(e)}"}

def set_volume(level: int) -> dict:
    level = max(0, min(100, int(level)))
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL, CoCreateInstance

        volume = None

        # 1. Try PyCaw Modern API (v2.x+)
        try:
            device = AudioUtilities.GetSpeakers()
            if hasattr(device, 'EndpointVolume'):
                volume = device.EndpointVolume
            elif hasattr(device, 'Activate'):
                interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
        except Exception:
            pass

        # 2. Fallback to Direct IMMDeviceEnumerator (COM direct call)
        if volume is None:
            from pycaw.pycaw import MMDeviceEnumerator, EDataFlow, ERole
            enumerator = CoCreateInstance(
                MMDeviceEnumerator._reg_clsid_,
                interface=MMDeviceEnumerator,
                clsctx=CLSCTX_ALL
            )
            endpoint = enumerator.GetDefaultAudioEndpoint(EDataFlow.eRender.value, ERole.eMultimedia.value)
            interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)

        scalar_val = float(level) / 100.0
        volume.SetMasterVolumeLevelScalar(scalar_val, None)

        return {"ok": True, "data": f"System master volume set to {level}%"}
    except Exception as e:
        logger.error(f"PyCaw volume error: {e}")
        return {"ok": False, "error": f"Failed to set system volume: {str(e)}"}

def media_control(action: str) -> dict:
    VK_MEDIA_NEXT = 0xB0
    VK_MEDIA_PREV = 0xB1
    VK_MEDIA_PLAY_PAUSE = 0xB3
    VK_VOLUME_MUTE = 0xAD
    KEYEVENTF_KEYUP = 0x0002

    act = action.lower().strip()
    key_code = None

    if act in ["play", "pause", "toggle"]:
        key_code = VK_MEDIA_PLAY_PAUSE
    elif act in ["next", "skip"]:
        key_code = VK_MEDIA_NEXT
    elif act in ["previous", "prev", "back"]:
        key_code = VK_MEDIA_PREV
    elif act in ["mute", "unmute"]:
        key_code = VK_VOLUME_MUTE
    else:
        return {"ok": False, "error": f"Unknown media action '{action}'."}

    try:
        ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP, 0)
        return {"ok": True, "data": f"Executed media command: {act}"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to send media key: {str(e)}"}

def set_brightness(level: int) -> dict:
    level = max(0, min(100, int(level)))
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        return {"ok": True, "data": f"Screen brightness set to {level}%"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to set screen brightness: {str(e)}"}

def process_manager(action: str, process_name: str = "") -> dict:
    act = action.lower().strip()

    if act == "list":
        try:
            cmd = "powershell -Command \"Get-Process | Where-Object {.MainWindowTitle -ne ''} | Select-Object -ExpandProperty ProcessName\""
            output = subprocess.check_output(cmd, shell=True, text=True)
            procs = list(set([p.strip() for p in output.splitlines() if p.strip()]))
            return {"ok": True, "data": f"Active app processes: {', '.join(procs[:15])}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    elif act in ["close", "kill"]:
        if not process_name:
            return {"ok": False, "error": "Must specify process_name to close."}
        
        proc_clean = process_name.replace(".exe", "").strip()
        try:
            os.system(f"taskkill /f /im {proc_clean}.exe")
            return {"ok": True, "data": f"Terminated process '{proc_clean}'"}
        except Exception as e:
            return {"ok": False, "error": f"Failed to terminate '{proc_clean}': {str(e)}"}

    return {"ok": False, "error": f"Invalid process action '{action}'"}

def set_reminder(message: str, delay_seconds: int) -> dict:
    def _timer_thread():
        time.sleep(delay_seconds)
        ps_script = f'''
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show("{message}", "N.I.L.A. Reminder", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        '''
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)
        except Exception as e:
            logger.error(f"Reminder notification failed: {e}")

    threading.Thread(target=_timer_thread, daemon=True).start()
    memory.add_reminder(message, f"in {delay_seconds} seconds")
    return {"ok": True, "data": f"Reminder set for '{message}' in {delay_seconds} seconds."}

def send_whatsapp_message(phone_number: str, message: str) -> dict:
    clean_number = "".join(filter(str.isdigit, phone_number))
    encoded_msg = urllib.parse.quote(message)
    
    app_uri = f"whatsapp://send?phone={clean_number}&text={encoded_msg}"
    web_url = f"https://web.whatsapp.com/send?phone={clean_number}&text={encoded_msg}"

    launched_native = False
    try:
        res = os.system(f'start "" "{app_uri}"')
        if res == 0:
            launched_native = True
    except Exception as e:
        logger.warning(f"Native WhatsApp launch attempt failed: {e}")

    if not launched_native:
        os.system(f'start "" "{web_url}"')

    def _auto_send():
        time.sleep(5 if launched_native else 8)
        try:
            import pyautogui
            pyautogui.press('enter')
        except Exception as e:
            logger.error(f"WhatsApp auto-send error: {e}")

    threading.Thread(target=_auto_send, daemon=True).start()
    status_text = "WhatsApp Desktop App" if launched_native else "WhatsApp Web"
    return {"ok": True, "data": f"Opened message for {phone_number} via {status_text}."}

def smart_open(target: str) -> dict:
    target_clean = target.strip().strip('"\'')
    
    cached_file = memory.lookup_file(target_clean)
    if cached_file and os.path.exists(cached_file):
        os.startfile(cached_file)
        return {"ok": True, "data": f"Opened cached file: {cached_file}"}

    if target_clean.startswith("http://") or target_clean.startswith("https://") or target_clean.startswith("www."):
        url = target_clean if target_clean.startswith("http") else f"https://{target_clean}"
        os.system(f'start "" "{url}"')
        return {"ok": True, "data": f"Opened web URL: {url}"}

    user_home = os.path.expanduser("~")
    special_folders = {
        "downloads": os.path.join(user_home, "Downloads"),
        "documents": os.path.join(user_home, "Documents"),
        "desktop": os.path.join(user_home, "Desktop"),
        "pictures": os.path.join(user_home, "Pictures"),
        "control panel": "control",
        "control": "control",
        "calculator": "calc",
        "cmd": "cmd",
        "terminal": "wt"
    }

    lower_target = target_clean.lower()
    if lower_target in special_folders:
        resolved = special_folders[lower_target]
        os.system(f'start "" "{resolved}"')
        return {"ok": True, "data": f"Opened {target_clean} via path: {resolved}"}

    expanded_path = os.path.expandvars(os.path.expanduser(target_clean))
    if os.path.exists(expanded_path):
        os.startfile(expanded_path)
        return {"ok": True, "data": f"Opened file/folder: {expanded_path}"}

    downloads_check = os.path.join(user_home, "Downloads", target_clean)
    if os.path.exists(downloads_check):
        os.startfile(downloads_check)
        return {"ok": True, "data": f"Found and opened in Downloads: {downloads_check}"}

    try:
        import pyautogui
        pyautogui.hotkey('win', 's')
        time.sleep(0.3)
        pyautogui.write(target_clean, interval=0.02)
        time.sleep(0.3)
        pyautogui.press('enter')
        return {"ok": True, "data": f"Invoked Windows Start Search for: {target_clean}"}
    except Exception as e:
        return {"ok": False, "error": f"Could not launch or search '{target_clean}': {str(e)}"}

def file_search(filename: str, search_dir: str = "Downloads") -> dict:
    user_home = os.path.expanduser("~")
    if search_dir.lower() in ["downloads", "download"]:
        base_path = os.path.join(user_home, "Downloads")
    elif search_dir.lower() in ["documents", "document"]:
        base_path = os.path.join(user_home, "Documents")
    elif search_dir.lower() in ["desktop"]:
        base_path = os.path.join(user_home, "Desktop")
    else:
        base_path = os.path.expanduser(search_dir)

    if not os.path.exists(base_path):
        return {"ok": False, "error": f"Directory does not exist: {base_path}"}

    matches = []
    for root, dirs, files in os.walk(base_path):
        for f in files:
            if filename.lower() in f.lower():
                full_p = os.path.join(root, f)
                matches.append(full_p)
                memory.remember_file(f, full_p)
                if len(matches) >= 5:
                    break

    if matches:
        return {"ok": True, "data": f"Found matching file(s): {', '.join(matches)}", "files": matches}
    return {"ok": False, "data": f"No file matching '{filename}' found in {base_path}"}

def youtube_search(query: str) -> dict:
    """Only searches for videos on YouTube without auto-playing."""
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
    os.system(f'start "" "{search_url}"')
    return {"ok": True, "data": f"Opened YouTube search results for: {query}"}

def youtube_play(query: str) -> dict:
    """Resolves top official YouTube video ID programmatically and launches direct video URL."""
    clean_q = query.strip()
    keywords = ["official", "original", "trailer", "song", "video"]
    if not any(k in clean_q.lower() for k in keywords):
        search_query = f"{clean_q} official"
    else:
        search_query = clean_q

    encoded_query = urllib.parse.quote(search_query)
    search_url = f"https://www.youtube.com/results?search_query={encoded_query}"

    video_id = None
    try:
        req = urllib.request.Request(
            search_url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        video_ids = re.findall(r"watch\?v=(\w{11})", html)
        if video_ids:
            video_id = video_ids[0]
    except Exception as e:
        logger.warning(f"Could not extract direct YouTube video ID: {e}")

    if video_id:
        target_url = f"https://www.youtube.com/watch?v={video_id}"
        os.system(f'start "" "{target_url}"')
        return {"ok": True, "data": f"Playing top video result directly: {target_url}"}

    # Fallback to search results page if scraping fails
    os.system(f'start "" "{search_url}"')
    return {"ok": True, "data": f"Opened YouTube search for: {search_query}"}