import asyncio
import json
import os

from common.mqtt_component import Component2MQTT
from config import mqtt_credentials, gpx, power_conversion
import glob
from common.gpx_reader import GPXTrack


class GPXController2MQTT(Component2MQTT):
    def __init__(self, mqtt):
        super().__init__(mqtt)

        self.track_mode = None
        self.selected_track = None
        self.tracks = self.load_tracks()

        self.register_handler("controller/cmnd/+", self.handle_command_messages)
        self.register_handler("kettler/data", self.handle_kettler_messages)

    @staticmethod
    def load_tracks():
        gpx_files = glob.glob(os.path.join(gpx['path'], "*.gpx"))
        return [GPXTrack(filename=gpx_file) for gpx_file in gpx_files]

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
                                await self.send_command("logger/cmnd/start", '{"logLocation": true}')
                                await self.send_command("kettler/cmnd/reset", '')
                            except (IndexError, ValueError, KeyError) as e:
                                await self.update_mqtt("controller/track", {"error": str(e)})
                except json.JSONDecodeError as e:
                    print(str(e), message.payload.decode())
                    pass

    async def handle_kettler_messages(self, messages):
        async for message in messages:
            if self.track_mode == "gpx":
                try:
                    data = json.loads(message.payload.decode())
                    info = self.selected_track.get_info_at_distance(data['payload']['calcDistance'])
                    await self.update_mqtt("controller/location", info)
                    await self.send_command("kettler/cmnd/power", int(power_conversion(info.grade)))

                    if info.progress >= 1:
                        await self.send_command("logger/cmnd/stop", '')
                        self.track_mode = None
                except json.JSONDecodeError:
                    pass


async def main():
    mqtt_server = GPXController2MQTT(mqtt_credentials)
    await asyncio.gather(mqtt_server.mqtt_connect(will_topic="gpx"))


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
