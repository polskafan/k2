heartrate_adapter = "hci0"

heartrate_macs = [
    "FB:E1:27:30:7A:7D"
]

kettler = {
    'port': '/dev/ttyUSB0'
}

logger = {
    'path': '/home/pi/k2/logs'
}

gpx_tracks = {
    'path': '/home/pi/k2/tracks'
}

def power_conversion(grade):
    idle_power = 100
    max_power = 200
    max_percentage = 0.15
    return min(max_power, max(max_power * (grade / max_percentage), 0) + idle_power)

mqtt_credentials = {
    'server': '127.0.0.1',
    'port': 1883,
    'base_topic': 'k2'
}