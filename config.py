heartrate = {
    'adapter': 'hci0',
    'macs': ['FB:E1:27:30:7A:7D']
}

antplus = {
    'sensor_id': 12345,
    'vendor_id': 0x0fcf,
    'product_id': 0x1008
}

kettler = {
    'port': '/dev/kettler'
}

logger = {
    'path': '/home/pi/k2/logs'
}

gpx = {
    'path': '/home/pi/k2/tracks'
}

komoot = {
    'user_id': 938424577470
}

power = {
    "lower_limit": 25,
    "upper_limit": 600,
    "min_power": 90,
    "max_power": 200,
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