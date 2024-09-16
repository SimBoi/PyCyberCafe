import datetime
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk

# Define the IP address and port where the script will listen
HOST = '0.0.0.0'  # Listen on all network interfaces
CLOCK_PORT = 22177

# text file to redirect the output of the script, None to disable
output_file = f"C:\\PyCafe\\Logs\\pycafeclock\\pycafeclock_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.log"
sys.stdout = open(output_file, "w") if output_file is not None else sys.__stdout__
sys.stderr = sys.stdout
logs_flushing_rate = 30  # in seconds

lock = threading.Lock()
current_time = 0 # in seconds

def update_time():
    with lock:
        global current_time
        current_time = max(0, current_time - 1)
        hours = current_time // 3600
        minutes = (current_time % 3600) // 60
        time_label.config(text=f"Session: {hours:02d}:{minutes:02d}", font=("Helvetica", 16))
        root.after(1000, update_time)

def listen_for_connections():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, CLOCK_PORT))
        s.listen()
        print(f"Listening on {HOST}:{CLOCK_PORT}")

        while True:
            conn, addr = s.accept()
            with conn:
                try:
                    data = conn.recv(1024).decode('utf-8')
                    print(f"Received: {data}")

                    if not data:
                        continue
                    if data.startswith("set_timer"):
                        cmd_args = data.split(" ")
                        if len(cmd_args) == 2:
                            with lock:
                                global current_time
                                current_time = int(cmd_args[1])
                        else:
                            print("Invalid command received.")
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

# Start the server
listen_thread = threading.Thread(target=listen_for_connections, daemon=True)
listen_thread.start()

# Start the log flushing thread
flush_logs_thread = threading.Thread(target=update_flush_logs, daemon=True)
flush_logs_thread.start()

# Create the main window
root = tk.Tk()
root.title("Cafe Clock")

# Create the time label
time_label = tk.Label(root, text="Session: 00:00", font=("Helvetica", 16))
time_label.pack(padx=10, pady=10)

root.after(1000, update_time)
root.mainloop()
