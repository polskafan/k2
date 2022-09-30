import json
from config import power, komoot
from common.komoot_reader import KomootTour


class KomootController:
    def __init__(self, manager):
        self.manager = manager
        self.selected_track = None
        self.tracks = self.load_tracks()

    @staticmethod
    def load_tracks():
        return KomootTour.getTours(user_id=komoot['user_id'])

    async def init_state(self):
        await self.manager.update_mqtt("controller/tracks/komoot", self.tracks)

    async def load_track(self, track):
        try:
            selected = self.tracks[int(track['trackIdx'])]
            self.selected_track = KomootTour(tour_id=selected['tour_id'])
            await self.manager.update_mqtt("controller/track", self.selected_track.get_info())
            await self.manager.send_command("logger/cmnd/start", '{"logLocation": true}')
            return True
        except (IndexError, ValueError, KeyError) as e:
            await self.manager.update_mqtt("controller/track", {"error": str(e)})
            return False

    async def handle_command_message(self, message):
        pass

    async def handle_kettler_message(self, message):
        try:
            data = json.loads(message.payload.decode())
            info = self.selected_track.get_info_at_distance(data['payload']['calcDistance'])
            highlight = self.selected_track.get_highlight_at_distance(data['payload']['calcDistance'])

            await self.manager.update_mqtt("controller/location", info)
            await self.manager.update_mqtt("controller/highlight", highlight)
            await self.manager.send_command("kettler/cmnd/power", int(power['grade'](info.grade)))

            if info.progress >= 1:
                await self.manager.send_command("logger/cmnd/stop", '')
                await self.manager.clear_topic("controller/location")
                await self.manager.clear_track_mode()
        except json.JSONDecodeError:
            pass