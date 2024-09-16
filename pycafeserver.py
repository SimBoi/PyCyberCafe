import tkinter as tk
from tkinter import messagebox
import random
import string
import socket
import threading
import time

# List of café PCs IP addresses
PORT = 22077
CLOCK_PORT = 22177
CAFE_PCS_IPS = [
    "10.100.102.23",
    "10.100.102.16",
    "10.100.102.27",
    "10.100.102.31",
    "10.100.102.14",
    "10.100.102.10",
    "10.100.102.8",
]

# update rate
update_ping_rate = 10 # in seconds
update_sessions_rate = 60 # in seconds
update_ui_rate = 100 # in milliseconds

# List to keep track of active sessions (index, time_left in minutes)
active_sessions = []
# Dictionary to store current passwords for each café PC
pc_passwords = {i: None for i in range(len(CAFE_PCS_IPS))}
# List to store the "alive" status of each PC (True if alive, False if not)
pc_statuses = {i: True for i in range(len(CAFE_PCS_IPS))}

# Lock to prevent race conditions between threads
lock = threading.Lock()

# Create the main UI window and widgets
root = tk.Tk()
labels = []
buttons = []
end_buttons = []
duration_entry = None

def start():
    # get already running sessions
    for index, ip in enumerate(CAFE_PCS_IPS):
        data = send_command(ip, PORT, "get_timer", receive_response=True, silent_fail=True)
        if data is not None and data.isdigit() and data != "0":
            active_sessions.append((index, int(data)))
            print(f"Found active session on café PC {index} ({ip}). Time left: {int(data)//60} minutes.")

    start_ui()

    # Start the pinging update loop in a separate thread
    ping_thread = threading.Thread(target=update_ping, daemon=True)
    ping_thread.start()

    # Start the session timer update loop in a separate thread
    timer_thread = threading.Thread(target=update_sessions, daemon=True)
    timer_thread.start()

    # Start the UI update loop in the main thread
    root.after(update_ui_rate, update_ui)
    root.mainloop()

# UI update loop on the main thread

def update_ui():
    # Update the UI based on session status and alive status
    with lock:
        for index, (password, timer) in enumerate(zip(pc_passwords.values(), [0]*len(CAFE_PCS_IPS))):
            if any(i == index for i, _ in active_sessions):
                # If there's an active session, find the remaining timer
                timer = next(tl for i, tl in active_sessions if i == index)
                status = f"Session Time Left: {int(timer)//60} minutes"
                buttons[index].config(text="Extend Session", command=extend_session_button(index))
                end_buttons[index].config(state=tk.NORMAL)
            else:
                status = "Available"
                buttons[index].config(text="Start Session", command=start_session_button(index))
                end_buttons[index].config(state=tk.DISABLED)
            
            # Add PC "alive" status to the UI
            alive_status = "Alive" if pc_statuses[index] else "Not Responding"
            labels[index].config(text=f"PC-{index+1}\nPassword: {password}\n{status}\n{alive_status}")
    
    root.after(update_ui_rate, update_ui)  # Update UI every second

