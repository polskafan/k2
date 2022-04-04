import time

from ant.core import driver
from ant.core.exceptions import ANTException
from ant.core.node import Node, Network
from ant.core.constants import NETWORK_KEY_ANT_PLUS, NETWORK_NUMBER_PUBLIC

from common.FitnessEquipmentTX import FitnessEquipmentTX
from config import antplus

antnode = Node(driver.USB1Driver(device=antplus['device']))
try:
    antnode.start()
    network = Network(key=NETWORK_KEY_ANT_PLUS, name='N:ANT+')
    antnode.setNetworkKey(NETWORK_NUMBER_PUBLIC, network)

    fitness_equipment = FitnessEquipmentTX(antnode, antplus['sensor_id'], callbacks={
        'basic_resistance': lambda **kwargs: print(kwargs),
        'target_power': lambda **kwargs: print(kwargs),
        'wind_resistance': lambda **kwargs: print(kwargs),
        'track_resistance': lambda **kwargs: print(kwargs),
        'user_config': lambda **kwargs: print(kwargs)
    })
    fitness_equipment.open()

    print("STARTED fitness equipment with ANT+ ID " + repr(antplus['sensor_id']))

    while True:
        try:
            fitness_equipment.data.time_elapsed += 1
            fitness_equipment.data.speed = 10000
            fitness_equipment.data.resistance = 20
            fitness_equipment.data.instant_cadence = 96
            fitness_equipment.data.instant_power = 200
            fitness_equipment.data.instant_heartrate = 130
            fitness_equipment.update()
            time.sleep(0.25)
        except KeyboardInterrupt:
            break
except ANTException as err:
    print(f'Could not start ANT.\n{err}')

antnode.stop()