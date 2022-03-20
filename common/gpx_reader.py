import gpxpy
import gpxpy.gpx
import math
import flexpolyline
import bisect
from itertools import accumulate
from dataclasses import dataclass

@dataclass
class GPXTrackOverview:
    filename: str
    trackname: str
    distance: float
    ascent_m: float
    descend_m: float
    max_ascent_percent: float
    max_descend_percent: float
    polyline: str


@dataclass
class DistanceTrackInfo:
    latitude: float
    longitude: float
    elevation: float
    grade: float
    progress: float

class GPXTrack:
    accumulated_distances = []
    points = []

    gpx = None

    def __init__(self, filename):
        gpx_file = open(filename, 'r', encoding="utf-8")
        self.gpx = gpxpy.parse(gpx_file)

        # pair start and end points for each waypoint-segment
        points = [point for track in self.gpx.tracks for segment in track.segments for point in segment.points]
        self.points = list(zip(points[:-1], points[1:]))

        # distances
        distances = [self.distance(start, end) for start, end in self.points]

        # accumulated distances (total distance)
        self.accumulated_distances = list(accumulate(distances))

        self.info = GPXTrackOverview(
            filename=filename,
            trackname="\n".join([track.name for track in self.gpx.tracks]),
            distance=self.accumulated_distances[-1],
            ascent_m=sum(filter(lambda x: x >= 0, self.ascends_m(self.points))),
            descend_m=sum(filter(lambda x: x < 0, self.ascends_m(self.points))),
            max_ascent_percent=max(self.ascends_percent(self.points))*100,
            max_descend_percent=min(self.ascends_percent(self.points))*100,
            polyline=self.to_polyline())

    def print_summary(self):
        print("\n".join([track.name for track in self.gpx.tracks]))
        print("Total distance: %0.1fm" % self.accumulated_distances[-1])

    def get_info(self):
        return self.info

    def get_info_at_distance(self, at_distance):
        dist_index = bisect.bisect_left(self.accumulated_distances, at_distance)

        if dist_index >= len(self.points):
            dist_index = len(self.points) - 1

        start, end = self.points[dist_index]

        segment_distance = self.distance(start, end)
        try:
            grade = (end.elevation - start.elevation) / segment_distance
        except ZeroDivisionError:
            grade = 0

        # force progress to [0, 1]
        segment_progress = max(0, min(1, 1 - (self.accumulated_distances[dist_index] - at_distance) / segment_distance))

        # interpolate coordinates
        progress_latitude = (1-segment_progress)*start.latitude + segment_progress*end.latitude
        progress_longitude = (1-segment_progress)*start.longitude + segment_progress*end.longitude
        progress_elevation = (1 - segment_progress) * start.elevation + segment_progress * end.elevation

        progress = max(0, min(1, at_distance / self.accumulated_distances[-1]))

        return DistanceTrackInfo(progress_latitude, progress_longitude, progress_elevation, grade, progress)

    def get_progress_at_distance(self, at_distance):
        # force progress to [0, 1]
        return max(0, min(1, at_distance/self.accumulated_distances[-1]))

    def to_polyline(self):
        return flexpolyline.encode([(point.latitude, point.longitude, point.elevation) for track in self.gpx.tracks
                                    for segment in track.segments
                                    for point in segment.points],
                                   third_dim=flexpolyline.ALTITUDE,
                                   precision=6,
                                   third_dim_precision=2)

    @staticmethod
    def ascends_m(segments):
        return [(end.elevation - start.elevation) for start, end in segments]

    @staticmethod
    def ascends_percent(segments):
        def get_ascend(start, end):
            try:
                return (end.elevation - start.elevation)/GPXTrack.distance(start, end)
            except ZeroDivisionError:
                return 0

        return [get_ascend(start, end) for start, end in segments]

    @staticmethod
    def distance(start, end):
        return GPXTrack.haversine(coord1=(start.latitude, start.longitude),
                                  coord2=(end.latitude, end.longitude))

    @staticmethod
    def haversine(coord1, coord2):
        R = 6372800  # Earth radius in meters
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2

        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


if __name__ == '__main__':
    t = GPXTrack(filename=r'fass.gpx')
    print(t.accumulated_distances[0:3])
    print(t.accumulated_distances[-1])

    print(t.get_info_at_distance(0))
    print(t.get_info_at_distance(15.74293762079552))
    print(t.get_info_at_distance(34.74293762079552))
    print(t.get_info_at_distance(34.74293762079553))
    print(t.get_info_at_distance(42))
    print(t.get_info_at_distance(49.493937106553695))
    print(t.get_info_at_distance(49.493937106553696))
    print(t.get_info_at_distance(25000))
    print(t.get_info_at_distance(25283.49829062201))

    # out of bounds test
    print("OOB Test")
    print(t.get_info_at_distance(-1))
    print(t.get_info_at_distance(37000))
