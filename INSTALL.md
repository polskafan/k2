Step 0: Connect hardware requirements
----------
1. Connect a DB9 USB to RS-232 cable to the Kettler
2. Connect an ANT+ Stick

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
bash install.sh
```



(Optional) Step 3: Allow outside MQTT connections for debugging
----------
To allow MQTT connections from outside of localhost run the following commands
```console
sudo cp scripts/mosquitto/default.conf /etc/mosquitto/conf.d/default.conf
sudo service mosquitto restart
```
