import asyncio
from asyncio_mqtt import Client, MqttError, Will
import json
import os
import time
from contextlib import AsyncExitStack
from config import mqtt_credentials, logger as logger_config
from datetime import datetime
import csv
import dataclasses
from typing import IO

@dataclasses.dataclass
class CSVWriter:
    filename: str
    handle: IO[str]
    writer: csv.DictWriter


@dataclasses.dataclass
class LogDatapoint:
    timestamp: int = None
    speed: float = None
    cadence: int = None
    power: int = None
    distance: float = None

    position_lat: float = None
    position_long: float = None
    altitude: float = None
    grade: float = None

    heart_rate: int = None
    rri: float = None

class MQTT2Log:
    def __init__(self, mqtt):
        self.mqtt = mqtt
        self.client = None

        self.command_task = None
        self.kettler_task = None
        self.heartrate_task = None

        self.csv = None
        self.log_location = False
        self.log_heartrate = False
        self.datapoint = LogDatapoint()

    async def mqtt_connect(self):
        while True:
            try:
                async with AsyncExitStack() as stack:
                    self.client = Client(self.mqtt['server'],
                                         port=self.mqtt['port'],
                                         will=Will(f"{self.mqtt['base_topic']}/status/logger", '{"connected": false}', retain=True))

                    await stack.enter_async_context(self.client)
                    print("[MQTT] Connected.")

                    await self.update_mqtt("status/logger", {"connected": True})
                    await self.update_mqtt("logger/data", {"status": "ready"})

                    # handle commands
                    command_messages = await stack.enter_async_context(
                        self.client.filtered_messages(f"{self.mqtt['base_topic']}/logger/cmnd/+"))
                    self.command_task = asyncio.create_task(self.handle_command_messages(command_messages))

                    # handle kettler
                    kettler_messages = await stack.enter_async_context(
                        self.client.filtered_messages(f"{self.mqtt['base_topic']}/kettler/data"))
                    self.kettler_task = asyncio.create_task(self.handle_kettler_messages(kettler_messages))

                    # handle location
                    location_messages = await stack.enter_async_context(
                        self.client.filtered_messages(f"{self.mqtt['base_topic']}/controller/location"))
                    self.location_task = asyncio.create_task(self.handle_location_messages(location_messages))

                    # handle heartrate
                    heartrate_messages = await stack.enter_async_context(
                        self.client.filtered_messages(f"{self.mqtt['base_topic']}/heartrate/+"))
                    self.heartrate_task = asyncio.create_task(self.handle_heartrate_messages(heartrate_messages))

                    await self.client.subscribe(f"{self.mqtt['base_topic']}/logger/cmnd/+")
                    await self.client.subscribe(f"{self.mqtt['base_topic']}/kettler/data")
                    await self.client.subscribe(f"{self.mqtt['base_topic']}/controller/location")
                    await self.client.subscribe(f"{self.mqtt['base_topic']}/heartrate/connected")
                    await self.client.subscribe(f"{self.mqtt['base_topic']}/heartrate/data")

                    try:
                        await asyncio.gather(self.command_task, self.kettler_task,
                                             self.location_task, self.heartrate_task)
                    except asyncio.CancelledError:
                        await self.update_mqtt("status/logger", {"connected": False})
                        return
            except MqttError as e:
                print(f"[MQTT] Disconnected: {str(e)}. Reconnecting...")

    async def open_log(self, data):
        if 'filename' in data and len(data['filename']) > 0:
            filename = os.path.join(logger_config['path'], data['filename'])
        else:
            filename = os.path.join(logger_config['path'],
                                    "%s.log.csv" % datetime.now().strftime("%Y-%m-%d_%H.%M.%S"))

        handle = open(filename, "w", newline="", encoding="utf-8")
        writer = csv.DictWriter(handle, fieldnames=[f.name for f in dataclasses.fields(self.datapoint)])
        writer.writeheader()

        print(f"[Logger] Log opened: {filename}")
        self.csv = CSVWriter(filename=filename, handle=handle, writer=writer)

        self.log_location = 'logLocation' in data and data['logLocation']

        await self.update_mqtt("logger/data", {'status': 'open',
                                               'filename': filename,
                                               'logLocation': self.log_location})

    async def close_log(self):
        if self.csv is not None:
            self.csv.handle.close()

            print(f"[Logger] Log closed: {self.csv.filename}")
            await self.update_mqtt("logger/data", {'status': 'closed', 'filename': self.csv.filename})

            # convert to gpx ?

            self.csv = None
            self.log_location = False

    async def handle_command_messages(self, messages):
        async for message in messages:
            try:
                action = message.topic.split("/")[-1]
                if action == "start":
                    await self.close_log()

                    try:
                        data = json.loads(message.payload.decode())
                        await self.open_log(data)
                    except json.JSONDecodeError as e:
                        await self.update_mqtt("logger/data", {'error': str(e)})
                elif action == "stop":
                    await self.close_log()

            except json.JSONDecodeError:
                pass

    async def handle_kettler_messages(self, messages):
        async for message in messages:
            try:
                data = json.loads(message.payload.decode())
                if self.csv is not None:
                    self.datapoint.timestamp = data['_timestamp']
                    self.datapoint.speed = data['payload']['speed']
                    self.datapoint.cadence = data['payload']['cadence']
                    self.datapoint.power = data['payload']['realPower']
                    self.datapoint.distance = data['payload']['calcDistance']

                    if not self.log_location:
                        self.csv.writer.writerow(dataclasses.asdict(self.datapoint))
            except json.JSONDecodeError:
                pass

    async def handle_heartrate_messages(self, messages):
        async for message in messages:
            try:
                data = json.loads(message.payload.decode())
                if message.topic == f"{self.mqtt['base_topic']}/heartrate/connected":
                    self.log_heartrate = data['payload']
                elif message.topic == f"{self.mqtt['base_topic']}/heartrate/data":
                    if 'hr' in data['payload']:
                        self.datapoint.heart_rate = data['payload']['hr']

                    if 'rri' in data['payload']:
                        self.datapoint.rri = data['payload']['rri']
            except json.JSONDecodeError:
                pass

    async def handle_location_messages(self, messages):
        async for message in messages:
            try:
                data = json.loads(message.payload.decode())
                self.datapoint.position_lat = data['payload']['latitude']
                self.datapoint.position_long = data['payload']['longitude']
                self.datapoint.altitude = data['payload']['elevation']
                self.datapoint.grade = data['payload']['grade']

                if self.log_location:
                    self.csv.writer.writerow(dataclasses.asdict(self.datapoint))
            except json.JSONDecodeError:
                pass

    async def update_mqtt(self, key, data):
        data = {
            'payload': data,
            '_timestamp': int(time.time())
        }

        if self.client is not None:
            await self.client.publish(f"{self.mqtt['base_topic']}/{key}",
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
