import json
import os
import copy

import customtkinter
from pathlib import Path

source_file = Path(customtkinter.__file__).parent / "assets" / "themes" / "blue.json"

with open(source_file, 'r') as f:
    base_theme = json.load(f)

rainbow = {
    "red": {"main": ["#D03B3B", "#A51F1F"], "hover": ["#9F3636", "#701414"], "om_hover": ["#7D2727", "#4F2020"]},
    "orange": {"main": ["#D0823B", "#A55C1F"], "hover": ["#9F6236", "#703C14"], "om_hover": ["#7D4927", "#4F3020"]},
    "yellow": {"main": ["#D0C73B", "#A59C1F"], "hover": ["#9F9636", "#706D14"], "om_hover": ["#7D7527", "#4F4B20"]},
    "green": {"main": ["#3BD050", "#1FA532"], "hover": ["#369F46", "#147023"], "om_hover": ["#277D36", "#204F29"]},
    "blue": {"main": ["#3B8ED0", "#1F6AA5"], "hover": ["#36719F", "#144870"], "om_hover": ["#27577D", "#203A4F"]},
    "indigo": {"main": ["#4F3BD0", "#311FA5"], "hover": ["#44369F", "#221470"], "om_hover": ["#33277D", "#26204F"]},
    "violet": {"main": ["#9E3BD0", "#781FA5"], "hover": ["#7B369F", "#521470"], "om_hover": ["#62277D", "#40204F"]},
    "pink": {"main": ["#D03B9E", "#A51F78"], "hover": ["#9F367B", "#701452"], "om_hover": ["#7D2762", "#4F2040"]}
}

def replace_colors(obj, color_map):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and v[0].startswith('#'):
                if v == ["#3B8ED0", "#1F6AA5"]:
                    obj[k] = color_map["main"]
                elif v == ["#36719F", "#144870"]:
                    obj[k] = color_map["hover"]
                elif v == ["#27577D", "#203A4F"]:
                    obj[k] = color_map["om_hover"]
            else:
                replace_colors(v, color_map)

os.makedirs("themes", exist_ok=True)

for name, color_map in rainbow.items():
    theme = copy.deepcopy(base_theme)
    replace_colors(theme, color_map)
    with open(f"themes/{name}.json", "w") as f:
        json.dump(theme, f, indent=2)

print("Generated rainbow themes!")
