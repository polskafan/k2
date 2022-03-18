import asyncio
from asyncio_mqtt import Client, MqttError, Will
import json
import os
import time
from contextlib import AsyncExitStack
from config import mqtt_credentials, logger as logger_config
from datetime import datetime
import csv

class MQTT2Log:
    def __init__(self, mqtt):
        self.mqtt = mqtt
        self.client = None

        self.command_task = None
        self.kettler_task = None
        self.heartrate_task = None

        self.csv_file = None
        self.csv_writer = None

        self.heartrate = dict()

    async def mqtt_connect(self):
        while True:
            try:
                async with AsyncExitStack() as stack:
                    self.client = Client(self.mqtt['server'],
                                         port=self.mqtt['port'],
                                         will=Will("status/logger", '{"connected": false}', retain=True))

                    await stack.enter_async_context(self.client)
                    print("[MQTT] Connected.")

                    await self.update_mqtt("status/logger", {"connected": True})

                    # handle commands
                    command_messages = await stack.enter_async_context(self.client.filtered_messages("logger/cmnd"))
                    self.command_task = asyncio.create_task(self.handle_command_messages(command_messages))

                    # handle kettler
                    kettler_messages = await stack.enter_async_context(self.client.filtered_messages("kettler/data"))
                    self.kettler_task = asyncio.create_task(self.handle_kettler_messages(kettler_messages))

                    # handle heartrate
                    heartrate_messages = await stack.enter_async_context(self.client.filtered_messages("heartrate/+"))
                    self.heartrate_task = asyncio.create_task(self.handle_heartrate_messages(heartrate_messages))

                    await self.client.subscribe("logger/cmnd")
                    await self.client.subscribe("kettler/data")
                    await self.client.subscribe("heartrate/connected")
                    await self.client.subscribe("heartrate/data")

                    await asyncio.gather(self.command_task, self.kettler_task, self.heartrate_task)
            except MqttError as e:
                print(f"[MQTT] Disconnected: {str(e)}. Reconnecting...")
                self.client = None
                pass

    async def handle_command_messages(self, messages):
        async for message in messages:
            try:
                data = json.loads(message.payload.decode())
                print(message.topic, data)
                if data['action'] == "start":
                    if self.csv_writer is None and self.csv_file is None:
                        if 'filename' in data:
                            filename = data['filename']
                        else:
                            filename = "%s.log.csv" % datetime.now().strftime("%Y-%m-%d_%H.%M.%S")

                        # open file
                        print(f"[Logger] {filename} open")

                        self.csv_file = open(os.path.join(logger_config['path'], filename), "w",
                                             newline="", encoding="utf-8")
                        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=['timestamp', 'speed', 'cadence',
                                                                                    'power', 'heart_rate', 'rri',
                                                                                    'distance', 'position_lat',
                                                                                    'position_long', 'altitude',
                                                                                    'grade'])
                        self.csv_writer.writeheader()
                elif data['action'] == "stop":
                    if self.csv_writer is not None and self.csv_file is not None:
                        self.csv_writer = None
                        self.csv_file.close()
                        self.csv_file = None
                        print(f"[Logger] closed")
                    # conver to gpx
            # close file and convert
            except json.JSONDecodeError:
                pass

    async def handle_kettler_messages(self, messages):
        async for message in messages:
            try:
                data = json.loads(message.payload.decode())
                print(message.topic, data)

                if self.csv_writer is not None and self.csv_file is not None:
                    if 'connected' in self.heartrate and self.heartrate['connected']['payload']\
                            and 'data' in self.heartrate:
                        hr = self.heartrate['data']['payload']['hr']
                        rri = self.heartrate['data']['payload']['rr']
                    else:
                        hr = "?"
                        rri = "?"

                    # TODO: Location task
                    self.csv_writer.writerow({
                        'timestamp': time.time(),
                        'speed': data['payload']['speed'],
                        'cadence': data['payload']['cadence'],
                        'power': data['payload']['realPower'],
                        'distance': data['payload']['calcDistance'],
                        'position_lat': "?",
                        'position_long': "?",
                        'altitude': "?",
                        'grade': "?",
                        'heart_rate': hr,
                        'rri': rri
                    })
            except json.JSONDecodeError:
                pass

    async def handle_heartrate_messages(self, messages):
        async for message in messages:
            try:
                data = json.loads(message.payload.decode())
                print(message.topic, data)
                if message.topic == "heartrate/connected":
                    self.heartrate['connected'] = data
                elif message.topic == "heartrate/data":
                    self.heartrate['data'] = data
            except json.JSONDecodeError:
                pass

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
    mqtt_server = MQTT2Log(mqtt_credentials)
    await mqtt_server.mqtt_connect()


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
