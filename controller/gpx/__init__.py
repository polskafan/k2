import asyncio
from asyncio_mqtt import Client, MqttError, Will
import json
import os
import time
from contextlib import AsyncExitStack
from config import mqtt_credentials, gpx_tracks, power_conversion
import glob
from common.gpx_reader import GPXTrack
from common.json_encoder import EnhancedJSONEncoder



class GPXController2MQTT:
    def __init__(self, mqtt):
        self.mqtt = mqtt
        self.client = None
        self.kettler = None

        self.command_task = None
        self.kettler_task = None

        self.track_mode = None
        self.selected_track = None
        self.tracks = self.load_tracks()

    @staticmethod
    def load_tracks():
        gpx_files = glob.glob(os.path.join(gpx_tracks['path'], "*.gpx"))
        return [GPXTrack(filename=gpx_file) for gpx_file in gpx_files]

    async def mqtt_connect(self):
        while True:
            try:
                async with AsyncExitStack() as stack:
                    self.client = Client(self.mqtt['server'],
                                         port=self.mqtt['port'],
                                         will=Will(f"{self.mqtt['base_topic']}/status/gpx", '{"connected": false}', retain=True))

                    await stack.enter_async_context(self.client)
                    print("[MQTT] Connected.")

                    await self.update_mqtt("status/gpx", {"connected": True})
                    await self.update_tracks()

                    # handle commands
                    command_messages = await stack.enter_async_context(self.client.filtered_messages(f"{self.mqtt['base_topic']}/controller/cmnd/+"))
                    self.command_task = asyncio.create_task(self.handle_command_messages(command_messages))

                    # handle kettler
                    kettler_messages = await stack.enter_async_context(self.client.filtered_messages(f"{self.mqtt['base_topic']}/kettler/data"))
                    self.kettler_task = asyncio.create_task(self.handle_kettler_messages(kettler_messages))

                    await self.client.subscribe(f"{self.mqtt['base_topic']}/controller/cmnd/+")
                    await self.client.subscribe(f"{self.mqtt['base_topic']}/kettler/data")

                    try:
                        await asyncio.gather(self.command_task, self.kettler_task)
                    except asyncio.CancelledError:
                        await self.update_mqtt("status/gpx", {"connected": False})
                        self.client = None
                        return
            except MqttError as e:
                print(f"[MQTT] Disconnected: {str(e)}. Reconnecting...")
                self.client = None
                pass

    async def update_tracks(self):
        await self.update_mqtt("controller/tracks/gpx", [track.get_info() for track in self.tracks])

    async def handle_command_messages(self, messages):
        async for message in messages:
            action = message.topic.split("/")[-1]
            if action == "track":
                try:
                    data = json.loads(message.payload.decode())
                    if 'trackMode' in data:
                        self.track_mode = data['trackMode']
                        if data['trackMode'] == "gpx":
                            try:
                                self.selected_track = self.tracks[int(data['trackIdx'])]
                                await self.update_mqtt("controller/track", self.selected_track.get_info())
                                await self.send_command("kettler/cmnd/reset", "")
                            except (IndexError, ValueError, KeyError) as e:
                                await self.update_mqtt("controller/track", {"error": str(e)})
                except json.JSONDecodeError:
                    pass

    async def handle_kettler_messages(self, messages):
        async for message in messages:
            if self.track_mode == "gpx":
                try:
                    data = json.loads(message.payload.decode())
                    info = self.selected_track.get_info_at_distance(data['payload']['calcDistance'])
                    await self.update_mqtt("controller/location", info)
                    await self.send_command("kettler/cmnd/power", int(power_conversion(info.grade)))
                except json.JSONDecodeError:
                    pass

    async def send_command(self, key, data):
        await self.client.publish(f"{self.mqtt['base_topic']}/{key}", data)

    async def update_mqtt(self, key, data, precise_timestamps = False):
        if precise_timestamps:
            data = {
                'payload': data,
                '_timestamp': int(time.time_ns() / 1000000) / 1000
            }
        else:
            data = {
                'payload': data,
                '_timestamp': int(time.time())
            }

        if self.client is not None:
            await self.client.publish(f"{self.mqtt['base_topic']}/{key}",
                                      json.dumps(data, cls=EnhancedJSONEncoder),
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
    mqtt_server = GPXController2MQTT(mqtt_credentials)
    await asyncio.gather(mqtt_server.mqtt_connect())


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
