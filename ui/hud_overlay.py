import sys
import json
import asyncio
import time
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QTextEdit, QLineEdit, QPushButton, QFrame, QProgressBar)
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QPolygonF
from PyQt6.QtCore import QPointF
import websockets
import psutil

class IPCManager(QThread):
    message_received = pyqtSignal(dict)
    connection_status = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.loop = None
        self.ws = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect_and_listen())

    async def connect_and_listen(self):
        uri = "ws://127.0.0.1:8765"
        while True:
            try:
                async with websockets.connect(uri) as ws:
                    self.ws = ws
                    self.connection_status.emit(True)
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        self.message_received.emit(data)
            except Exception:
                self.connection_status.emit(False)
                await asyncio.sleep(2)

    def send_intent(self, text: str):
        if self.ws and self.loop:
            payload = json.dumps({
                "type": "user_intent",
                "payload": {"text": text}
            })
            asyncio.run_coroutine_threadsafe(self.ws.send(payload), self.loop)

class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "IDLE"
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_wave)
        self.timer.start(30)

    def set_state(self, state: str):
        self.state = state

    def update_wave(self):
        self.phase += 0.1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        mid_y = height / 2.0

        if self.state == "THINKING":
            color = QColor(176, 0, 255)
            freq = 0.08
            amp = 18.0
        elif self.state == "EXECUTING":
            color = QColor(0, 255, 136)
            freq = 0.12
            amp = 22.0
        else:
            color = QColor(0, 240, 255)
            freq = 0.04
            amp = 6.0

        pen = QPen(color, 2)
        painter.setPen(pen)

        import math
        points = []
        for x in range(0, width, 2):
            y = mid_y + math.sin(x * freq + self.phase) * amp
            points.append(QPointF(x, y))

        if points:
            painter.drawPolyline(points)

class AdvancedNILAHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.drag_position = QPoint()
        self.ipc = IPCManager()
        self.init_ui()
        self.setup_ipc()
        self.setup_telemetry()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(520, 360)
        self.move(120, 120)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 14, 23, 0.92);
                border: 1.5px solid #00F0FF;
                border-radius: 14px;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 14, 16, 14)

        # Header Bar
        header_layout = QHBoxLayout()
        self.orb = QLabel("●")
        self.orb.setStyleSheet("color: #00F0FF; font-size: 16px; border: none; background: transparent;")
        
        self.status_title = QLabel("N.I.L.A. // ONLINE")
        self.status_title.setStyleSheet("color: #00F0FF; font-weight: bold; font-family: 'Consolas'; font-size: 13px; border: none; background: transparent;")

        self.telemetry_label = QLabel("CPU: --% | RAM: --%")
        self.telemetry_label.setStyleSheet("color: #5580A0; font-size: 10px; font-family: 'Consolas'; border: none; background: transparent;")

        header_layout.addWidget(self.orb)
        header_layout.addWidget(self.status_title)
        header_layout.addStretch()
        header_layout.addWidget(self.telemetry_label)
        container_layout.addLayout(header_layout)

        # Waveform Canvas Visualizer
        self.waveform = WaveformWidget(self)
        self.waveform.setFixedHeight(36)
        self.waveform.setStyleSheet("border: none; background: transparent;")
        container_layout.addWidget(self.waveform)

        # Console Stream Display
        self.console = QTextEdit(self)
        self.console.setReadOnly(True)
        self.console.setPlainText("System online. IPC linked on ws://127.0.0.1:8765.\nType a command to execute...")
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 0.45);
                color: #D0E5F5;
                border: 1px solid rgba(0, 240, 255, 0.25);
                border-radius: 8px;
                font-family: 'Segoe UI Variable Text', 'Segoe UI';
                font-size: 13px;
                padding: 8px;
            }
        """)
        container_layout.addWidget(self.console)

        # Command Input Field
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Ask N.I.L.A. or type system command...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(20, 32, 48, 0.85);
                color: #FFFFFF;
                border: 1px solid rgba(0, 240, 255, 0.45);
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #00F0FF;
            }
        """)
        self.input_field.returnPressed.connect(self.send_command)

        self.btn_send = QPushButton("EXECUTE", self)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #00F0FF;
                color: #050811;
                font-weight: bold;
                font-family: 'Consolas';
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #00C8FF;
            }
        """)
        self.btn_send.clicked.connect(self.send_command)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.btn_send)
        container_layout.addLayout(input_layout)

        main_layout.addWidget(self.container)

    def setup_ipc(self):
        self.ipc.message_received.connect(self.handle_ipc_message)
        self.ipc.connection_status.connect(self.handle_connection_status)
        self.ipc.start()

    def setup_telemetry(self):
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self.update_telemetry)
        self.telemetry_timer.start(1500)

    def update_telemetry(self):
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            self.telemetry_label.setText(f"CPU: {cpu}% | RAM: {ram}%")
        except Exception:
            pass

    def handle_connection_status(self, connected: bool):
        if connected:
            self.status_title.setText("N.I.L.A. // ONLINE")
            self.orb.setStyleSheet("color: #00F0FF; font-size: 16px; border: none; background: transparent;")
        else:
            self.status_title.setText("N.I.L.A. // DISCONNECTED")
            self.orb.setStyleSheet("color: #FF0055; font-size: 16px; border: none; background: transparent;")

    def handle_ipc_message(self, data: dict):
        msg_type = data.get("type", "")
        payload = data.get("payload", {})

        if msg_type == "assistant_token":
            text = payload.get("text", "")
            self.console.setPlainText(text)
            self.status_title.setText("N.I.L.A. // IDLE")
            self.orb.setStyleSheet("color: #00F0FF; font-size: 16px; border: none; background: transparent;")
            self.waveform.set_state("IDLE")

        elif msg_type == "tool_start":
            tool_name = payload.get("tool_name", "")
            self.status_title.setText(f"EXECUTING // {tool_name.upper()}")
            self.orb.setStyleSheet("color: #00FF88; font-size: 16px; border: none; background: transparent;")
            self.waveform.set_state("EXECUTING")

        elif msg_type == "tool_end":
            self.status_title.setText("N.I.L.A. // COMPLETED")
            self.orb.setStyleSheet("color: #00F0FF; font-size: 16px; border: none; background: transparent;")
            self.waveform.set_state("IDLE")

    def send_command(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.console.setPlainText(f"User > {text}\nProcessing intent...")
        self.status_title.setText("N.I.L.A. // THINKING...")
        self.orb.setStyleSheet("color: #B000FF; font-size: 16px; border: none; background: transparent;")
        self.waveform.set_state("THINKING")

        self.ipc.send_intent(text)
        self.input_field.clear()

    # Window Dragging Logic
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    hud = AdvancedNILAHUD()
    hud.show()
    sys.exit(app.exec())