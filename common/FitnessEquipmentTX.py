# Thanks to the original work of
# https://github.com/dhague/vpower

from ant.core import message, node, constants
from ant.core.exceptions import ChannelError
from dataclasses import dataclass

@dataclass
class FitnessEquipmentData:
    time_elapsed: int = 0           # unit: 0.25s
    speed: int = 0                  # unit: 0.001 m/s
    resistance: int = 0             # unit: 0.5%
    instant_cadence: int = 0        # unit: 1 rpm
    instant_power: int = 0          # unit:
    instant_heartrate: int = None   # unit: bpm


class FitnessEquipmentTX:
    def __init__(self, antnode, sensor_id, callbacks=None):
        self.tick = 0
        self.update_event = 0
        self.accumulated_power = 0

        self.data = FitnessEquipmentData()

        self.antnode = antnode
        self.channel = antnode.getFreeChannel()

        self.callbacks = callbacks if callbacks is not None else dict()

        try:
            self.channel.name = 'C:FEC'
            network = node.Network(constants.NETWORK_KEY_ANT_PLUS, 'N:ANT+')
            self.channel.assign(network, constants.CHANNEL_TYPE_TWOWAY_TRANSMIT)
            self.channel.setID(0x11, sensor_id, 0)
            self.channel.period = 8192
            self.channel.frequency = 57
            self.channel.registerCallback(self)
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
            0x10,                                           # general fe data page
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
            0x11,                                           # general settings page
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
            0x19,                                           # specific stationary bike data
            self.update_event % 256,                        # event counter
            (self.data.instant_cadence or 0xFF) % 256,      # cadence - unit rpm
            self.accumulated_power & 0xFF,                  # accumulated power LSB - unit 1W
            self.accumulated_power >> 8,                    # accumulated power MSB - unit 1W
            self.data.instant_power & 0xFF,                 # instant power LSB - unit 1W
            (self.data.instant_power >> 8) & 0xF,           # instant power MSN & trainer status
            0x20                                            # capabilities & FE state
        ]

    def page_vendor(self):
        return [0x50, 0xFF, 0xFF, 0x0A, 0xFF, 0x00, 0x24, 0x01]

    def page_product(self):
        return [0x51, 0xFF, 0x50, 0x0D, 0x02, 0x00, 0x24, 0x01]

    # handle control messages from fitness equipment display
    def process(self, msg, _):
        if isinstance(msg, message.ChannelAcknowledgedDataMessage):
            if msg.data[0] == 0x30:     # basic resistance
                if 'basic_resistance' in self.callbacks:
                    self.callbacks['basic_resistance'](basic_resistance=msg.data[7] * 5)
            elif msg.data[0] == 0x31:   # target power
                if 'target_power' in self.callbacks:
                    self.callbacks['target_power'](target_power=((msg.data[7] << 8) + msg.data[6]) * 25)
            elif msg.data[0] == 0x32:   # wind resistance
                if 'wind_resistance' in self.callbacks:
                    self.callbacks['wind_resistance'](wind_resistance=msg.data[5] if msg.data[5] != 0xFF else None,
                                                      wind_speed=msg.data[6] - 127 if msg.data[6] != 0xFF else None,
                                                      drafting_factor=msg.data[7] if msg.data[7] != 0xFF else None)
            elif msg.data[0] == 0x33:   # track resistance
                if 'track_resistance' in self.callbacks:
                    self.callbacks['track_resistance'](grade=(msg.data[6] << 8) + msg.data[5] - 20000
                                                             if (msg.data[5], msg.data[6]) != (0xFF, 0xFF) else None,
                                                       coefficient=msg.data[7] * 5 if msg.data[7] != 0xFF else None)
            elif msg.data[0] == 0x37:   # user configuration
                if 'user_config' in self.callbacks:
                    self.callbacks['user_config'](user_weight=((msg.data[2] << 8) + msg.data[1])
                                                              if (msg.data[1], msg.data[2]) != (0xFF, 0xFF) else None,
                                                  wheel_offset=msg.data[4] & 0x0F
                                                               if msg.data[4] & 0x0F != 0xF else None,
                                                  bike_weight=((msg.data[5] << 4) + ((msg.data[4] & 0xF0) >> 4)) * 5
                                                               if (msg.data[4] >> 4, msg.data[5]) != (0xF, 0xFF)
                                                               else None,
                                                  wheel_diameter=msg.data[6] if msg.data[6] != 0xFF else None,
                                                  gear_ratio=msg.data[7] * 3 if msg.data[7] != 0x00 else None)