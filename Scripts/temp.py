""" - """

import base64
import json
from arf8123aa import parse_message as arf8123aa_parse

frame = bytes.fromhex("BE2439430160002549303610000F81")
frame = base64.b64decode("ryIFBQ89Cwg=")
print(frame.hex())
result = arf8123aa_parse(frame)
print(json.dumps(result))
