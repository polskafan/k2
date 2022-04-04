import asyncio
import os

from common.mqtt_component import Component2MQTT
from config import mqtt_credentials
from gpx import GPXController
from antplus import ANTController
import json

class ControllerManager2MQTT(Component2MQTT):
    def __init__(self, mqtt):
        super().__init__(mqtt)

        self.track_mode = None

        self.register_handler("controller/cmnd/+", self.handle_command_messages)
        self.register_handler("kettler/data", self.handle_kettler_messages)

        self.controllers = {
            "gpx": GPXController(self)
        }

        self.ant = ANTController(self)

    async def set_track_mode(self, track_mode = None):
        self.track_mode = track_mode
        await self.update_mqtt("controller/trackMode", track_mode)

    async def init_state(self):
        await self.update_mqtt("controller/trackMode", None)
        await self.update_mqtt("controller/track", None)
        await self.clear_topic("controller/location")

        for controller in self.controllers.values():
            await controller.init_state()

    async def handle_command_messages(self, messages):
        async for message in messages:
            action = message.topic.split("/")[-1]
            if action == "track":
                try:
                    data = json.loads(message.payload.decode())
                    if 'trackMode' in data:
                        controller = self.controllers.get(data['trackMode'])
                        if await controller.load_track(data):
                            self.track_mode = data['trackMode']
                            await self.update_mqtt("controller/trackMode", self.track_mode)
                            await self.send_command("kettler/cmnd/reset", '')
                except json.JSONDecodeError:
                    pass
            else:
                controller = self.controllers.get(self.track_mode)
                if controller is not None:
                    await controller.handle_command_message(message)

    async def handle_kettler_messages(self, messages):
        async for message in messages:
            controller = self.controllers.get(self.track_mode)
            if controller is not None:
                await controller.handle_kettler_message(message)

            await self.ant.handle_kettler_message(message)

    async def ant_power(self, power):
        # auto enable ant controller, if no other controller is active
        if self.track_mode is None:
            await self.set_track_mode("ant")

        if self.track_mode == "ant":
            await self.send_command("kettler/cmnd/power", power)

async def main():
    mqtt_server = ControllerManager2MQTT(mqtt_credentials)
    await asyncio.gather(mqtt_server.mqtt_connect(will_topic="controller"))

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
