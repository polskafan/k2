Step 0: Connect hardware requirements
----------
1. Kettler Ergoracer GT
2. Connect a DB9 USB to RS-232 cable to the Kettler Ergoracer GT
3. Connect an ANT+ Stick

Step 1: Install prerequisites
-----------
Install an MQTT broker
```console
sudo apt install mosquitto python3-virtualenv
```

Step 2: Checkout and install project
----------
Clone the project from GitHub
```console
git clone https://github.com/polskafan/k2.git
cd k2
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Step 3: Edit udev rules and install drivers and autorun scripts
----------
Edit the `scripts/udev/99-kettler.rules` file and replace the example IDs
for a Garmin2 ANT+ stick and pl2303 RS232 adapter with the IDs of your
devices. You can find the IDs by running `lsusb`.

After that install everything with
```
bash install.sh 
```

(Optional) Step 3: Allow outside MQTT connections for debugging
----------
To allow MQTT connections from outside of localhost run the following commands
```console
sudo cp scripts/mosquitto/default.conf /etc/mosquitto/conf.d/default.conf
sudo service mosquitto restart
```

Disclaimer
----------
Tested with Kettler Ergoracer GT, Raspberry Pi 3B/4 (Raspbian Bullseye), Anself ANT+ Sticks and Generic PL2303 Adapter. 