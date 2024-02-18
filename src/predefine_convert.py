"""
Author: Konano
Description: Convert predefine.lark to predefine.json
"""

import json

predefine = {}

for line in open("grammar/predefine.lark", "r").readlines():
    line = line.strip()
    if ": " in line:
        name, value = line.split(": ")
        values = [x[1:-1].replace('\\"', '"') for x in value.split(" | ")]
        if name not in predefine:
            predefine[name] = sorted(values)

json.dump(predefine, open("grammar/predefine.json", "w"), indent=4)
