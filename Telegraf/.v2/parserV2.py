# pylint: disable=line-too-long

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json
import base64
import datetime
import os


class Status:
    signal = 0
    battery = 1
    downlink = 2
    uplink = 3
    gps = 4
    button_trigger = 5
    accel_trigger = 6
    temp = 7


class Payload:
    temp = 1
    gps = 2  # includes: latitude, longitude and gps strength
    ulink = 3  # uplink counter
    dlink = 4  # downloadlink counter
    battery = 5
    signal = 6  # rssi and snr information


class Result:
    pass


QUALITY = {1: "Bad", 2: "Average", 3: "Good"}

client = mqtt.Client()


def not_present(position: int, status: int):
    """returns [true], if the bit located in the given [position] inside [status] is 0"""
    return not (status >> position) & 1


def out_of_array(array: bytes, start: int, size: int):
    """returns [true], if reading [size] bits at position [start] for the given [array] will cause overflow"""
    return start + size > len(array)


def complement_two(val: int, length: int):
    """compute the 2's complement of int value val"""
    if (val & (1 << (length - 1))) != 0:
        val = val - (1 << length)
    return val


# --- NEW HELPER FUNCTIONS FOR DECIMAL GPS CONVERSION ---
def bcd_byte_to_int(bcd_byte):
    """Converts a single byte representing two BCD digits to an integer."""
    high_nibble = bcd_byte >> 4
    low_nibble = bcd_byte & 0x0F
    return (high_nibble * 10) + low_nibble


def bcd_to_decimal_degrees(degrees, minutes, seconds_hundreds):
    """Converts DDD MM SS.SS format to a decimal degree."""
    decimal_minutes = minutes + (seconds_hundreds / 10000)
    return float(degrees) + (decimal_minutes / 60.0)


# --- TelegrafProcessingScript LOGIC ---

status = Status()
pcodes = Payload()


def on_message(_, __, msg):
    if (not msg.topic.endswith("up")):
        return

    try:
        data = json.loads(msg.payload.decode('utf-8'))
        payload = base64.b64decode(data["data"])
        status_bit = payload[0]
        current_byte_offset = 1
        
        # Initialize result object with default values to ensure a consistent JSON structure
        result = Result()
        result.topic = msg.topic
        result.temperature = None
        result.accel_trigger = "false"
        result.button_trigger = "false"
        result.latitude = None
        result.longitude = None
        result.gps_quality = None
        result.satellites = None
        result.uplinks = None
        result.dwlinks = None
        result.battery = None
        result.rssi = None
        result.snr = None

        # --- Dynamic Parsing based on Flags ---
        if not not_present(status.temp, status_bit) and not out_of_array(payload, current_byte_offset, 1):
            result.temperature = complement_two(int(payload[current_byte_offset]), 8)
            current_byte_offset += 1
        
        if not not_present(status.accel_trigger, status_bit):
            result.accel_trigger = "true"
        
        if not not_present(status.button_trigger, status_bit):
            result.button_trigger = "true"

        if not not_present(status.gps, status_bit) and not out_of_array(payload, current_byte_offset, 9):
            # GPS data is 9 bytes
            gps_payload = payload[current_byte_offset: current_byte_offset + 9]
            
            # Latitude Parsing (first 4 bytes)
            lat_deg = bcd_byte_to_int(gps_payload[0])
            lat_min = bcd_byte_to_int(gps_payload[1])
            lat_seconds_hundreds = (bcd_byte_to_int(gps_payload[2]) * 100) + (gps_payload[3] >> 4)
            lat_orientation = gps_payload[3] & 0x0F
            lat_decimal = bcd_to_decimal_degrees(lat_deg, lat_min, lat_seconds_hundreds)
            if lat_orientation & 0b0001:  # Check the LSB for South
                lat_decimal *= -1
            
            # Longitude Parsing (next 4 bytes)
            lon_deg = bcd_byte_to_int(gps_payload[4]) * 10 + bcd_byte_to_int(gps_payload[5] >> 4)
            lon_min = bcd_byte_to_int(gps_payload[5] & 0x0F) * 10 + bcd_byte_to_int(gps_payload[6] >> 4)
            lon_seconds_hundreds = bcd_byte_to_int(gps_payload[6] & 0x0F) * 100 + bcd_byte_to_int(gps_payload[7])
            lon_orientation = gps_payload[7] & 0x0F
            lon_decimal = bcd_to_decimal_degrees(lon_deg, lon_min, lon_seconds_hundreds)
            if lon_orientation & 0b0001:  # Check the LSB for West
                lon_decimal *= -1
            
            # GPS Quality and Satellites (last byte)
            gps_quality = gps_payload[8] >> 4
            gps_satellites = gps_payload[8] & 0x0F

            result.latitude = lat_decimal
            result.longitude = lon_decimal
            result.gps_quality = QUALITY.get(gps_quality, f"Unknown ({gps_quality})")
            result.satellites = gps_satellites
            current_byte_offset += 9

        if not not_present(status.uplink, status_bit) and not out_of_array(payload, current_byte_offset, 1):
            result.uplinks = int(payload[current_byte_offset])
            current_byte_offset += 1

        if not not_present(status.downlink, status_bit) and not out_of_array(payload, current_byte_offset, 1):
            result.dwlinks = int(payload[current_byte_offset])
            current_byte_offset += 1

        if not not_present(status.battery, status_bit) and not out_of_array(payload, current_byte_offset, 2):
            result.battery = int.from_bytes(bytes([payload[current_byte_offset], payload[current_byte_offset + 1]]), 'big')
            current_byte_offset += 2
        
        if not not_present(status.signal, status_bit) and not out_of_array(payload, current_byte_offset, 2):
            result.rssi = -int(payload[current_byte_offset])
            result.snr = complement_two(int(payload[current_byte_offset + 1]), 8)
            current_byte_offset += 2

        # Publish the final JSON object with all fields
        publish.single("telegraf", json.dumps(vars(result)), hostname="192.168.2.193")
    
    except Exception as e:
        print(f"Error processing message: {e}")
        # Log the error, but do not stop the script

def on_connect(_, __, ___, rc):
    if rc == 0:
        print("Telegraf Processing Script Connected to MQTT Broker!")
        client.subscribe("lora/#")
    else:
        print(f"Telegraf Processing Script Failed to connect, return code {rc}")

# --- Main Execution Block ---
client.on_connect = on_connect
client.on_message = on_message
client.connect("192.168.2.193", 1883, 60)
try:
    client.loop_forever()
except KeyboardInterrupt:
    client.disconnect()
    print("Exiting.")