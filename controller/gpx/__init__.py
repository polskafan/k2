import json
import os

from config import gpx, power
import glob
from common.gpx_reader import GPXTrack


class GPXController:
    def __init__(self, manager):
        self.manager = manager
        self.selected_track = None
        self.tracks = self.load_tracks()

    @staticmethod
    def load_tracks():
        gpx_files = glob.glob(os.path.join(gpx['path'], "*.gpx"))
        return [GPXTrack(filename=gpx_file) for gpx_file in gpx_files]

    async def init_state(self):
        await self.manager.update_mqtt("controller/tracks/gpx", [track.get_info() for track in self.tracks])

    async def load_track(self, track):
        try:
            self.selected_track = self.tracks[int(track['trackIdx'])]
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
            await self.manager.update_mqtt("controller/location", info)
            await self.manager.send_command("kettler/cmnd/power", int(power['grade'](info.grade)))

            if info.progress >= 1:
                await self.manager.send_command("logger/cmnd/stop", '')
                await self.manager.clear_topic("controller/location")
                await self.manager.clear_track_mode()
        except json.JSONDecodeError:
            pass