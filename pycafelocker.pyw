import datetime
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk

# Define the IP address and port where the script will listen
HOST = '0.0.0.0'  # Listen on all network interfaces
LOCKER_PORT = 22277

# text file to redirect the output of the script, None to disable
output_file = f"C:\\PyCafe\\Logs\\pycafelocker\\pycafelocker_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.log"
sys.stdout = open(output_file, "w") if output_file is not None else sys.__stdout__
sys.stderr = sys.stdout
logs_flushing_rate = 30  # in seconds

def lock_pc():
    try:
        result = subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
        if result.returncode == 0:
            print("PC locked.")
        else:
            print(f"Error locking PC: {result.stderr}")
    except Exception as e:
        print(f"Error locking PC: {e}")

def listen_for_connections():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, LOCKER_PORT))
        s.listen()
        print(f"Listening on {HOST}:{LOCKER_PORT}")

        while True:
            conn, _ = s.accept()
            with conn:
                try:
                    data = conn.recv(1024).decode('utf-8')
                    print(f"Received: {data}")

                    if not data:
                        continue
                    if data.startswith("lock"):
                        lock_pc()
                    else:
                        print("Invalid command received.")
                except Exception as e:
                    print(f"Error: {e}")
                    continue

# log flushing thread
def update_flush_logs():
    while True:
        sys.stdout.flush()
        time.sleep(logs_flushing_rate)

# Start the log flushing thread
flush_logs_thread = threading.Thread(target=update_flush_logs, daemon=True)
flush_logs_thread.start()

# Start the server
listen_for_connections()
