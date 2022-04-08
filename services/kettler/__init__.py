import asyncio
import os
import time
from config import mqtt_credentials, kettler
from common.kettler import Kettler
from common.mqtt_component import Component2MQTT

class Kettler2MQTT(Component2MQTT):
    def __init__(self, mqtt):
        super().__init__(mqtt)

        self.kettler = None
        self.dist = None
        self.target_power = 100

        self.task = asyncio.create_task(self.kettler_task())

        self.register_handler("kettler/cmnd/+", self.handle_command_messages)

    async def handle_command_messages(self, messages):
        async for message in messages:
            try:
                action = message.topic.split("/")[-1]
                if action == "power":
                    self.target_power = int(message.payload.decode())
                elif action == "reset":
                    print("[Kettler] Reset")
                    await self.cancel_task(self.task)
                    self.task = asyncio.create_task(self.kettler_task())
            except (IndexError, ValueError):
                pass

    async def kettler_task(self):
        while True:
            try:
                # connect to bike
                self.kettler = Kettler(serial_port=kettler['port'])

                print("[Kettler] Bike %s" % await self.kettler.getId())

                await self.kettler.reset()
                await asyncio.sleep(0.2)
                await self.kettler.changeMode()

                # init state
                self.dist = 0
                last_status_timestamp = round(time.monotonic() * 1000)
                last_status_message = None

                while True:
                    status = await self.kettler.setPower(self.target_power)

                    if status is not None:
                        time_elapsed = time.monotonic() - last_status_timestamp
                        last_status_timestamp = time.monotonic()

                        if status['speed'] > 0:
                            speed = status['speed'] / 3.6
                            self.dist += speed * time_elapsed

                        status['calcDistance'] = int(self.dist)

                        if status != last_status_message:
                            await self.update_mqtt("kettler/data", status, precise_timestamps=True)
                            last_status_message = status

                    await asyncio.sleep(0.2)
            except IOError:
                print("[Kettler] IO Error. Reconnecting...")
                try:
                    await self.kettler.close()
                except IOError:
                    pass
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                await asyncio.sleep(0.2)
                print("[Kettler] Disconnected")
                return

async def main():
    mqtt_server = Kettler2MQTT(mqtt_credentials)
    await asyncio.gather(mqtt_server.mqtt_connect(will_topic="kettler"))

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
