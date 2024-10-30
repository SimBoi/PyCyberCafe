import glob
import json
import os
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

# file containing the IPs of the cafe PCs
ips_file_path = "ips.txt"
# file containing the offline timers of the cafe PCs
offline_timers_file_path = "offline_timers.txt"
# json file to store the state of the cafe
state_file_paths = "cafe_state_*.json"

# update rate
update_ping_rate = 30 # in seconds
update_sessions_rate = 60 # in seconds
update_ui_rate = 100 # in milliseconds

# list of cafe PCs IPs
ips = []
try:
    with open(ips_file_path, "r") as f:
        # read the IPs from the file line by line
        lines = f.read().splitlines()
        # remove whitespaces
        lines = [line.strip() for line in lines]
        # remove empty lines
        lines = [line for line in lines if line]
        # remove comments
        lines = [line for line in lines if not line.startswith("#")]
        ips = lines
except Exception as e:
    print(f"Error reading IPs from file: {e}")
    exit(1)

# list of lists of cafe offline timers
offline_timer_titles = []
tab_names = []
try:
    with open(offline_timers_file_path, "r") as f:
        # read the IPs from the file line by line
        lines = f.read().splitlines()
        # remove whitespaces
        lines = [line.strip() for line in lines]
        # remove empty lines
        lines = [line for line in lines if line]
        # remove comments
        lines = [line for line in lines if not line.startswith("#")]
        
        # separate the offline timers by tabs
        for line in lines:
            if line.startswith("Tab:"):
                tab_names.append(line[4:])
                offline_timer_titles.append([])
            else:
                offline_timer_titles[-1].append(line)
except Exception as e:
    print(f"Error reading offline timers from file: {e}")
    exit(1)

# List to keep track of active sessions (index, time_left in minutes, is_paused)
active_sessions = []
# List of lists to store the offline timers [(index, time_left in seconds, is_paused)*, ...]
active_offline_timers = [[] for _ in tab_names]
# Dictionary to store current passwords for each café PC
pc_passwords = [None for _ in ips]
# List to store the "alive" status of each PC (True if alive, False if not)
pc_statuses = [2 for _ in ips]

# Lock to prevent race conditions between threads
lock = threading.Lock()

# Create the main UI window and widgets for the café PCs
root = tk.Tk()
labels = []
buttons = []
pause_buttons = []
end_buttons = []
duration_entry = None

# Create the main UI window and widgets for the offline timers
roots_offline_timers = [tk.Tk() for _ in tab_names]
labels_offline_timers = [[] for _ in tab_names]
buttons_offline_timers = [[] for _ in tab_names]
pause_buttons_offline_timers = [[] for _ in tab_names]
end_buttons_offline_timers = [[] for _ in tab_names]
duration_entry_offline_timers = [None for _ in tab_names]

