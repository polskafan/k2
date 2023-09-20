import gpxpy
import gpxpy.gpx
import math
import flexpolyline
import bisect
from itertools import accumulate
import requests
from dataclasses import dataclass
import time


@dataclass
class DistanceTrackInfo:
    latitude: float
    longitude: float
    elevation: float
    grade: float
    progress: float


class JSONEntity:
    @staticmethod
    def encode(o):
        if isinstance(o, JSONEntity):
            return o.to_json()
        elif isinstance(o, list):
            return [JSONEntity.encode(lo) for lo in o]
        else:
            return o

    def to_json(self):
        return dict([(a, JSONEntity.encode(self.__getattribute__(a))) for a in self.attributes])


class Highlight(JSONEntity):
    def __init__(self, name, images, front_image):
        self.attributes = ['name', 'images', 'front_image']
        self.name = name
        self.images = images
        self.front_image = front_image
        pass


class Image(JSONEntity):
    def __init__(self, image_id, src, creator):
        self.attributes = ['image_id', 'src', 'creator']
        self.image_id = image_id
        self.src = "/".join(src.split("/")[0:-1])+"/"
        self.creator = creator
        pass


class Creator(JSONEntity):
    def __init__(self, username, display_name, avatar):
        self.attributes = ['username', 'display_name', 'avatar']
        self.username = username
        self.display_name = display_name
        self.avatar = "/".join(avatar.split("/")[0:-2])+"/"
        pass


class KomootTour:
    accumulated_distances = []
    points = []

    gpx = None

    def __init__(self, tour_id):
        self.tour_id = tour_id

        # get tour info
        r_tour = requests.get('https://api.komoot.de/v007/%s' % tour_id)
        d_tour = r_tour.json()

        # get coordinates
        r_cord = requests.get('https://api.komoot.de/v007/%s/coordinates/' % tour_id)
        d_cord = r_cord.json()

        self.coordinates = [gpxpy.gpx.GPXTrackPoint(latitude=point['lat'],
                                                    longitude=point['lng'],
                                                    elevation=point['alt']) for point in d_cord['items']]

        # get highlights
        r_tl = requests.get('https://api.komoot.de/v007/%s/timeline/' % tour_id)
        d_tl = r_tl.json()

        def format_highlight(highlight):
            try:
                return Highlight(name=highlight['name'],
                                 images=[Image(image_id=image['id'],
                                               src=image['src'],
                                               creator=Creator(username=image['_embedded']['creator']['username'],
                                                               display_name=image['_embedded']['creator']['display_name'],
                                                               avatar=image['_embedded']['creator']['avatar']['src']))
                                         for image in highlight['_embedded']['images']['_embedded']['items']],
                                 front_image=Image(image_id=highlight['_embedded']['front_image']['id'],
                                                   src=highlight['_embedded']['front_image']['src'],
                                                   creator=Creator(username=highlight['_embedded']['front_image']
                                                                   ['_embedded']['creator']['username'],
                                                                   display_name=highlight['_embedded']['front_image']
                                                                   ['_embedded']['creator']['display_name'],
                                                                   avatar=highlight['_embedded']['front_image']
                                                                   ['_embedded']['creator']['avatar']['src'])))
            except KeyError:
                return None

        self.highlights = dict([(entry['index'], format_highlight(entry['_embedded']['reference']))
                                for entry in d_tl['_embedded']['items']
                                if entry['type'] == "highlight"
                                and format_highlight(entry['_embedded']['reference']) is not None])

        # pair start and end points for each waypoint-segment
        self.points = list(zip(self.coordinates[:-1], self.coordinates[1:]))

        # add final track segment
        self.points.append((self.coordinates[-1], self.coordinates[-1]))

        # distances
        distances = [self.distance(start, end) for start, end in self.points]

        # accumulated distances (total distance)
        self.accumulated_distances = list(accumulate(distances))

        self.info = {
            'name': d_tour['name'],
            'distance': self.accumulated_distances[-1],
            'ascent_m': sum(filter(lambda x: x >= 0, self.ascends_m(self.points))),
            'descend_m': sum(filter(lambda x: x < 0, self.ascends_m(self.points))),
            'ascent_%': max(self.ascends_percent(self.points))*100,
            'descend_%': min(self.ascends_percent(self.points))*100,
            'polyline': self.to_polyline(),
            'highlights': [self.accumulated_distances[hl_idx] for hl_idx in self.highlights.keys()]
        }

    def print_summary(self):
        print(self.info['name'])
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
        try:
            segment_progress = max(0, min(1, 1 - (self.accumulated_distances[dist_index] - at_distance) / segment_distance))
        except ZeroDivisionError:
            segment_progress = 1

        # interpolate coordinates
        progress_latitude = (1-segment_progress)*start.latitude + segment_progress*end.latitude
        progress_longitude = (1-segment_progress)*start.longitude + segment_progress*end.longitude
        progress_elevation = (1-segment_progress)*start.elevation + segment_progress*end.elevation

        progress = max(0, min(1, at_distance / self.accumulated_distances[-1]))

        return DistanceTrackInfo(progress_latitude, progress_longitude, progress_elevation, grade, progress)

    def get_highlight_at_distance(self, at_distance):
        dist_index = bisect.bisect_left(self.accumulated_distances, at_distance)

        if dist_index >= len(self.points):
            dist_index = len(self.points) - 1

        # find the last highlight we passed
        hl_indices = list(self.highlights.keys())
        hl_index = hl_indices[bisect.bisect_right(hl_indices, dist_index) - 1]

        # if we are within 500m of the highlight return it
        if hl_index <= dist_index and self.accumulated_distances[dist_index] - self.accumulated_distances[hl_index] <= 500:
            return self.highlights[hl_index]
        else:
            return None

    def get_progress_at_distance(self, at_distance):
        # force progress to [0, 1]
        return max(0, min(1, at_distance/self.accumulated_distances[-1]))

    def to_polyline(self):
        return flexpolyline.encode([(point.latitude, point.longitude, point.elevation) for point in self.coordinates],
                                   third_dim=flexpolyline.ALTITUDE, precision=6, third_dim_precision=2)

    @staticmethod
    def ascends_m(segments):
        return [(end.elevation - start.elevation) for start, end in segments]

    @staticmethod
    def ascends_percent(segments):
        def get_ascend(start, end):
            try:
                return (end.elevation - start.elevation)/KomootTour.distance(start, end)
            except ZeroDivisionError:
                return 0

        return [get_ascend(start, end) for start, end in segments]

    @staticmethod
    def distance(start, end):
        return KomootTour.haversine(coord1=(start.latitude, start.longitude),
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

    @staticmethod
    def getTours(user_id):
        for _ in range(5):
            try:
                r_tour = requests.get('https://www.komoot.com/api/v007/users/%d/tours/?type=tour_planned&status=public' % user_id)
                break
            except requests.exceptions.RequestException:
                time.sleep(10)
                pass
        d_tour = r_tour.json()

        tours = []
        for t in d_tour['_embedded']['tours']:
            tid = t['_links']['self']['href'].replace("http://api.komoot.de/v007/", "")
            tours.append({'name': t['name'], 'tour_id': tid, 'distance': t['distance']})

        return tours


if __name__ == '__main__':
    t = KomootTour(tour_id='smart_tours/95408')
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

    print(t.get_highlight_at_distance(1700).to_json())

    # out of bounds test
    print("OOB Test")
    print(t.get_info_at_distance(-1))
    print(t.get_info_at_distance(37000))