def start_ui():
    global root, labels, buttons, end_buttons, duration_entry
    root.title("Café PC Management")
    for idx, ip in enumerate(CAFE_PCS_IPS):
        frame = tk.Frame(root, width=200, height=100, borderwidth=2, relief="groove")
        frame.grid(row=idx//2, column=idx%2, padx=10, pady=10)

        label = tk.Label(frame, text=f"PC-{idx+1}\nPassword: {pc_passwords[idx]}\nAvailable", justify="left")
        label.pack(padx=5, pady=5)
        labels.append(label)

        button = tk.Button(frame, text="Start Session", command=start_session_button(idx))
        button.pack(padx=5, pady=5)
        buttons.append(button)

        end_button = tk.Button(frame, text="End Session", command=end_session_button(idx), state=tk.DISABLED)
        end_button.pack(padx=5, pady=5)
        end_buttons.append(end_button)

    duration_entry = tk.Entry(root)
    duration_entry.insert(0, "Duration in minutes")
    duration_entry.grid(row=len(CAFE_PCS_IPS)//2 + 1, column=0, columnspan=2, padx=10, pady=10)

def start_session(index, session_duration_minutes):
    if index < 0 or index >= len(CAFE_PCS_IPS):
        display_error("Invalid café PC index.")
        return
    
    cafe_pc_ip = CAFE_PCS_IPS[index]
    new_password = generate_password()
    with lock:
        if any(i == index for i, _ in active_sessions):
            display_error(f"A session is already active on this café PC-{index+1}.")
            return
        
        # change password
        if not send_command(cafe_pc_ip, PORT, f"change_password {new_password}"):
            display_error(f"Failed to start session on café PC-{index+1}.")
            return
        pc_passwords[index] = new_password

        # set timer
        if not send_command(cafe_pc_ip, PORT, f"set_timer {session_duration_minutes*60}"):
            display_error(f"Failed to set timer on café PC-{index+1}.")
            return
        active_sessions.append((index, session_duration_minutes * 60))
        
        print(f"Session started on café PC {index} ({cafe_pc_ip}) for {session_duration_minutes} minutes. Password: {new_password}")

def extend_session(index, extra_time_minutes):
    with lock:
        for i, (pc_index, time_left) in enumerate(active_sessions):
            if pc_index == index:
                if not send_command(CAFE_PCS_IPS[index], PORT, f"set_timer {time_left + extra_time_minutes*60}"):
                    display_error(f"Failed to extend session on café PC-{index+1}.")
                    return
                if not send_command(CAFE_PCS_IPS[index], PORT, f"change_password {pc_passwords[index]}"):
                    display_error(f"Failed to extend session on café PC-{index+1}.")
                    return
                active_sessions[i] = (pc_index, time_left + extra_time_minutes * 60)
                print(f"Extended session on café PC {index} by {extra_time_minutes} minutes. New time left: {time_left//60 + extra_time_minutes} minutes")
                return

def end_session(index):
    with lock:
        for i, (pc_index, time_left) in enumerate(active_sessions):
            if pc_index == index:
                cafe_pc_ip = CAFE_PCS_IPS[index]
                if not send_command(cafe_pc_ip, PORT, f"set_timer 0"):
                    display_error(f"Failed to end session on café PC-{index+1}.")
                    return
                if not send_command(cafe_pc_ip, PORT, f"restart"):
                    display_error(f"Failed to end session on café PC-{index+1}.")
                    return
                print(f"Session ended for café PC {index} with time left: {time_left*60} minutes. restarting PC.")
                pc_passwords[index] = None
                # Remove session from active_sessions
                active_sessions.pop(i)

def start_session_button(index):
    def start():
        duration = int(duration_entry.get())
        start_session(index, duration)
    return start

def extend_session_button(index):
    def extend():
        extra_time = int(duration_entry.get())
        extend_session(index, extra_time)
    return extend

def end_session_button(index):
    def end():
        end_session(index)
    return end

# ping thread

def update_ping():
    while True:
        for idx, ip in enumerate(CAFE_PCS_IPS):
            ping_pc(ip, idx)
        time.sleep(update_ping_rate)

def ping_pc(ip, index):
    if send_command(ip, PORT, "ping", receive_response=True, silent_fail=True) == "pong":
        with lock:
            pc_statuses[index] = True
    else:
        if pc_statuses[index]:
            display_error(f"PC-{index+1} is not responding.")
        with lock:
            pc_statuses[index] = False

# session timer thread

def update_sessions():
    while True:
        with lock:
            # Update the session timers
            for i in range(len(active_sessions)):
                active_sessions[i] = (active_sessions[i][0], max(0, active_sessions[i][1] - update_sessions_rate))
                
            # Check for timed out sessions and lock the PC with a random password
            for i, (index, time_left) in enumerate(active_sessions):
                if time_left <= 0:
                    cafe_pc_ip = CAFE_PCS_IPS[index]
                    if not send_command(cafe_pc_ip, PORT, f"set_timer 0"):
                        display_error(f"Failed to end session on café PC-{index+1}.")
                        continue
                    if not send_command(cafe_pc_ip, PORT, f"lock {generate_password()}"):
                        display_error(f"Failed to lock café PC-{index+1}.")
                        continue
                    print(f"Session timed out for café PC {index+1}. PC locked.")
        
        time.sleep(update_sessions_rate)

# Helper functions

def generate_password(length=3, characters=string.digits):
    return ''.join(random.choice(characters) for i in range(length))

def display_error(error_info):
    def display_non_blocking_error(error_info):
        msg_box = tk.Tk()
        msg_box.withdraw()
        messagebox.showerror("Error", error_info, parent=msg_box)
        msg_box.destroy()
    threading.Thread(target=display_non_blocking_error, args={error_info}).start()

def send_command(ip, port, command, receive_response=False, silent_fail=False):
    for i in range(2):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((ip, port))
                s.sendall(command.encode('utf-8'))
                print(f"Sent command to {ip}: {command}")
                return s.recv(1024).decode('utf-8') if receive_response else True
        except Exception as e:
            if not silent_fail:
                msg = f"Error sending command to {ip}: {command}\nError: {e}\nAttempt {i+1}"
                print(msg)
                display_error(msg)
    return None if receive_response else False

start()
