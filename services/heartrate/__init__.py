import asyncio
from asyncio_mqtt import Client, MqttError, Will
import json
import os
import time
from contextlib import AsyncExitStack
from config import mqtt_credentials, heartrate_macs, heartrate_adapter
from bleak import BleakClient, BleakError
import bleak_sigspec.utils
import struct

class Heartrate2MQTT:
    def __init__(self, mqtt):
        self.mqtt = mqtt
        self.client = None

    async def mqtt_connect(self):
        while True:
            try:
                async with AsyncExitStack() as stack:
                    self.client = Client(self.mqtt['server'],
                                         port=self.mqtt['port'],
                                         will=Will("status/heartrate", '{"connected": false}', retain=True))

                    await stack.enter_async_context(self.client)
                    print("[MQTT] Connected.")

                    await self.update_mqtt("status/heartrate", {"connected": True})

                    try:
                        # do nothing while we are connected
                        # sleep forever
                        while True:
                            await asyncio.sleep(3600)
                    except asyncio.CancelledError as e:
                        await self.update_mqtt("status/heartrate", {"connected": False})
                        self.client = None
                        return
            except MqttError as e:
                print(f"[MQTT] Disconnected: {str(e)}. Reconnecting...")
                self.client = None
                pass

    async def listen_heartrate(self):
        device_mac = heartrate_macs[0]

        while True:
            try:
                disconnect_event = asyncio.Event()

                def disconnect_handler(c):
                    print(f"[Bluetooth] Disconnected {c.is_connected}")
                    disconnect_event.set()

                async with BleakClient(device_mac,
                                       timeout=30,
                                       adapter=heartrate_adapter,
                                       disconnected_callback=disconnect_handler) as client:
                    print(f"[Bluetooth] Connected {client.is_connected}")
                    await self.update_mqtt("heartrate/connected", True)
                    await client.get_services()

                    heart_rate_service = None
                    for service in client.services:
                        if service.uuid.startswith('0000180d'):
                            heart_rate_service = service

                    characteristic_heart_rate_measurement = None
                    characteristic_body_sensor_location = None
                    for characteristic in heart_rate_service.characteristics:
                        if characteristic.uuid.startswith('00002a37'):
                            characteristic_heart_rate_measurement = characteristic

                        if characteristic.uuid.startswith('00002a38'):
                            characteristic_body_sensor_location = characteristic

                    body_sensor_location_data = await client.read_gatt_char(characteristic_body_sensor_location)
                    body_sensor_location = bleak_sigspec.utils.get_char_value(body_sensor_location_data,
                                                                              "body_sensor_location")
                    print("Sensor location: %s" % str(body_sensor_location))
                    await self.update_mqtt("heartrate/location", body_sensor_location)

                    async def callback(_, data):
                        try:
                            value = bleak_sigspec.utils.get_char_value(data, "heart_rate_measurement")
                        except struct.error:
                            print(f"Struct error {str(data)}")
                            return

                        try:
                            if 'RR-Interval' in value:
                                await self.update_mqtt('heartrate/data',
                                                 {'hr': value['Heart Rate Measurement Value (uint8)']['Value'],
                                                 'rr': value['RR-Interval']['RR-Interval']['RR-I0']['Value']})
                                print(value['Heart Rate Measurement Value (uint8)']['Value'],
                                      value['RR-Interval']['RR-Interval']['RR-I0']['Value'])
                            else:
                                await self.update_mqtt('heartrate/data',
                                                 {'hr': value['Heart Rate Measurement Value (uint8)']['Value'],
                                                 'rr': None})
                                print(value['Heart Rate Measurement Value (uint8)']['Value'])
                        except KeyError:
                            print(f"Could not parse Heart Rate Data {str(value)}")
                            return

                    await client.start_notify(characteristic_heart_rate_measurement, callback)

                    await self.update_mqtt('heartrate', {})
                    await disconnect_event.wait()
                    await self.update_mqtt("heartrate/connected", False)

            except (asyncio.TimeoutError, BleakError) as e:
                print(f"[Bluetooth] Error - {str(e)}")
                pass
            finally:
                print("Retrying...")

    async def update_mqtt(self, key, data):
        data = {
            'payload': data,
            '_timestamp': int(time.time())
        }

        if self.client is not None:
            await self.client.publish(f'{key}',
                                      json.dumps(data),
                                      retain=True)

    async def cancel_task(self, task):
        if task.done():
            return
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass


async def main():
    mqtt_server = Heartrate2MQTT(mqtt_credentials)
    await asyncio.gather(mqtt_server.mqtt_connect(), mqtt_server.listen_heartrate())


def run():
    # Change to the "Selector" event loop for Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Goodbye...")


if __name__ == '__main__':
    run()
