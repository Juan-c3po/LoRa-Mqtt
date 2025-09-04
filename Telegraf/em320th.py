""" - """
# pylint: disable=line-too-long

def get_value(frame: bytes, start : int, channel : int, ttype: int, vallength: int, signed : bool = False):
    """ - """
    if int(frame[start]) == channel and int(frame[start+1]) == ttype:
        value = int.from_bytes(frame[start + 2:start + 2 + vallength], byteorder='little', signed=signed)
        return { 'found': True, 'value': value }
    return { 'found': False }

def parse_message(frame:bytes):
    """ - """
    current_byte : int = 0
    result={}

    if int(frame[0]) != 0x01:
        return None

    value = get_value(frame, current_byte, 0x1, 0x75, 1)
    if value['found']: #battery level in percentage points
        result['battery'] = value['value']
        current_byte += 3

    value = get_value(frame, current_byte, 0x3, 0x67, 2, True)
    if value['found']: #tempeture in ºC
        result['tempeture'] = float(value['value']) * 0.1
        current_byte += 4

    value = get_value(frame, current_byte, 0x4, 0x68, 1)
    if value['found']: #battery level in percentage points
        result['humidity'] = float(value['value']) * 0.5
        current_byte += 3

    return result
