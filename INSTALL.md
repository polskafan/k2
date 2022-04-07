Step 0: Connect hardware requirements
----------
1. Kettler Ergoracer GT
2. Connect a DB9 USB to RS-232 cable to the Kettler Ergoracer GT
3. Connect an ANT+ Stick

Step 1: Install prerequisites
-----------
Install an MQTT broker
```bash
sudo apt install mosquitto python3-virtualenv
```

Step 2: Checkout and install project
----------
Clone the project from GitHub
```bash
git clone https://github.com/polskafan/k2.git
cd k2
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

(Optional) Step 2b: Remote control
-----------
Run the following commands to allow MQTT connections from outside of localhost (e.g. for remote control)
```bash
sudo cp scripts/mosquitto/default.conf /etc/mosquitto/conf.d/default.conf
sudo service mosquitto restart
```

Step 3: Setup udev rules, install drivers and autorun scripts
----------
Edit the `scripts/udev/99-kettler.rules` file and replace the example IDs
for a generic pl2303 RS232 adapter with the IDs of your device.
You can find the IDs by running `lsusb`.

After that install everything with
```
bash install.sh 
```

Disclaimer
----------
This project has been tested with the following devices:

- Kettler Ergoracer GT
- Raspberry Pi 3B/4 (Raspbian Bullseye)
- Anself ANT+ sticks
- Generic PL2303 RS232 adapter 
