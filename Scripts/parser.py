""" - """
# pylint: disable=line-too-long, disable=global-statement, disable=global-variable-not-assigned
import sys
import json
import base64
import socket
from paho.mqtt import client as pahoClient
from paho.mqtt import publish as pahoPublisher
from arf8123aa import parse_message as arf8123aa_parse
from em320th import parse_message as em320th_parse

active_ip: str = ""

def ping_url(ip:str):
    """ - """
    sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sk.settimeout(5)
    try:
        sk.connect((ip, 1883))
        return True
    except socket.timeout:
        return False

def find_server_or_exit(ips):
    """ finds the current mqtt active server, ends the program if none is found """
    for inx in range(0,2):
        if ping_url(ips[inx]):
            return ips[inx]
    sys.exit("No active ip")

def message_action(_, __, msg):
    """ - """
    global active_ip
    if not msg.topic.endswith("up"):
        return
    data = json.loads(msg.payload.decode('utf-8'))
    frame = base64.b64decode(data["data"])
    if data['deveui'] == '00-18-b2-00-00-02-0f-23':
        result = arf8123aa_parse(frame)
    elif data['deveui'] == '24-e1-24-78-5d-12-43-02':
        result = em320th_parse(frame)
    else:
        return
    if result is None:
        return
    result['deveui'] = data["deveui"]
    pahoPublisher.single(f"telegraf/{data['deveui']}", json.dumps(result), hostname=active_ip)

def connect_action(client, _, __, ___):
    """ - """
    client.subscribe("lora/#")

def main():
    """ - """
    global active_ip
    ips = ['192.168.2.217', '192.168.2.193']
    active_ip = mqtt_ip = find_server_or_exit(ips)
    mqtt_client = pahoClient.Client()
    # --- Main Execution Block ---
    mqtt_client.on_connect = connect_action
    mqtt_client.on_message = message_action
    mqtt_client.connect(mqtt_ip, 1883, 60)
    try:
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        mqtt_client.disconnect()
        print("Exiting.")

main()
