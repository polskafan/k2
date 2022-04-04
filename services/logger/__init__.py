import asyncio
import json
import os
from config import mqtt_credentials, logger as logger_config
from datetime import datetime
import csv
import dataclasses
from typing import IO
from common.mqtt_component import Component2MQTT

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

class MQTT2Log(Component2MQTT):
    def __init__(self, mqtt):
        super().__init__(mqtt)

        self.csv = None
        self.log_location = False
        self.log_heartrate = False
        self.datapoint = LogDatapoint()

        self.register_handler("logger/cmnd/+", self.handle_command_messages)
        self.register_handler("kettler/data", self.handle_kettler_messages)
        self.register_handler("controller/location", self.handle_location_messages)
        self.register_handler("heartrate/+", self.handle_heartrate_messages)

    async def init_state(self):
        await self.update_mqtt("logger/data", {"status": "ready"})

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

            # TODO: convert to gpx ?

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

async def main():
    mqtt_server = MQTT2Log(mqtt_credentials)
    await mqtt_server.mqtt_connect(will_topic="logger")

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
