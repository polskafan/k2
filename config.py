heartrate = {
    'adapter': 'hci0',
    'macs': ['FB:E1:27:30:7A:7D']
}

antplus = {
    'device': '/dev/ttyUSB0',
    'sensor_id': 17012
}

kettler = {
    'port': '/dev/ttyUSB1'
}

logger = {
    'path': '/home/pi/k2/logs'
}

gpx = {
    'path': '/home/pi/k2/tracks'
}

power = {
    "lower_limit": 25,
    "upper_limit": 600,
    "min_power": 80,
    "max_power": 280,
    "max_grade": 0.15,
    "minmax": lambda value, lower, upper: min(upper, max(value, lower)),
    "grade": lambda grade: power['minmax'](value=(power['max_power'] - power['min_power']) * (grade / power['max_grade']) + power['min_power'],
                                           lower=power['min_power'],
                                           upper=power['max_power']),
    "resistance": lambda resistance: power['min_power'] + resistance * (power['max_power'] - power['min_power'])
}

mqtt_credentials = {
    'server': '127.0.0.1',
    'port': 1883,
    'base_topic': 'k2'
}