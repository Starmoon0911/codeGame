import json
from vpython import box, vector, scene

GRID_RANGE = range(-3, 4)

def load_colors(path="colors.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {int(k): tuple(v) for k, v in data.items()}

def rgb_to_vec(rgb):
    return vector(rgb[0]/255, rgb[1]/255, rgb[2]/255)

class GameEngine:
    def __init__(self):
        scene.width = 600
        scene.height = 600
        scene.background = vector(1, 1, 1)
        self.colors = load_colors()
        self.blocks = []

    def clear(self):
        for b in self.blocks:
            b.visible = False
        self.blocks = []

    def draw(self, rule_func):
        self.clear()
        result = {}
        for x in GRID_RANGE:
            for y in GRID_RANGE:
                for z in GRID_RANGE:
                    try:
                        cid = rule_func(x, y, z)
                    except Exception:
                        cid = 0
                    if cid not in self.colors or cid == 0:
                        continue
                    rgb = self.colors[cid]
                    b = box(pos=vector(x, y, z), size=vector(0.9,0.9,0.9),
                            color=rgb_to_vec(rgb))
                    self.blocks.append(b)
                    result[(x, y, z)] = cid
        return result

    def check_level(self, rule_func, level_path):
        player_result = self.draw(rule_func)
        with open(level_path, "r", encoding="utf-8") as f:
            level = json.load(f)
        target_blocks = {(tuple(b["pos"])): b["color"] for b in level["blocks"]}
        return player_result == target_blocks
