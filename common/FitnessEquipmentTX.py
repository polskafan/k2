# Thanks to the original work of
# https://github.com/dhague/vpower

from ant.core import message, node
from ant.core.constants import *
from ant.core.exceptions import ChannelError
from dataclasses import dataclass

FITNESS_EQUIPMENT_TYPE = 0x11
CHANNEL_PERIOD = 8192
DEBUG = True

class FecListener:
    def __init__(self, callbacks=None):
        if callbacks is not None:
            self.callbacks = dict(callbacks)

    def process(self, msg, _):
        if isinstance(msg, message.ChannelAcknowledgedDataMessage):
            if DEBUG: print("[Message received] Page ID", msg.data[0], "data", bytes(msg.data[1:8]).hex())
            if msg.data[0] == 0x30:
                # basic resistance
                basic_resistance = msg.data[7] * 5

                if DEBUG: print(f"[basic resistance] basic_resistance {basic_resistance}")

                if 'on_basic_resistance' in self.callbacks:
                    self.callbacks['on_basic_resistance'](basic_resistance)
            elif msg.data[0] == 0x31:
                # target power
                target_power = ((msg.data[7] << 8) + msg.data[6]) * 25

                if DEBUG: print(f"[target power] target_power {target_power}")

                if 'on_target_power' in self.callbacks:
                    self.callbacks['on_target_power'](target_power)
            elif msg.data[0] == 0x32:
                # wind resistance
                wind_resistance = msg.data[5]
                wind_speed = msg.payload[6] - 127
                drafting_factor = msg.payload[7]

                if DEBUG: print(f"[wind resistance] "
                                f"wind_resistance {wind_resistance} "
                                f"wind_speed {wind_speed} "
                                f"drafting_factor {drafting_factor}")

                if 'on_wind_resistance' in self.callbacks:
                    self.callbacks['on_wind_resistance'](wind_resistance, wind_speed, drafting_factor)
            elif msg.data[0] == 0x33:
                # track resistance
                grade = (msg.data[6] << 8) + msg.data[5] - 20000
                coefficient = msg.data[7] * 5

                if DEBUG: print(f"[track resistance] grade: {grade} coefficient: {coefficient}")

                if 'on_track_resistance' in self.callbacks:
                    self.callbacks['on_track_resistance'](grade, coefficient)
            elif msg.data[0] == 0x37:
                # user configuration
                user_weight = ((msg.data[2] << 8) + msg.data[1])
                wheel_offset = msg.data[4] & 0x0F
                bike_weight = ((msg.data[5] << 4) + ((msg.data[4] & 0xF0) >> 4)) * 5
                wheel_diameter = msg.data[6]
                gear_ratio = msg.data[7] * 3

                print(f"[user config] "
                      f"user weight: {user_weight} "
                      f"wheel_offset: {wheel_offset} "
                      f"bike_weight: {bike_weight} "
                      f"wheel_diameter: {wheel_diameter} "
                      f"gear_ratio: {gear_ratio}")

                if 'on_user_config' in self.callbacks:
                    self.callbacks['on_user_config'](user_weight, wheel_offset, bike_weight, wheel_diameter, gear_ratio)
            elif msg.data[0] == 0x46 and msg.data[7] == 0x01:
                # request data page
                retries = msg.data[5] & 0x7F
                page_number = msg.data[6]

                print(f"[request data page] retries: {retries} page_number: {page_number}")

        else:
            print("Unknown message type", msg)

pages = {
    "general": 0x10,
    "general_settings": 0x11,
    "stationary_bike": 0x19,
    "vendor": 0x50,
    "product": 0x51
}

@dataclass
class FitnessEquipmentData:
    time_elapsed: int = 0    # unit: 0.25s
    speed: int = 0           # unit: 0.001 m/s
    resistance: int = 0      # unit: 0.5%
    instant_cadence: int = 0 # unit: 1 rpm
    instant_power: int = 0   # unit:
    instant_heartrate: int = None  # unit: bpm


