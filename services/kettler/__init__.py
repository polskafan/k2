import asyncio
from asyncio_mqtt import Client, MqttError, Will
import json
import os
import time
from contextlib import AsyncExitStack
from config import mqtt_credentials, kettler
from common.kettler import Kettler

class Kettler2MQTT:
    def __init__(self, mqtt):
        self.mqtt = mqtt
        self.client = None
        self.kettler = None
        self.dist = None
        self.target_power = 100

        self.task = asyncio.create_task(self.kettler_task())

    async def mqtt_connect(self):
        while True:
            try:
                async with AsyncExitStack() as stack:
                    self.client = Client(self.mqtt['server'],
                                         port=self.mqtt['port'],
                                         will=Will(f"{self.mqtt['base_topic']}status/kettler", '{"connected": false}',
                                                   retain=True))

                    await stack.enter_async_context(self.client)
                    print("[MQTT] Connected.")

                    await self.update_mqtt("status/kettler", {"connected": True})

                    try:
                        cmd_topic = f"{self.mqtt['base_topic']}/kettler/cmnd/+"
                        async with self.client.filtered_messages(cmd_topic) as messages:
                            await self.client.subscribe(cmd_topic)
                            async for message in messages:
                                try:
                                    action = message.topic.split("/")[-1]
                                    if action == "power":
                                        print(await self.kettler.setPower(int(message.payload.decode())))
                                    elif action == "reset":
                                        print("[Kettler] Reset")
                                        await self.cancel_task(self.task)
                                        self.task = asyncio.create_task(self.kettler_task())
                                except (IndexError, ValueError):
                                    pass
                    except asyncio.CancelledError:
                        await self.update_mqtt("status/kettler", {"connected": False})
                        self.client = None
                        return
            except MqttError as e:
                print(f"[MQTT] Disconnected: {str(e)}. Reconnecting...")
                self.client = None
                pass

    async def kettler_task(self):
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
            try:
                status = await self.kettler.readStatus()

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
            except asyncio.CancelledError:
                await asyncio.sleep(0.2)
                print("[Kettler] Disconnected")
                break

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
    mqtt_server = Kettler2MQTT(mqtt_credentials)
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
