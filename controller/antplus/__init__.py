import asyncio

from common import ant_driver
from ant.core.exceptions import ANTException
from ant.core.node import Node, Network
from ant.core.constants import NETWORK_KEY_ANT_PLUS, NETWORK_NUMBER_PUBLIC

from common.FitnessEquipmentTX import FitnessEquipmentTX
from config import antplus, power
import json

class ANTController:
    def __init__(self, manager):
        self.manager = manager
        self.task = asyncio.create_task(self.ant_task())
        self.fitness_equipment = None
        self.loop = None

    async def ant_task(self):
        self.loop = asyncio.get_event_loop()

        antnode = Node(ant_driver.USB2Driver(idVendor=antplus['vendor_id'], idProduct=antplus['product_id']))
        try:
            antnode.start()
            network = Network(key=NETWORK_KEY_ANT_PLUS, name='N:ANT+')
            antnode.setNetworkKey(NETWORK_NUMBER_PUBLIC, network)

            self.fitness_equipment = FitnessEquipmentTX(antnode, antplus['sensor_id'], callbacks={
                'basic_resistance': lambda basic_resistance:
                                        self.update_power(int(power['resistance'](basic_resistance/1000))),
                'target_power': lambda target_power:
                                        self.update_power(int(target_power / 100)),
                'track_resistance': lambda grade, coefficient:
                                        self.update_power(int(power['grade'](grade / 10000))),
                'wind_resistance': lambda **kwargs: print("[wind resistance]", kwargs)
            })
            self.fitness_equipment.open()

            print(f"[ANT+] Started fitness equipment controller with ANT+ ID {antplus['sensor_id']}")

            while True:
                try:
                    self.fitness_equipment.update()
                    await asyncio.sleep(0.25)
                except asyncio.CancelledError:
                    break
        except ANTException as err:
            print(f'Could not start ANT.\n{err}')

        antnode.stop()

    async def handle_kettler_message(self, message):
        try:
            data = json.loads(message.payload.decode())
            minutes, seconds = data['payload']['timeElapsed'].split(":", 2)
            self.fitness_equipment.data.time_elapsed = (int(minutes)*60 + int(seconds)) * 4
            self.fitness_equipment.data.speed = int(data['payload']['speed'] * 1000 / 3.6)
            self.fitness_equipment.data.resistance = int(data['payload']['realPower'] / 1200)
            self.fitness_equipment.data.instant_cadence = data['payload']['cadence']
            self.fitness_equipment.data.instant_power = data['payload']['realPower']

        except json.JSONDecodeError:
            pass

    def update_power(self, watts):
        self.loop.create_task(self.manager.ant_power(power['minmax'](value=watts,
                                                                     lower=power['lower_limit'],
                                                                     upper=power['upper_limit'])))