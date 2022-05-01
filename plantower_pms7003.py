import serial

FIRST_BYTE_FOR_CRC = 0
LAST_BYTE_FOR_CRC = 30
PROTOCOL_CRC_BYTE = 31
PROTOCOL_DATA_1_HIGH_BYTE = 4
PROTOCOL_STARTING_BYTE = b'B'
PROTOCOL_START_FRAME = b'BM'
PROTOCOL_DATA_13_HIGH_BYTE = 28

COMMAND_START = b'\x42\x4d'
COMMAND_SLEEP = b'\xe4\x00\x00'
COMMAND_WAKE = b'\xe4\x00\x01'
COMMAND_MODE_PASIVE = b'\xe1\x00\x00'
COMMAND_MODE_ACTIVE = b'\xe1\x00\x01'
COMMAND_READ_PASSIVE = b'\xe2\x00\x00'

UNITS_UG_M3 = "ug/m3"
UNITS_N_PARTICLES_0_1_L = "n/0.1L"

protocol = ("PM1 CF1", "PM2.5 CF1", "PM10 CF1", "PM1", "PM2.5", "PM10",
            "PM0.3", "PM0.5", "PM1.0", "PM2.5", "PM5.0", "PM10",
            "Reserved", "Data Check")

units = (UNITS_UG_M3, UNITS_UG_M3, UNITS_UG_M3, UNITS_UG_M3, UNITS_UG_M3, UNITS_UG_M3,
         UNITS_N_PARTICLES_0_1_L, UNITS_N_PARTICLES_0_1_L, UNITS_N_PARTICLES_0_1_L,
         UNITS_N_PARTICLES_0_1_L, UNITS_N_PARTICLES_0_1_L, UNITS_N_PARTICLES_0_1_L, "", "")

class PMS7003:
    PASSIVE = 0
    ACTIVE = 1
    _mode = ACTIVE

    def __init__(self, port: str, reset=0):
        self.port = port
        self.reset = reset
        self.serial = serial.Serial(port, baudrate=9600)

    def read(self) -> {}:
        serial_data = bytearray(0)

        if not self.serial.is_open:
            self.serial.open()

        if self._mode == self.PASSIVE:
            self._send_command(COMMAND_READ_PASSIVE)

        self._serial_sync_start_frame()

        serial_data.extend(PROTOCOL_START_FRAME)
        for i in range(2, 32):
            serial_data.extend(self.serial.read())

        self.serial.close()

        if self._check_crc(serial_data):
            return self._parse_message(serial_data)
        else:
            raise Exception("CRC failed")

    def _serial_sync_start_frame(self):
        serial_data = bytearray(0)
        while 1:
            serial_data.extend(bytearray(self.serial.read()))
            if serial_data.find(bytearray(PROTOCOL_START_FRAME), 0) != -1:
                return

    def _check_crc(self, message: bytearray) -> bool:
        buffer = 0

        for byte_idx in range(FIRST_BYTE_FOR_CRC, LAST_BYTE_FOR_CRC):
            buffer += int(message[byte_idx])

        crc = int(message[PROTOCOL_CRC_BYTE])
        calculated_crc = buffer & 0xFF

        return calculated_crc == crc

    def _parse_message(self, message: bytearray) -> []:
        data = []

        high_bytes = range(PROTOCOL_DATA_1_HIGH_BYTE, PROTOCOL_DATA_13_HIGH_BYTE, 2)

        for idx, byte_idx in enumerate(high_bytes):
            value = message[byte_idx] * 16 + message[byte_idx + 1]
            data.append({"type": protocol[idx], "value": value, "unit": units[idx]})

        return data

    def sleep(self):
        if not self.serial.is_open:
            self.serial.open()

        self._send_command(COMMAND_SLEEP)

        self.serial.close()

    def wake(self):
        if not self.serial.is_open:
            self.serial.open()

        self._send_command(COMMAND_WAKE)

        self.serial.close()


    def set_mode(self, mode: int):

        if not self.serial.is_open:
            self.serial.open()

        self._mode = mode
        if mode == self.ACTIVE:
            self._send_command(COMMAND_MODE_ACTIVE)
        elif mode == self.PASSIVE:
            self._send_command(COMMAND_MODE_PASIVE)
        else:
            pass

        # TODO Check ack
        self.serial.read(8)

        self.serial.close()


    def _generate_crc_for_command(self, command: bytes) -> bytes:
        buffer = 0
        for byte in command:
            buffer += int(byte)
        return buffer.to_bytes(2, "big")

    def _send_command(self, command: bytes):

        buffer_cmd = COMMAND_START
        buffer_cmd += command

        crc = self._generate_crc_for_command(buffer_cmd)
        buffer_cmd += crc

        self.serial.write(buffer_cmd)

