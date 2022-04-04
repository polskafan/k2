import asyncio
from asyncio_mqtt import Client, MqttError, Will
import json
import time
from contextlib import AsyncExitStack
from common.json_encoder import EnhancedJSONEncoder

class Component2MQTT:
    def __init__(self, mqtt):
        self.mqtt = mqtt
        self.client = None
        self.handler_tasks = []
        self.handlers = dict()

    def register_handler(self, topic_pattern, handler):
        self.handlers[topic_pattern] = handler

    async def mqtt_connect(self, will_topic):
        while True:
            try:
                async with AsyncExitStack() as stack:
                    self.client = Client(self.mqtt['server'],
                                         port=self.mqtt['port'],
                                         will=Will(f"{self.mqtt['base_topic']}/status/{will_topic}", '{"connected": false}',
                                                   retain=True))

                    await stack.enter_async_context(self.client)
                    print("[MQTT] Connected.")

                    await self.update_mqtt(f"status/{will_topic}", {"connected": True})
                    await self.init_state()

                    # create handler tasks
                    for (topic_pattern, handler) in self.handlers.items():
                        messages = await stack.enter_async_context(
                            self.client.filtered_messages(f"{self.mqtt['base_topic']}/{topic_pattern}"))
                        self.handler_tasks.append(asyncio.create_task(handler(messages)))
                        await self.client.subscribe(f"{self.mqtt['base_topic']}/{topic_pattern}")

                    try:
                        if len(self.handlers):
                            await asyncio.gather(*self.handler_tasks)
                        else:
                            while True:
                                await asyncio.sleep(3600)
                    except asyncio.CancelledError:
                        await self.update_mqtt(f"status/{will_topic}", {"connected": False})
                        for task in self.handler_tasks:
                            await self.cancel_task(task)
                        return
            except MqttError as e:
                print(f"[MQTT] Disconnected: {str(e)}. Reconnecting...")
                await asyncio.sleep(5)

    async def init_state(self):
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

    async def cancel_task(self, task):
        if task.done():
            return
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass