#!/usr/bin/python
#
import time
import hashlib

from ant.core import driver
from ant.core.exceptions import ANTException
from ant.core.node import Node, Network
from ant.core.constants import NETWORK_KEY_ANT_PLUS, NETWORK_NUMBER_PUBLIC

from common.FitnessEquipmentTX import FitnessEquipmentTX
from config import mqtt_credentials, antplus

########################   Get the serial number of Raspberry Pi

def getserial():
    # Extract serial from cpuinfo file
    cpuserial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                cpuserial = line[10:26]
        f.close()
    except:
        cpuserial = "ERROR000000000"
    return cpuserial

####################################################################

FEC_SENSOR_ID = int(int(hashlib.md5(getserial().encode()).hexdigest(), 16) & 0xfffe) + 2

#-------------------------------------------------#
#  Initialization                                 #
#-------------------------------------------------#
antnode = Node(driver.USB1Driver(device=antplus['device']))
try:
    antnode.start()
    network = Network(key=NETWORK_KEY_ANT_PLUS, name='N:ANT+')
    antnode.setNetworkKey(NETWORK_NUMBER_PUBLIC, network)

    fitness_equipment = FitnessEquipmentTX(antnode, FEC_SENSOR_ID)
    fitness_equipment.open()
    print("SUCCESFULLY STARTED fitness equipment with ANT+ ID " + repr(FEC_SENSOR_ID))

    while True:
        fitness_equipment.data.time_elapsed += 1
        fitness_equipment.data.speed = 10000
        fitness_equipment.data.resistance = 20
        fitness_equipment.data.instant_cadence = 96
        fitness_equipment.data.instant_power = 200
        fitness_equipment.data.instant_heartrate = 130
        fitness_equipment.update()
        time.sleep(0.25)

except ANTException as err:
    print(f'Could not start ANT.\n{err}')

#######################################################################################

while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        break

antnode.stop()