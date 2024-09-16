# PyCyberCafe

Session management software for remotely giving timed access to Windows PCs.
- Start a new session: generates a new password for the selected PC
- Extend session: Adds/removes time from an active session
- On session timer end: locks the pc with a randomly generated password
- End session: restarts the PC and sets a random password, if paired with software like Reboot Restore RX, will restore the PC to the state from before the session start

Offline timers are included to create sessions for other devices, basically regular timers with labels

Other features:
- autosave feature for storing the state of the cafe, will automatically restore the last saved state on script startup
- constantly pings the client script on the target PCs for detecting attemps to bypass the system, the ping rate can be set in the server script
- clock script to display the time left for the current session on the target PCs
- output logs to text files

# How To Install

## Master PC setup
1. download the pycafeserver.py file on your master PC
2. download the ips.txt file to the same directory as pycafeserver.py
3. edit the file, add the ips of the target PCs line by line
4. download the offline_timers.txt file to the same directory as the pycafeserver.py
5. edit the file, add tab names and add the labels of the offline timers line by line, each tab will create a new UI window with the timers below it
6. run the pycafeserver.py script from the terminal or create an executable using PyInstaller and run it

## Target PCs setup
on each PC:
1. create a user called PC-\<number\>-Guest
2. download pycafeclient.py and edit the logs file path string to a location of your choosing
3. using Windows Task Scheduler, configure the script or an executable made with PyInstaller to run on startup with the user SYSTEM
4. download the pycafeclock.py and pycafelocker.py scripts and edit the logs file path string to a location of your choosing
5. using Windows Task Scheduler, configure both scripts or executables made with PyInstaller to run on logon with the user PC-\<number\>-Guest

## Notes
1. make sure that all the scripts have inbound and outbound traffic allowed in the firewall
2. additional settings can be edited inside the scripts, such as the pinging rate and the clock update rate...
