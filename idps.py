import os
import time
import psutil
import socket
import logging
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from sklearn.ensemble import IsolationForest
import numpy as np

# === CONFIGURATION ===
paths = ["./lab", "./important_folder", "./monitoring_dir"]  # Add your directories here

# === SETUP DIRECTORIES IF THEY DON'T EXIST ===
for path in paths:
    if not os.path.exists(path):
        print(f"[INFO] Directory {path} does not exist. Creating it.")
        os.makedirs(path)

# === LOGGING SETUP ===
logging.basicConfig(level=logging.INFO)

file_log = open("file_system_log.txt", "a")
net_log = open("network_connections_log.txt", "a")
proc_log = open("processes_log.txt", "a")

# === EVENT HANDLER FOR FILE MONITORING ===
class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        log_event("MODIFIED", event.src_path)

    def on_created(self, event):
        log_event("CREATED", event.src_path)

    def on_deleted(self, event):
        log_event("DELETED", event.src_path)

    def on_moved(self, event):
        log_event("MOVED", f"{event.src_path} to {event.dest_path}")

def log_event(event_type, detail):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    msg = f"[{timestamp}] {event_type}: {detail}\n"
    file_log.write(msg)
    file_log.flush()
    print(msg, end="")

# === PROCESS MONITORING ===
def monitor_processes(events):
    seen = set()
    while True:
        for proc in psutil.process_iter(['pid', 'name']):
            pid = proc.info['pid']
            if pid not in seen:
                seen.add(pid)
                msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] New Process Started: {proc.info['name']} (PID {pid})\n"
                proc_log.write(msg)
                proc_log.flush()
                print(msg, end="")
                events.append(1)
        time.sleep(5)

# === NETWORK MONITORING ===
def monitor_network(events):
    seen = set()
    while True:
        connections = psutil.net_connections()
        for conn in connections:
            if conn.status == "ESTABLISHED" and conn.raddr:
                remote_ip = conn.raddr.ip
                if remote_ip not in seen:
                    seen.add(remote_ip)
                    msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] New Connection: {remote_ip}\n"
                    net_log.write(msg)
                    net_log.flush()
                    print(msg, end="")
                    events.append(1)
        time.sleep(5)

# === ANOMALY DETECTION ===
def anomaly_detector(events):
    clf = IsolationForest(contamination=0.1)
    window = []

    while True:
        time.sleep(10)
        count = len(events)
        events.clear()
        window.append([count])
        if len(window) > 10:
            window.pop(0)
        if len(window) >= 5:
            pred = clf.fit_predict(window)
            if pred[-1] == -1:
                print(f"[ALERT] Potential anomaly detected! Event count in last 10s: {count}")

# === MAIN FUNCTION ===
def main():
    print("[INFO] Starting IDPS...")

    event_handler = FileChangeHandler()
    observer = Observer()

    for path in paths:
        print(f"[INFO] Monitoring directory: {path}")
        observer.schedule(event_handler, path, recursive=True)

    observer.start()

    events = []

    # Start monitoring threads
    threading.Thread(target=monitor_processes, args=(events,), daemon=True).start()
    threading.Thread(target=monitor_network, args=(events,), daemon=True).start()
    threading.Thread(target=anomaly_detector, args=(events,), daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

    # Close logs
    file_log.close()
    net_log.close()
    proc_log.close()
    print("[INFO] IDPS stopped.")

if __name__ == "__main__":
    main()