class FitnessEquipmentTX:
    def __init__(self, antnode, sensor_id):
        self.tick = 0
        self.update_event = 0
        self.accumulated_power = 0

        self.data = FitnessEquipmentData()

        self.antnode = antnode

        # Get the channel
        self.channel = antnode.getFreeChannel()

        try:
            self.channel.name = 'C:FEC'
            network = node.Network(NETWORK_KEY_ANT_PLUS, 'N:ANT+')
            self.channel.assign(network, CHANNEL_TYPE_TWOWAY_TRANSMIT)
            self.channel.setID(FITNESS_EQUIPMENT_TYPE, sensor_id, 0)
            self.channel.period = CHANNEL_PERIOD
            self.channel.frequency = 57
            self.channel.registerCallback(FecListener())
        except ChannelError as e:
            print ("Channel config error: "+str(e))

    def open(self):
        self.channel.open()

    def close(self):
        self.channel.close()

    def unassign(self):
        self.channel.unassign()

    def update(self):
        try:
            # transmission pattern "C"
            if self.tick % 132 in [64, 65]:
                payload = self.page_vendor()
            elif self.tick % 132 in [130, 131]:
                payload = self.page_product()
            elif self.tick % 66 % 8 in [3, 6]:
                payload = self.page_settings()
            elif self.tick % 66 % 8 in [2, 7]:
                payload = self.page_stationary_bike()
                self.update_event += 1
            else:
                payload = self.page_general()

            payload = bytearray(payload)
            ant_msg = message.ChannelBroadcastDataMessage(self.channel.number, data=payload)
            self.antnode.send(ant_msg)

            # tick
            self.tick += 1
        except Exception as e:
            print("Exception in FitnessEquipmentTX: " + repr(e))

    def page_general(self):
        # general data page
        return [
            pages['general'],                               # general fe data page
            0x19,                                           # equipment type - trainer
            self.data.time_elapsed % 256,                   # time elapsed - unit 0.25s
            0x00,                                           # distance travelled - unit metres - NOT IMPLEMENTED
            self.data.speed & 0xFF,                         # speed LSB - unit 0.001 m/s
            self.data.speed >> 8,                           # speed MSB - unit 0.001 m/s
            (self.data.instant_heartrate or 0xFF) % 256,    # heartrate - unit bpm
            0x20                                            # capabilities & FE state
        ]

    def page_settings(self):
        return [
            pages['general_settings'],                      # general settings page
            0xFF,                                           # reserved
            0xFF,                                           # reserved
            215,                                            # cycle length (wheel circumference) - unit 0.01m
            0xFF,                                           # incline LSB - not supported by bike
            0x7F,                                           # incline MSB - not supported by bike
            self.data.resistance % 256,                     # resistance level
            0x20                                            # capabilities & FE state
        ]

    def page_stationary_bike(self):
        self.accumulated_power += self.data.instant_power
        self.accumulated_power %= 65536

        return [
            pages['stationary_bike'],                               # specific stationary bike data
            self.update_event % 256,                        # event counter
            (self.data.instant_cadence or 0xFF) % 256,       # cadence - unit rpm
            self.accumulated_power & 0xFF,                  # accumulated power LSB - unit 1W
            self.accumulated_power >> 8,                    # accumulated power MSB - unit 1W
            self.data.instant_power & 0xFF,                 # instant power LSB - unit 1W
            (self.data.instant_power >> 8) & 0xF,           # instant power MSN & trainer status
            0x20                                            # capabilities & FE state
        ]

    def page_vendor(self):
        return [pages['vendor'], 0xFF, 0xFF, 0x0A, 0xFF, 0x00, 0x24, 0x01]

    def page_product(self):
        return [pages['product'], 0xFF, 0x50, 0x0D, 0x02, 0x00, 0x24, 0x01]
