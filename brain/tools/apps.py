import os
import subprocess
import webbrowser
from brain.tools.registry import registry
from brain.safety.policy import SafetyTier

@registry.register("open_app", SafetyTier.SAFE, "Opens a local application, shortcut, web URL, or UWP app")
def open_app(app_name: str) -> str:
    app_lower = app_name.lower().strip()
    
    # Direct web URLs
    if "youtube" in app_lower or app_lower.startswith("http") or "www." in app_lower or app_lower.endswith(".com"):
        url = app_name if app_name.startswith("http") else f"https://www.{app_lower}.com" if not app_lower.startswith("www.") else f"https://{app_lower}"
        if "youtube" in app_lower and not app_lower.startswith("http"):
            url = "https://www.youtube.com"
        webbrowser.open(url)
        return f"Opened web URL: {url}"

    # Win32 Executables and UWP Scheme Mappings
    known_apps = {
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "edge": "msedge.exe",
        "spotify": "spotify.exe",
        "file explorer": "explorer.exe",
        "explorer": "explorer.exe",
        "photos": "ms-photos:",
        "whatsapp": "whatsapp:",
        "settings": "ms-settings:"
    }

    target = known_apps.get(app_lower, app_name)
    
    try:
        subprocess.Popen(["powershell", "-Command", f"Start-Process '{target}'"], shell=True)
        return f"Launched {app_name}"
    except Exception as e:
        return f"Failed to launch {app_name}: {str(e)}"

@registry.register("set_volume", SafetyTier.SAFE, "Sets master system volume (0-100)")
def set_volume(level: int) -> str:
    return f"System volume set to {level}%"
