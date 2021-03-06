import asyncio
from asyncio_mqtt import Client, MqttError, Will
import json
import time
from contextlib import AsyncExitStack
from common.json_encoder import EnhancedJSONEncoder

def handle_pattern(topic_pattern):
    def _handle_pattern(f):
        f.topic_pattern = topic_pattern
        return f
    return _handle_pattern

class Component2MQTT:
    def __init__(self, mqtt):
        self.mqtt = mqtt
        self.client = None
        self.handler_tasks = []

        self.handlers = dict()

    async def mqtt_connect(self, will_topic):
        while True:
            try:
                async with AsyncExitStack() as stack:
                    self.client = Client(self.mqtt['server'],
                                         port=self.mqtt['port'],
                                         will=Will(f"{self.mqtt['base_topic']}/status/{will_topic}",
                                                   '{"connected": false}',
                                                   retain=True))

                    await stack.enter_async_context(self.client)
                    print("[MQTT] Connected.")

                    await self.update_mqtt(f"status/{will_topic}", {"connected": True})
                    await self.on_connect()

                    # create handler tasks
                    # find all registered handlers in class attributes
                    for func in self.__class__.__dict__.values():
                        if callable(func) and hasattr(func, "topic_pattern"):
                            topic_pattern = getattr(func, "topic_pattern")
                            messages = await stack.enter_async_context(
                                self.client.filtered_messages(f"{self.mqtt['base_topic']}/{topic_pattern}"))
                            self.handler_tasks.append(asyncio.create_task(func(self, messages)))
                            await self.client.subscribe(f"{self.mqtt['base_topic']}/{topic_pattern}")

                    try:
                        if len(self.handlers):
                            await asyncio.gather(*self.handler_tasks)
                        else:
                            while True:
                                await asyncio.sleep(3600)
                    except asyncio.CancelledError:
                        await self.on_cancel()
                        await self.update_mqtt(f"status/{will_topic}", {"connected": False})
                        for task in self.handler_tasks:
                            await self.cancel_task(task)
                        return
            except MqttError as e:
                print(f"[MQTT] Disconnected: {str(e)}. Reconnecting...")
                await self.on_disconnect()
                await asyncio.sleep(5)

    async def on_connect(self):
        return

    async def on_disconnect(self):
        return

    async def on_cancel(self):
        return

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

    async def send_command(self, key, data):
        await self.client.publish(f"{self.mqtt['base_topic']}/{key}", data)

    async def clear_topic(self, key):
        await self.client.publish(f"{self.mqtt['base_topic']}/{key}", "")

    @staticmethod
    async def cancel_task(task):
        if task.done():
            return
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass