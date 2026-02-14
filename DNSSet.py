import sys
import subprocess
import threading
import re
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from concurrent.futures import ThreadPoolExecutor

DNS_LIST = sorted(list(set([
    "1.0.0.1","1.1.1.1","1.1.4.1","1.4.1.1","4.2.2.1","4.2.2.2","4.2.2.3","4.2.2.4",
    "4.2.2.5","4.2.2.6","8.20.247.20","8.26.56.26","8.8.4.4","8.8.8.8","9.9.9.10",
    "9.9.9.9","10.202.10.10","10.202.10.102","10.202.10.11","10.202.10.202",
    "45.90.28.230","45.90.30.230","64.6.64.6","64.6.65.6","74.82.42.42","78.157.42.100",
    "78.157.42.101","80.67.169.12","80.67.169.40","80.80.80.80","80.80.81.81","84.200.69.80",
    "84.200.70.40","86.54.11.100","86.54.11.200","91.239.100.100","94.140.14.14","94.140.15.15",
    "149.112.112.10","149.112.112.112","156.154.70.1","156.154.70.22","156.154.70.5","156.154.71.1",
    "156.154.71.22","156.154.71.5","178.22.122.100","185.51.200.2","195.46.39.39","195.46.39.40",
    "195.92.195.94","195.92.195.95","198.153.192.1","198.153.194.1","199.2.252.10","199.85.126.10",
    "199.85.127.10","204.69.234.1","204.74.101.1","204.97.212.10","204.117.214.10","205.171.2.65",
    "205.171.3.65","208.67.220.220","208.67.220.222","208.67.222.220","208.67.222.222"
])))

INTERFACE_NAME = "Wi-Fi"
CHECK_INTERVAL = 5
PING_OK = 75   #Decent ping
PING_BAD = 90   #High ping
MAX_WORKERS = 15

class Signals(QObject):
    update_table = pyqtSignal(str, str, str)
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

class DNSMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart DNS Switcher - Optimized")
        self.setGeometry(200, 100, 720, 600)

        self.current_primary = None
        self.current_secondary = None
        self.running = False
        self.signals = Signals()

        self.init_ui()

        self.signals.update_table.connect(self.update_table_item)
        self.signals.log_signal.connect(self.append_log)
        self.signals.status_signal.connect(self.update_status_label)

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_dns_change)
        self.timer.start(2000)

    def init_ui(self):
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setRowCount(len(DNS_LIST))
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["DNS", "Ping (ms)", "Status"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for i, dns in enumerate(DNS_LIST):
            self.table.setItem(i, 0, QTableWidgetItem(dns))
            self.table.setItem(i, 1, QTableWidgetItem("---"))
            self.table.setItem(i, 2, QTableWidgetItem("---"))

        layout.addWidget(self.table)

        self.status_label = QLabel("Primary: - | Secondary: -")
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Monitoring")
        self.start_btn.clicked.connect(self.start_monitor)
        self.stop_btn = QPushButton("Stop Monitoring")
        self.stop_btn.clicked.connect(self.stop_monitor)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.setLayout(layout)

    def append_log(self, text):
        self.log_box.append(text)

    def update_table_item(self, dns, ping, status):
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).text() == dns:
                self.table.item(i, 1).setText(ping)
                self.table.item(i, 2).setText(status)
                break

    def update_status_label(self, text):
        self.status_label.setText(text)

    def ping_dns(self, ip):
        try:
            output = subprocess.check_output(
                ["ping", "-n", "1", "-w", "1000", ip],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            match = re.search(r"time=(\d+)ms", output)
            if match:
                return int(match.group(1))
        except:
            pass
        return None

    def set_dns(self, primary, secondary):
        try:
            cmd = (
                f'Set-DnsClientServerAddress -InterfaceAlias "{INTERFACE_NAME}" '
                f'-ServerAddresses ("{primary}","{secondary}")'
            )
            subprocess.run(["powershell", "-Command", cmd], check=True)
            self.signals.log_signal.emit(f"DNS successfully changed → {primary} , {secondary}")
            self.current_primary = primary
            self.current_secondary = secondary
            self.signals.status_signal.emit(f"Primary: {primary} | Secondary: {secondary}")
        except subprocess.CalledProcessError as e:
            self.signals.log_signal.emit(f"Error changing DNS: {e}")

    def monitor_loop(self):
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            while self.running:
                futures = {executor.submit(self.ping_dns, dns): dns for dns in DNS_LIST}
                results = []
                for future in futures:
                    dns = futures[future]
                    ping = future.result()
                    status = "OK" if ping else "Fail"
                    ping_text = str(ping) if ping else "Timeout"
                    self.signals.update_table.emit(dns, ping_text, status)
                    if ping is not None:
                        results.append((dns, ping))

                results.sort(key=lambda x: x[1])
                need_switch = False

                if self.current_primary and self.current_secondary:
                    p1 = self.ping_dns(self.current_primary)
                    p2 = self.ping_dns(self.current_secondary)
                    if p1 is None or p2 is None or p1 > PING_BAD or p2 > PING_BAD:
                        need_switch = True
                else:
                    need_switch = True

                if need_switch and len(results) >= 2:
                    best1, p1 = results[0]
                    best2, p2 = results[1]
                    if p1 <= PING_OK:
                        self.signals.status_signal.emit("Switching DNS...")
                        self.signals.log_signal.emit(f"Switching DNS → {best1}, {best2}")
                        self.set_dns(best1, best2)

                threading.Event().wait(CHECK_INTERVAL)

    def start_monitor(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.monitor_loop, daemon=True).start()
            self.signals.log_signal.emit("Monitoring started")

    def stop_monitor(self):
        if self.running:
            self.running = False
            self.signals.log_signal.emit("Monitoring stopped")

    def check_dns_change(self):
        try:
            output = subprocess.check_output(
                ["powershell", "-Command",
                 f'Get-DnsClientServerAddress -InterfaceAlias "{INTERFACE_NAME}" | Select-Object -ExpandProperty ServerAddresses'],
                universal_newlines=True
            ).strip()
            current = [x.strip() for x in output.split('\n') if x.strip()]
            if current:
                primary = current[0]
                secondary = current[1] if len(current) > 1 else None
                if primary != self.current_primary or secondary != self.current_secondary:
                    self.signals.log_signal.emit(f"DNS manually changed! Current: {current}")
                    self.current_primary = primary
                    self.current_secondary = secondary
                    self.signals.status_signal.emit(f"Primary: {primary} | Secondary: {secondary if secondary else '-'}")
        except Exception as e:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DNSMonitor()
    window.show()
    sys.exit(app.exec())
