""" - """
# pylint: disable=line-too-long
import pygeohash as pgh
from utils import present, inside_array, complement_two, merge_digits  # type: ignore

def get_coordinate(data: bytes, offset: int, indexes: list[int], direction: dict):
    """ - """
    digits : list[int] = []
    for index in range(0, 4):
        digits.append(int(data[offset+index] >> 4))
        digits.append(int(data[offset+index] & 0xF))
    min_decimal = merge_digits(digits, indexes[4:6]) / pow(10, indexes[5]-indexes[4]+1)
    numbers = [merge_digits(digits, indexes[0:2]), merge_digits(digits, indexes[2:4]), min_decimal, int(digits[7] & 1)]
    return {
        'dms_coord': f"{numbers[0]}º {numbers[1]}' {f"{(numbers[2] * 60):0.2f}"} {direction[numbers[3]]}", 
        'degree_coord': (-1 if numbers[3] else 1) * (float(numbers[0]) + ((float(numbers[1]) + float(numbers[2]))/60)) } #Converts DDD MM SS.SS to decimal degree

def parse_message(frame:bytes):
    """ - """
    result = {}
    status_byte_flag = frame[0]
    current_byte = 1

    result['button_trigger'] = bool(present(status_byte_flag, 5)) # button_trigger
    result['accel_trigger'] = bool(present(status_byte_flag, 6)) # accel_trigger

    if present(status_byte_flag, 7) and inside_array(frame, current_byte, 1):  # tempeture
        result['tempeture'] = complement_two(int(frame[current_byte]), 8)
        # temperature (1 bit) exists and has been read, move head 1 bit
        current_byte += 1

    if present(status_byte_flag, 4) and inside_array(frame, current_byte, 9):  # gps
        latitude = get_coordinate(frame, current_byte, [0, 1, 2, 3, 4, 6], {1: "S", 0: "N"}) #, result)
        longitude = get_coordinate(frame, current_byte + 4, [0, 2, 3, 4, 5, 6], {1: "W", 0: "E"}) #, result)
        result["geohash"] = pgh.encode(latitude = latitude["degree_coord"], longitude = longitude["degree_coord"])
        result['strength'] = int(frame[current_byte + 8] >> 4)
        result['satellites'] = frame[current_byte + 8] & 0xF
        result['latitude'] = latitude["dms_coord"]
        result['longitude'] = longitude["dms_coord"]
        # gps data (4bit for longitud, 4bit for latitud, 1bit for strength) exists and has been read, move head 9 bits
        current_byte += 9

    if present(status_byte_flag, 3) and inside_array(frame, current_byte, 1):  # upload link
        result['uplinks'] = int(frame[current_byte])
        # upload link counter (1 bit) exists and has been read, move head 1 bits
        current_byte += 1

    if present(status_byte_flag, 2) and inside_array(frame, current_byte, 1):  # download link
        result['dwlinks'] = int(frame[current_byte])
        # download link counter (1 bit) exists and has been read, move head 1 bits
        current_byte += 1

    if present(status_byte_flag, 1) and inside_array(frame, current_byte, 2):  # battery level
        result['battery'] = int.from_bytes(
            bytes([frame[current_byte], frame[current_byte + 1]]))
        # battery (2 bit) exists and has been read, move head 2 bits
        current_byte += 2

    if present(status_byte_flag, 0) and inside_array(frame, current_byte, 2):  # RSSI and SNR
        result['rssi'] = -int(frame[current_byte])
        result['snr'] = complement_two(int(frame[current_byte + 1]), 8)

    return result
