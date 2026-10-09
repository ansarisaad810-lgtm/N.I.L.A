import sys
import json
import asyncio
import psutil
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QUrl, QTimer
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
import websockets

class HUDLogReceiver(QThread):
    msg_received = pyqtSignal(dict)

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.listen())

    async def listen(self):
        uri = "ws://127.0.0.1:8765"
        while True:
            try:
                async with websockets.connect(uri) as ws:
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        self.msg_received.emit(data)
            except Exception:
                await asyncio.sleep(2)

class DisplayOnlyHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.drag_pos = QPoint()
        self.init_ui()
        self.setup_telemetry()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1100, 720)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView(self)
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)

        self.receiver = HUDLogReceiver()
        self.receiver.msg_received.connect(self.handle_ipc_message)
        self.receiver.start()

        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>N.I.L.A. HUD Display</title>
    <style>
        :root {
            --cyan-main: #00f3ff;
            --cyan-glow: rgba(0, 243, 255, 0.4);
            --cyan-dim: rgba(0, 243, 255, 0.15);
            --bg-dark: rgba(2, 8, 19, 0.88);
            --panel-bg: rgba(4, 20, 38, 0.75);
            --border-line: rgba(0, 243, 255, 0.35);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Courier New', Courier, monospace; user-select: none; }
        body {
            background-color: var(--bg-dark);
            color: var(--cyan-main);
            height: 100vh;
            overflow: hidden;
            background-image: 
                radial-gradient(circle at center, rgba(0, 80, 120, 0.2) 0%, transparent 70%),
                linear-gradient(rgba(0, 243, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 243, 255, 0.03) 1px, transparent 1px);
            background-size: 100% 100%, 30px 30px, 30px 30px;
            border: 1.5px solid var(--cyan-main);
            border-radius: 8px;
        }

        .overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%);
            background-size: 100% 4px; z-index: 10;
        }

        .hud-container {
            display: grid;
            grid-template-columns: 280px 1fr 320px;
            grid-template-rows: 60px 1fr 160px;
            height: 100vh; padding: 15px; gap: 15px;
        }

        .hud-panel {
            background: var(--panel-bg);
            border: 1px solid var(--border-line);
            box-shadow: 0 0 15px var(--cyan-dim), inset 0 0 15px var(--cyan-dim);
            backdrop-filter: blur(5px);
            position: relative; padding: 12px; border-radius: 4px;
        }

        .hud-panel::before, .hud-panel::after {
            content: ''; position: absolute; width: 8px; height: 8px; border-color: var(--cyan-main); border-style: solid;
        }
        .hud-panel::before { top: -2px; left: -2px; border-width: 2px 0 0 2px; }
        .hud-panel::after { bottom: -2px; right: -2px; border-width: 0 2px 2px 0; }

        .panel-header {
            font-size: 0.75rem; letter-spacing: 2px; text-transform: uppercase;
            border-bottom: 1px solid var(--border-line); padding-bottom: 4px; margin-bottom: 8px;
            display: flex; justify-content: space-between; color: #fff; text-shadow: 0 0 5px var(--cyan-main);
        }

        .header { grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center; padding: 0 20px; }
        .title-group h1 { font-size: 1.6rem; letter-spacing: 4px; text-shadow: 0 0 10px var(--cyan-main); }
        .title-group p { font-size: 0.65rem; letter-spacing: 1px; opacity: 0.7; }
        .sys-status { display: flex; gap: 20px; font-size: 0.8rem; }
        .status-tag { color: #4cd137; text-shadow: 0 0 5px #4cd137; }

        .left-col, .right-col { display: flex; flex-direction: column; gap: 15px; }
        .stat-bar { margin-bottom: 12px; }
        .stat-label { display: flex; justify-content: space-between; font-size: 0.7rem; margin-bottom: 4px; }
        .bar-outer { width: 100%; height: 8px; background: rgba(0, 243, 255, 0.1); border: 1px solid var(--border-line); overflow: hidden; }
        .bar-inner { height: 100%; background: var(--cyan-main); box-shadow: 0 0 8px var(--cyan-main); transition: width 0.3s ease; }

        .center-col { display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; }
        .ai-core { position: relative; width: 280px; height: 280px; display: flex; align-items: center; justify-content: center; }
        .ring { position: absolute; border-radius: 50%; border: 2px solid transparent; }
        .ring-1 { width: 260px; height: 260px; border-top-color: var(--cyan-main); border-bottom-color: var(--cyan-main); animation: spin 10s linear infinite; }
        .ring-2 { width: 200px; height: 200px; border-left-color: var(--cyan-main); border-right-color: var(--cyan-main); animation: spin-reverse 6s linear infinite; }
        .ring-3 { width: 140px; height: 140px; border: 1px dashed var(--cyan-main); animation: spin 15s linear infinite; }
        .core-glow { width: 70px; height: 70px; background: radial-gradient(circle, #fff 0%, var(--cyan-main) 60%, transparent 100%); border-radius: 50%; box-shadow: 0 0 30px var(--cyan-main); animation: pulse 2s ease-in-out infinite; }
        .nila-text { position: absolute; font-size: 1.1rem; font-weight: bold; letter-spacing: 3px; text-shadow: 0 0 8px var(--cyan-main); color: #fff; }

        .feed-list { list-style: none; font-size: 0.75rem; display: flex; flex-direction: column; gap: 8px; }
        .feed-item { display: flex; justify-content: space-between; border-bottom: 1px rgba(0, 243, 255, 0.1) dashed; padding-bottom: 4px; }

        .bottom-row { grid-column: 1 / -1; display: grid; grid-template-columns: 1fr 300px; gap: 15px; }
        .terminal-log { font-size: 0.75rem; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; color: rgba(0, 243, 255, 0.85); }
        .terminal-log p::before { content: "> "; color: var(--cyan-main); }

        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes spin-reverse { from { transform: rotate(360deg); } to { transform: rotate(0deg); } }
        @keyframes pulse { 0%, 100% { transform: scale(0.9); opacity: 0.8; } 50% { transform: scale(1.1); opacity: 1; } }
    </style>
</head>
<body>
    <div class="overlay"></div>
    <div class="hud-container">
        <header class="hud-panel header">
            <div class="title-group">
                <h1>N.I.L.A.</h1>
                <p>Neural Interactive Logic Assistant // VERSION 4.0.2</p>
            </div>
            <div class="sys-status">
                <div>SYSTEM: <span class="status-tag" id="sys-status-text">ONLINE</span></div>
                <div>SECURE CONNECTION: <span class="status-tag">ACTIVE</span></div>
                <div id="clock">00:00:00</div>
            </div>
        </header>

        <div class="left-col">
            <div class="hud-panel" style="flex: 1;">
                <div class="panel-header">
                    <span>Task Manager Telemetry</span>
                    <span>REALTIME</span>
                </div>
                <div class="stat-bar">
                    <div class="stat-label"><span>CPU UTILIZATION</span><span id="cpu-val">0%</span></div>
                    <div class="bar-outer"><div class="bar-inner" id="cpu-bar" style="width: 0%;"></div></div>
                </div>
                <div class="stat-bar">
                    <div class="stat-label"><span>MEMORY (RAM) LOAD</span><span id="ram-val">0%</span></div>
                    <div class="bar-outer"><div class="bar-inner" id="ram-bar" style="width: 0%;"></div></div>
                </div>
                <div class="stat-bar">
                    <div class="stat-label"><span>DISK USAGE (C:)</span><span id="disk-val">0%</span></div>
                    <div class="bar-outer"><div class="bar-inner" id="disk-bar" style="width: 0%;"></div></div>
                </div>
                <div class="stat-bar">
                    <div class="stat-label"><span>ACTIVE PROCESSES</span><span id="proc-val">0</span></div>
                    <div class="bar-outer"><div class="bar-inner" id="proc-bar" style="width: 50%;"></div></div>
                </div>
            </div>
        </div>

        <div class="center-col">
            <div class="ai-core">
                <div class="ring ring-1"></div>
                <div class="ring ring-2"></div>
                <div class="ring ring-3"></div>
                <div class="core-glow" id="core-glow"></div>
                <div class="nila-text">N.I.L.A.</div>
            </div>
        </div>

        <div class="right-col">
            <div class="hud-panel" style="flex: 1;">
                <div class="panel-header">
                    <span>System Diagnostic</span>
                    <span>NET_01</span>
                </div>
                <ul class="feed-list">
                    <li class="feed-item"><span>NODE_ALPHA</span><span style="color:#4cd137;">LINKED</span></li>
                    <li class="feed-item"><span>FIREWALL</span><span style="color:#4cd137;">ACTIVE</span></li>
                    <li class="feed-item"><span>IPC SERVER</span><span style="color:#4cd137;">PORT 8765</span></li>
                    <li class="feed-item"><span>SWAP MEMORY</span><span id="swap-val">0%</span></li>
                    <li class="feed-item"><span>THREAT DETECT</span><span style="color:#4cd137;">0 FOUND</span></li>
                </ul>
            </div>
        </div>

        <div class="bottom-row">
            <div class="hud-panel terminal-log" id="terminal" style="grid-column: 1 / -1;">
                <p>N.I.L.A. Display Monitor Initialized.</p>
                <p>Listening for backend execution events on ws://127.0.0.1:8765...</p>
            </div>
        </div>
    </div>

    <script>
        function updateClock() {
            const now = new Date();
            document.getElementById('clock').innerText = now.toTimeString().split(' ')[0];
        }
        setInterval(updateClock, 1000);
        updateClock();

        function updateRealTelemetry(cpu, ram, disk, procs, swap) {
            document.getElementById('cpu-val').innerText = cpu + '%';
            document.getElementById('cpu-bar').style.width = cpu + '%';

            document.getElementById('ram-val').innerText = ram + '%';
            document.getElementById('ram-bar').style.width = ram + '%';

            document.getElementById('disk-val').innerText = disk + '%';
            document.getElementById('disk-bar').style.width = disk + '%';

            document.getElementById('proc-val').innerText = procs;
            document.getElementById('swap-val').innerText = swap + '%';
        }

        function addTerminalLine(text) {
            const terminal = document.getElementById('terminal');
            const newP = document.createElement('p');
            const time = new Date().toTimeString().split(' ')[0];
            newP.innerText = '[' + time + '] ' + text;
            terminal.appendChild(newP);
            terminal.scrollTop = terminal.scrollHeight;
            if (terminal.children.length > 15) {
                terminal.removeChild(terminal.children[0]);
            }
        }

        function handleIPC(data) {
            if(data.type === 'assistant_token') {
                addTerminalLine('N.I.L.A.: ' + data.payload.text);
                document.getElementById('sys-status-text').innerText = 'ONLINE';
            } else if(data.type === 'tool_start') {
                addTerminalLine('Executing Tool: ' + data.payload.tool_name);
                document.getElementById('sys-status-text').innerText = 'EXECUTING';
            } else if(data.type === 'tool_end') {
                document.getElementById('sys-status-text').innerText = 'ONLINE';
            }
        }
    </script>
</body>
</html>"""

        self.web_view.setHtml(html_content, QUrl("http://localhost/"))
        layout.addWidget(self.web_view)

    def setup_telemetry(self):
        psutil.cpu_percent(interval=None)
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self.send_real_telemetry)
        self.telemetry_timer.start(1000)

    def send_real_telemetry(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('C:\\').percent
            procs = len(psutil.pids())
            swap = psutil.swap_memory().percent

            js_call = f"updateRealTelemetry({cpu}, {ram}, {disk}, {procs}, {swap});"
            self.web_view.page().runJavaScript(js_call)
        except Exception:
            pass

    def handle_ipc_message(self, data_dict):
        json_str = json.dumps(data_dict)
        js = f"handleIPC({json_str});"
        self.web_view.page().runJavaScript(js)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    hud = DisplayOnlyHUD()
    hud.show()
    sys.exit(app.exec())