def start():
    # Load the state of the cafe
    load_state()
    for idx, _ in enumerate(ips):
        threading.Thread(target=restore_client, args=(idx,), daemon=True).start()

    # Start the UI in the main thread
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
    with lock:
        # Update the UI for the café PCs
        for index, password in enumerate(pc_passwords):
            if any(i == index for i, _, _ in active_sessions):
                # If there's an active session, find the remaining timer and the is_paused status
                timer, is_paused = next((tl, p) for i, tl, p in active_sessions if i == index)
                if is_paused:
                    session_status = f"Session Paused, {int(timer)//60} minutes left"
                    pause_buttons[index].config(text="Resume Session", command=resume_session_button(index))
                else:
                    session_status = f"Session Time Left: {int(timer)//60} minutes"
                    pause_buttons[index].config(text="Pause Session", command=pause_session_button(index))
                buttons[index].config(text="Extend Session", command=extend_session_button(index))
                pause_buttons[index].config(state=tk.NORMAL)
                end_buttons[index].config(state=tk.NORMAL)
                if timer > 0:
                    if is_paused:
                        labels[index].config(bg="lightyellow")
                    else:
                        labels[index].config(bg="lightblue")
                else:
                    labels[index].config(bg="lightcoral")
            else:
                session_status = "No Session"
                buttons[index].config(text="Start Session", command=start_session_button(index))
                pause_buttons[index].config(state=tk.DISABLED)
                end_buttons[index].config(state=tk.DISABLED)
                labels[index].config(bg="lightgray")

            if pc_statuses[index] == 2:
                alive_status = "Alive"
            elif pc_statuses[index] == 1:
                alive_status = "Alive, Locker Dead"
            else:
                alive_status = "Dead"
            labels[index].config(text=f"PC-{index+1}\nPassword: {password}\n{session_status}\n{alive_status}")

        # Update the UI for the offline timers
        for tab_idx, tab in enumerate(roots_offline_timers):
            for index, title in enumerate(offline_timer_titles[tab_idx]):
                if any(i == index for i, _, _ in active_offline_timers[tab_idx]):
                    # If there's an active offline timer, find the remaining timer
                    timer, is_paused = next((tl, p) for i, tl, p in active_offline_timers[tab_idx] if i == index)
                    if is_paused:
                        session_status = f"Session Paused, {int(timer)//60} minutes left"
                        pause_buttons_offline_timers[tab_idx][index].config(text="Resume Session", command=resume_offline_session_button(tab_idx, index))
                    else:
                        session_status = f"Session Time Left: {int(timer)//60} minutes"
                        pause_buttons_offline_timers[tab_idx][index].config(text="Pause Session", command=pause_offline_session_button(tab_idx, index))
                    buttons_offline_timers[tab_idx][index].config(text="Extend Session", command=extend_offline_session_button(tab_idx, index))
                    pause_buttons_offline_timers[tab_idx][index].config(state=tk.NORMAL)
                    end_buttons_offline_timers[tab_idx][index].config(state=tk.NORMAL)
                    if timer > 0:
                        if is_paused:
                            labels_offline_timers[tab_idx][index].config(bg="lightyellow")
                        else:
                            labels_offline_timers[tab_idx][index].config(bg="lightblue")
                    else:
                        labels_offline_timers[tab_idx][index].config(bg="lightcoral")
                else:
                    session_status = "No Session"
                    buttons_offline_timers[tab_idx][index].config(text="Start Session", command=start_offline_session_button(tab_idx, index))
                    pause_buttons_offline_timers[tab_idx][index].config(state=tk.DISABLED)
                    end_buttons_offline_timers[tab_idx][index].config(state=tk.DISABLED)
                    labels_offline_timers[tab_idx][index].config(bg="lightgray")
                labels_offline_timers[tab_idx][index].config(text=f"{title}\n{session_status}")

    root.after(update_ui_rate, update_ui)  # Update UI every second

