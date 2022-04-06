#!/bin/bash

USERID=$(id -u)
GROUPID=$(id -g)
BASE_DIRECTORY=$(pwd)

# Install ANT+ Driver
sudo cp scripts/udev/51-garmin.rules /etc/udev/rules.d
sudo cp scripts/udev/99-kettler.rules /etc/udev/rules.d

# Install Autostart Scripts
sed "s|###USERID###|$USERID|g;s|###GROUPID###|$GROUPID|g;s|###BASE_DIRECTORY###|$BASE_DIRECTORY|g" scripts/systemd/kettler.service > /tmp/kettler.service
sudo cp /tmp/kettler.service /etc/systemd/system/k2-kettler.service
rm /tmp/kettler.service

sed "s|###USERID###|$USERID|g;s|###GROUPID###|$GROUPID|g;s|###BASE_DIRECTORY###|$BASE_DIRECTORY|g" scripts/systemd/controller.service  > /tmp/controller.service
sudo cp /tmp/controller.service /etc/systemd/system/k2-controller.service
rm /tmp/controller.service

# Reload systemctl daemons files
sudo systemctl daemon-reload

# Start Services
sudo systemctl restart k2-kettler
sudo systemctl restart k2-controller

# Enable Autostart Scripts
sudo systemctl enable k2-kettler
sudo systemctl enable k2-controller