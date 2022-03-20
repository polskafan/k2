import serial
import aioserial


class Kettler:
    def __init__(self, serial_port):
        self.serial_port = aioserial.AioSerial(serial_port, baudrate=9600, parity=serial.PARITY_NONE, timeout=1)
        self.CHANGE_MODE = "CM\r\n"
        self.GET_ID = "ID\r\n"
        self.GET_STATUS = "ST\r\n"
        self.SET_POWER = "PW %d\r\n"
        self.RESET = "RS\r\n"

    async def rpc(self, message):
        await self.serial_port.write_async(message.encode("utf-8"))
        self.serial_port.flush()
        response = (await self.serial_port.readline_async()).rstrip()  # rstrip trims trailing whitespace
        return response

    async def changeMode(self):
        # put the bike in remote control mode
        return (await self.rpc(self.CHANGE_MODE)).decode("utf-8")

    async def reset(self):
        return (await self.rpc(self.RESET)).decode("utf-8")

    async def getId(self):
        return (await self.rpc(self.GET_ID)).decode("utf-8")

    async def setPower(self, power):
        status_line = (await self.rpc(self.SET_POWER % power)).decode("utf-8")
        return self.decode_status(status_line)

    async def readStatus(self):
        status_line = (await self.rpc(self.GET_STATUS)).decode("utf-8")
        return self.decode_status(status_line)

    @staticmethod
    def decode_status(status_line):
        # heartRate cadence speed distanceInFunnyUnits destPower energy timeElapsed realPower
        # 000 052 095 000 030 0001 00:12 030
        segments = status_line.split()

        if len(segments) == 8:
            result = {
                # 'pulse': int(segments[0]),
                'cadence': int(segments[1]),
                'speed': float(segments[2]) / 10,
                'distance': int(segments[3]) / 10,
                'destPower': int(segments[4]),
                'energy': int(segments[5]),
                'timeElapsed': segments[6],
                'realPower': int(segments[7]),
            }
            return result
        else:
            print("Received bad status string from Kettler: [%s]" % status_line)
            return None