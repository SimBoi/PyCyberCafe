import random
import socket
import subprocess
import threading
import time
import sys
import datetime

# Define the IP address and port where the script will listen
HOST = '0.0.0.0'  # Listen on all network interfaces
PORT = 22077
CLOCK_PORT = 22177
LOCKER_PORT = 22277
CAFE_PCS_IPS = [
    "10.100.102.23",
    "10.100.102.16",
    "10.100.102.27",
    "10.100.102.31",
    "10.100.102.14",
    "10.100.102.10",
    "10.100.102.8",
]

# text file to redirect the output of the script, None to disable
output_file = f"C:\\PyCafe\\Logs\\pycafeclient\\pycafeclient_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.log"
sys.stdout = open(output_file, "w") if output_file is not None else sys.__stdout__
sys.stderr = sys.stdout
logs_flushing_rate = 30  # in seconds

# Session timer
session_timer = 0  # in seconds
session_timer_update_rate = 60  # in seconds
clock_update_rate = 30  # in seconds

def lock_pc():
    send_command("localhost", LOCKER_PORT, "lock", False, False)

def change_password(new_password):
    try:
        # get the index of the pc using the ip
        pc_index = CAFE_PCS_IPS.index(socket.gethostbyname(socket.gethostname()))
        username = f"PC-{pc_index+1}-Guest"

        # Command to change the user password
        command = f'net user "{username}" {new_password}'
        
        # Run the command using subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        # Check if the command was successful
        if result.returncode == 0:
            print(f"Password for {username} successfully changed.")
        else:
            print(f"Error changing password: {result.stderr}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

def ping(conn, adress):
    print('got pinged from :' + str(adress))
    conn.sendall("pong".encode('utf-8'))

def restart_pc():
    # Use Windows API to restart the PC
    subprocess.run("shutdown /r /t 0", shell=True)
    print("PC Restarting")

def set_session_timer(seconds):
    global session_timer
    session_timer = seconds

def send_session_timer(conn):
    conn.sendall(str(session_timer).encode('utf-8'))

def handle_client_connection(args):
    conn , adress = args[0],args[1]
    with conn:
        command = conn.recv(1024).decode('utf-8')
        print(f"Received command: {command}")
        
        if command.startswith("ping"):
            ping(conn, adress)
        elif command.startswith("lock"):
            cmd_args = command.split(" ")
            if len(cmd_args) == 2:
                change_password(cmd_args[1])
                lock_pc()
            else:
                lock_pc()
        elif command.startswith("restart"):
            restart_pc()
        elif command.startswith("change_password"):
            cmd_args = command.split(" ")
            change_password(cmd_args[1])
        elif command.startswith("set_timer"):
            cmd_args = command.split(" ")
            if len(cmd_args) == 2:
                set_session_timer(int(cmd_args[1]))
        elif command.startswith("get_timer"):
            send_session_timer(conn)
        else:
            print("Invalid command received.")

# session timer thread
def update_session_timer():
    global session_timer
    while True:
        # Decrement the session timer
        session_timer = max(0, session_timer - session_timer_update_rate)
        time.sleep(session_timer_update_rate)

# client clock thread
def update_client_clock():
    while True:
        send_command("localhost", CLOCK_PORT, f"set_timer {session_timer}", True)
        time.sleep(clock_update_rate)

# log flushing thread
def update_flush_logs():
    while True:
        sys.stdout.flush()
        time.sleep(logs_flushing_rate)

def listen_for_connections():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Listening on {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            args = (conn, addr)
            threading.Thread(target=handle_client_connection, args={args}, daemon=True).start()

def send_command(ip, port, command, receive_response=False, silent_fail=False):
    for i in range(2):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((ip, port))
                s.sendall(command.encode('utf-8'))
                print(f"Sent command: {command}")
                return s.recv(1024).decode('utf-8') if receive_response else True
        except Exception as e:
            if not silent_fail:
                print(f"Error sending command to {ip}: {command}\nError: {e}\nAttempt {i+1}")
    return None if receive_response else False

if __name__ == "__main__":
    # Start the PC with a random password
    change_password(random.randint(1000, 9999))
    lock_pc()

    # Start the session timer in a separate thread
    threading.Thread(target=update_session_timer, daemon=True).start()
    # Start the client clock update in a separate thread
    threading.Thread(target=update_client_clock, daemon=True).start()
    # Start the log flushing in a separate thread
    threading.Thread(target=update_flush_logs, daemon=True).start()
    # Start listening for connections in the main thread
    listen_for_connections()
