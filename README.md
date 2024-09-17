<h1 align="center">
    PyCyberCafe
    <img src="https://img.shields.io/badge/python-3.12-green?logo=python&logoColor=white&style=for-the-badge">
</h1>

PyCyberCafe is a Python-based session management system designed for managing access to multiple Windows PCs in a cyber café environment.

# Overview
PyCyberCafe is a session management software designed primarily for cyber cafés but can also be used in other environments where timed access to Windows PCs is needed, such as libraries, schools, or shared office spaces. It allows administrators to remotely start, extend, or end sessions while ensuring system security by locking PCs when sessions end. If paired with software like Reboot Restore RX, the PCs can be restored to their original state after each session. The software also supports offline timers for non-networked devices and includes additional features such as autosaving the café state and logging session activity.

# Features
- Start a new session: generates a new password for the selected PC.
- Extend session: adds or removes time from an active session.
- On session timer end: locks the PC with a randomly generated password.
- End session: restarts the PC and sets a random password. When paired with software like Reboot Restore RX, the PC is restored to its pre-session state.
- Autosave café state: automatically restores the last saved state upon script startup.
- Ping detection: regularly pings target PCs to detect attempts to bypass the system (ping rate adjustable in the server script).
- Clock script: displays the time left for the current session on the target PCs.
- Offline timers: create and manage timers for non-networked devices with labels.
- Output logs: logs session activity to text files for easy monitoring.

# Installation

## Requirements
- Python 3.12
- (Optional) PyInstaller for generating executables
- Administrator access to configure user accounts and scheduled tasks
- `tkinter` (comes pre-installed with Python, but may need to be installed separately on some systems)

If `tkinter` is not installed, follow the installation guide here:  
[Installing Tkinter](https://tkdocs.com/tutorial/install.html)


## Master PC Setup
1. Download the `pycafeserver.py` file on your master PC.
2. Download the `ips.txt` file to the same directory as `pycafeserver.py`.
3. Edit `ips.txt` and add the IPs of the target PCs, one per line.
4. Download `offline_timers.txt` to the same directory as `pycafeserver.py`.
5. Edit `offline_timers.txt` and add tab names and the labels of the offline timers, one per line. Each tab will create a new UI window with the timers listed below it.
6. Run the `pycafeserver.py` script from the terminal or create an executable using PyInstaller and run it.

## Target PCs Setup
For each target PC:
1. Create a user named `PC-<number>-Guest`.
2. Download `pycafeclient.py` and edit the log file path string to a location of your choosing.
3. Using Windows Task Scheduler, configure the script (or an executable created with PyInstaller) to run on startup with the user SYSTEM.
4. Download the `pycafeclock.pyw` and `pycafelocker.pyw` scripts and edit the log file paths as needed.
5. Configure both scripts (or their executables) to run on logon using Task Scheduler with the `PC-<number>-Guest` user.

## Notes
- Ensure that all scripts have inbound and outbound traffic allowed in the firewall.
- Make sure all target PCs are configured with **static IP addresses** to avoid connection issues between the Master PC and the Target PCs.
- Additional settings, such as ping rate and clock update rate, can be adjusted within the scripts.