def start_ui():
    global root, labels, buttons, end_buttons, pause_buttons, duration_entry, roots_offline_timers, labels_offline_timers, buttons_offline_timers, end_buttons_offline_timers, pause_buttons_offline_timers, duration_entry_offline_timers
    
    # Create the main UI window and widgets for the café PCs
    root.title("Café PC Management")
    for idx, _ in enumerate(ips):
        frame = tk.Frame(root, width=200, height=100, borderwidth=2, relief="groove")
        frame.grid(row=idx//2, column=idx%2, padx=10, pady=10)

        label = tk.Label(frame, text=f"PC-{idx+1}\nPassword: {pc_passwords[idx]}\nAvailable", justify="left")
        label.pack(padx=5, pady=5)
        labels.append(label)

        button = tk.Button(frame, text="Start Session", command=start_session_button(idx))
        button.pack(padx=5, pady=5)
        buttons.append(button)

        pause_button = tk.Button(frame, text="Pause Session", command=pause_session_button(idx), state=tk.DISABLED)
        pause_button.pack(padx=5, pady=5)
        pause_buttons.append(pause_button)

        end_button = tk.Button(frame, text="End Session", command=end_session_button(idx), state=tk.DISABLED)
        end_button.pack(padx=5, pady=5)
        end_buttons.append(end_button)

    duration_entry = tk.Entry(root)
    duration_entry.insert(0, "Duration in minutes")
    duration_entry.grid(row=len(ips)//2 + 1, column=0, columnspan=2, padx=10, pady=10)

    # Create the main UI window and widgets for the offline timers
    for tab_idx, tab in enumerate(roots_offline_timers):
        tab.title(f"Offline Timers - {tab_names[tab_idx]}")
        for idx, _ in enumerate(offline_timer_titles[tab_idx]):
            frame = tk.Frame(tab, width=200, height=100, borderwidth=2, relief="groove")
            frame.grid(row=idx//2, column=idx%2, padx=10, pady=10)

            label = tk.Label(frame, text=f"{offline_timer_titles[tab_idx][idx]}\nAvailable", justify="left")
            label.pack(padx=5, pady=5)
            labels_offline_timers[tab_idx].append(label)

            button = tk.Button(frame, text="Start Session", command=start_offline_session_button(tab_idx, idx))
            button.pack(padx=5, pady=5)
            buttons_offline_timers[tab_idx].append(button)

            pause_button = tk.Button(frame, text="Pause Session", command=pause_offline_session_button(tab_idx, idx), state=tk.DISABLED)
            pause_button.pack(padx=5, pady=5)
            pause_buttons_offline_timers[tab_idx].append(pause_button)

            end_button = tk.Button(frame, text="End Session", command=end_offline_session_button(tab_idx, idx), state=tk.DISABLED)
            end_button.pack(padx=5, pady=5)
            end_buttons_offline_timers[tab_idx].append(end_button)

        duration_entry_offline_timers[tab_idx] = tk.Entry(tab)
        duration_entry_offline_timers[tab_idx].insert(0, "Duration in minutes")
        duration_entry_offline_timers[tab_idx].grid(row=len(offline_timer_titles[tab_idx])//2 + 1, column=0, columnspan=2, padx=10, pady=10)

def start_session(index, session_duration_minutes):
    if index < 0 or index >= len(ips):
        display_error("Invalid café PC index.")
        return
    if any(i == index for i, _, _ in active_sessions):
        display_error(f"A session is already active on this café PC-{index+1}.")
        return
    
    cafe_pc_ip = ips[index]
    
    # change password
    new_password = generate_password()
    if not send_command(cafe_pc_ip, PORT, f"change_password {new_password}"):
        display_error(f"Failed to start session on café PC-{index+1}.")
        return
    with lock:
        pc_passwords[index] = new_password

    # set timer
    session_duration_seconds = int(session_duration_minutes * 60)
    if not send_command(cafe_pc_ip, PORT, f"set_timer {session_duration_seconds}"):
        display_error(f"Failed to set timer on café PC-{index+1}.")
        return
    with lock:
        active_sessions.append((index, session_duration_seconds, False))

    print(f"Session started on café PC {index+1} ({cafe_pc_ip}) for {session_duration_minutes} minutes. Password: {new_password}")
    save_state()

def extend_session(index, extra_time_minutes):
    for i, (pc_index, time_left, is_paused) in enumerate(active_sessions):
        if pc_index == index:
            new_time_left = int(max(0, time_left + extra_time_minutes * 60))

            if not send_command(ips[index], PORT, f"set_timer {new_time_left}"):
                display_error(f"Failed to extend session on café PC-{index+1}.")
                return
            
            new_password = pc_passwords[index] if new_time_left > 0 else generate_password()
            if not send_command(ips[index], PORT, f"change_password {new_password}"):
                display_error(f"Failed to extend session on café PC-{index+1}.")
                return
            
            with lock:
                active_sessions[i] = (pc_index, new_time_left, is_paused)

            print(f"Extended session on café PC {index+1} by {extra_time_minutes} minutes. New time left: {new_time_left//60} minutes")
            save_state()

def end_session(index):
    for i, (pc_index, time_left, _) in enumerate(active_sessions):
        if pc_index == index:
            cafe_pc_ip = ips[index]

            if not send_command(cafe_pc_ip, PORT, f"set_timer 0"):
                display_error(f"Failed to end session on café PC-{index+1}.")
                return
            
            if not send_command(cafe_pc_ip, PORT, f"restart"):
                display_error(f"Failed to end session on café PC-{index+1}.")
                return
            
            with lock:
                pc_passwords[index] = None
                active_sessions.pop(i)

            print(f"Session ended for café PC {index+1} with time left: {time_left*60} minutes. restarting PC.")
            save_state()

def pause_session(index):
    # lock the PC with a random password
    for i, (pc_index, time_left, _) in enumerate(active_sessions):
        if pc_index == index:
            with lock:
                active_sessions[i] = (pc_index, time_left, True)
            
            print(f"Paused session on café PC {index+1}.")
            save_state()

def resume_session(index):
    # restore the PC with the same password
    for i, (pc_index, time_left, _) in enumerate(active_sessions):
        if pc_index == index:
            with lock:
                active_sessions[i] = (pc_index, time_left, False)
            extend_session(index, 0) # extend the session by 0 minutes to update the password

            print(f"Resumed session on café PC {index+1}.")
            save_state()

def start_session_button(index):
    def start_sh():
        duration = int(duration_entry.get())
        start_session(index, duration)
    return start_sh

def extend_session_button(index):
    def extend():
        extra_time = int(duration_entry.get())
        extend_session(index, extra_time)
    return extend

def end_session_button(index):
    def end():
        end_session(index)
    return end

def pause_session_button(index):
    def pause():
        pause_session(index)
    return pause

def resume_session_button(index):
    def resume():
        resume_session(index)
    return resume

def start_offline_session(tab_idx, index, session_duration_minutes):
    if index < 0 or index >= len(offline_timer_titles[tab_idx]):
        display_error("Invalid timer index.")
        return
    
    timer_title = offline_timer_titles[tab_idx][index]
    if any(i == index for i, _, _ in active_offline_timers[tab_idx]):
        display_error(f"Timer {timer_title} is already active.")
        return
    with lock:
        active_offline_timers[tab_idx].append((index, session_duration_minutes * 60, False))

    print(f"Started offline timer {timer_title} for {session_duration_minutes} minutes.")
    save_state()

def extend_offline_session(tab_idx, index, extra_time_minutes):
    for i, (timer_index, time_left, is_paused) in enumerate(active_offline_timers[tab_idx]):
        if timer_index == index:
            new_time_left = int(max(0, time_left + extra_time_minutes * 60))
            with lock:
                active_offline_timers[tab_idx][i] = (timer_index, new_time_left, is_paused)

            print(f"Extended offline timer {offline_timer_titles[tab_idx][index]} by {extra_time_minutes} minutes. New time left: {new_time_left//60} minutes")
            save_state()

def end_offline_session(tab_idx, index):
    for i, (timer_index, time_left, _) in enumerate(active_offline_timers[tab_idx]):
        if timer_index == index:
            with lock:
                active_offline_timers[tab_idx].pop(i)

            print(f"Ended offline timer {offline_timer_titles[tab_idx][index]} with time left: {time_left//60} minutes.")
            save_state()

def pause_offline_session(tab_idx, index):
    # lock the PC with a random password
    for i, (timer_index, time_left, _) in enumerate(active_offline_timers[tab_idx]):
        if timer_index == index:
            with lock:
                active_offline_timers[tab_idx][i] = (timer_index, time_left, True)

            print(f"Paused offline timer {offline_timer_titles[tab_idx][index]}.")
            save_state()

def resume_offline_session(tab_idx, index):
    # restore the PC with the same password
    for i, (timer_index, time_left, _) in enumerate(active_offline_timers[tab_idx]):
        if timer_index == index:
            with lock:
                active_offline_timers[tab_idx][i] = (timer_index, time_left, False)
            extend_offline_session(tab_idx, index, 0) # extend the session by 0 minutes to update the password

            print(f"Resumed offline timer {offline_timer_titles[tab_idx][index]}.")
            save_state()

def start_offline_session_button(tab_idx, index):
    def start_sh():
        duration = int(duration_entry_offline_timers[tab_idx].get())
        start_offline_session(tab_idx, index, duration)
    return start_sh

def extend_offline_session_button(tab_idx, index):
    def extend():
        extra_time = int(duration_entry_offline_timers[tab_idx].get())
        extend_offline_session(tab_idx, index, extra_time)
    return extend

def end_offline_session_button(tab_idx, index):
    def end():
        end_offline_session(tab_idx, index)
    return end

def pause_offline_session_button(tab_idx, index):
    def pause():
        pause_offline_session(tab_idx, index)
    return pause

def resume_offline_session_button(tab_idx, index):
    def resume():
        resume_offline_session(tab_idx, index)
    return resume

# ping thread

def update_ping():
    while True:
        for idx, ip in enumerate(ips):
            threading.Thread(target=ping_pc, args=(ip, idx), daemon=True).start()
        time.sleep(update_ping_rate)

def ping_pc(ip, index):
    response = send_command(ip, PORT, "ping", receive_response=True, silent_fail=True)
    needs_restoration = pc_statuses[index] == 0
    if response is not None and response == "pong":
        with lock:
            pc_statuses[index] = 2
    else:
        if pc_statuses[index] == 2:
            display_error(f"PC-{index+1} is not responding.")
        with lock:
            if response is not None and response == "locker dead":
                pc_statuses[index] = 1
            else:
                pc_statuses[index] = 0
    if needs_restoration and pc_statuses[index] != 0:
        if index in [i for i, _, _ in active_sessions]:
            restore_client(index)

# session timer thread

def update_sessions():
    while True:
        # Update the session timers for café PCs
        for i in range(len(active_sessions)):
            with lock:
                if not active_sessions[i][2]:  # if the session is not paused
                    active_sessions[i] = (active_sessions[i][0], int(max(0, active_sessions[i][1] - update_sessions_rate)), False)
            
        # Check for timed out sessions and lock the PC with a random password
        for _, (index, time_left, is_paused) in enumerate(active_sessions):
            if time_left <= 0 or is_paused:
                threading.Thread(target=time_out_session, args=(index,), daemon=True).start()

        # Update the offline timers
        for tab_idx, _ in enumerate(offline_timer_titles):
            for i in range(len(active_offline_timers[tab_idx])):
                with lock:
                    if not active_offline_timers[tab_idx][i][2]: # if the session is not paused
                        active_offline_timers[tab_idx][i] = (active_offline_timers[tab_idx][i][0], int(max(0, active_offline_timers[tab_idx][i][1] - update_sessions_rate)), False)
        
        time.sleep(update_sessions_rate)

def time_out_session(index):
    cafe_pc_ip = ips[index]

    if not send_command(cafe_pc_ip, PORT, f"set_timer 0"):
        display_error(f"Failed to end session on café PC-{index+1}.")
        return

    if not send_command(cafe_pc_ip, PORT, f"lock {generate_password()}"):
        display_error(f"Failed to lock café PC-{index+1}.")
        return

    print(f"Session timed out for café PC {index+1}. PC locked.")

# Helper functions

def save_state():
    # Save the current state of the café to a JSON file
    path = state_file_paths.replace("*", str(int(time.time())))
    state = {}
    with lock:
        state["timestamp"] = time.time()
        state["active_sessions"] = active_sessions
        state["pc_passwords"] = pc_passwords
        state["active_offline_timers"] = active_offline_timers
    try:
        # save state to file
        with open(path, "w") as f:
            json.dump(state, f)
        # remove old files
        for file in glob.glob(state_file_paths):
            if file != path:
                os.remove(file)
    except Exception as e:
        msg = f"Error saving state to file: {e}"
        print(msg)
        display_error(msg)

def load_state():
    # load state from the oldest file
    files = glob.glob(state_file_paths)
    if not files:
        print("No state files found.")
        return
    path = min(files, key=os.path.getctime)
    try:
        with open(path, "r") as f:
            state = json.load(f)

            with lock:
                global active_sessions, pc_passwords, active_offline_timers
                active_sessions = state["active_sessions"]
                pc_passwords = state["pc_passwords"]
                active_offline_timers = state["active_offline_timers"]

            # update the time left for active sessions on café PCs based on the time passed since the state was saved
            time_passed = time.time() - state["timestamp"]
            for i, (index, time_left, is_paused) in enumerate(active_sessions):
                if not is_paused:
                    active_sessions[i] = (index, int(max(0, time_left - time_passed)), False)
            # update the time left for active offline timers based on the time passed since the state was saved
            for tab_idx, _ in enumerate(offline_timer_titles):
                for i, (index, time_left, is_paused) in enumerate(active_offline_timers[tab_idx]):
                    if not is_paused:
                        active_offline_timers[tab_idx][i] = (index, int(max(0, time_left - time_passed)), False)

            # restore the active sessions on café PCs
            for index, _, _ in active_sessions:
                restore_client(index)

        print(f"Loaded state from file: {path}")
    except Exception as e:
        msg = f"Error loading state from file: {e}"
        print(msg)
        display_error(msg)

def restore_client(index):
    time_left = 0
    for _, (pc_index, tl, _) in enumerate(active_sessions):
        if pc_index == index:
            time_left = tl
            break

    if not send_command(ips[index], PORT, f"set_timer {time_left}"):
        display_error(f"Failed to extend session on café PC-{index+1}.")
        return
    
    new_password = pc_passwords[index] if time_left > 0 else generate_password() 
    if not send_command(ips[index], PORT, f"change_password {new_password}"):
        display_error(f"Failed to extend session on café PC-{index+1}.")
        return
    
    print(f"Restored session on café PC {index+1} with time left: {time_left//60} minutes")

def generate_password(length=3, characters=string.digits):
    return ''.join(random.choice(characters) for _ in range(length))

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
                s.settimeout(5)
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
