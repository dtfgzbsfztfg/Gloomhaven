"""
아주 단순한 사각 그리드 맵. 글룸헤이븐 실제 타일은 육각형이지만,
텍스트/좌표 기반 봇 운용에는 사각 그리드가 다루기 쉬워 이렇게 단순화했다.
"""
from dataclasses import dataclass, field
from PIL import Image, ImageDraw, ImageFont

CELL_SIZE = 56
MARGIN = 30

COLOR_BG = (28, 24, 20)
COLOR_GRID = (70, 62, 52)
COLOR_OBSTACLE = (90, 40, 40)
COLOR_CHAR = (70, 140, 220)
COLOR_MONSTER = (200, 70, 70)
COLOR_MONSTER_ELITE = (150, 30, 140)
COLOR_TEXT = (240, 240, 235)


@dataclass
class GridMap:
    cols: int
    rows: int
    positions: dict = field(default_factory=dict)  # name -> (x, y)
    kinds: dict = field(default_factory=dict)  # name -> "character" | "monster" | "monster_elite"
    obstacles: set = field(default_factory=set)  # {(x, y), ...}

    def place(self, name: str, x: int, y: int, kind: str = "character"):
        x = max(0, min(self.cols - 1, x))
        y = max(0, min(self.rows - 1, y))
        self.positions[name] = (x, y)
        self.kinds[name] = kind

    def remove(self, name: str):
        self.positions.pop(name, None)
        self.kinds.pop(name, None)

    def toggle_obstacle(self, x: int, y: int) -> bool:
        key = (x, y)
        if key in self.obstacles:
            self.obstacles.discard(key)
            return False
        self.obstacles.add(key)
        return True

    def render(self, path: str):
        w = MARGIN * 2 + self.cols * CELL_SIZE
        h = MARGIN * 2 + self.rows * CELL_SIZE
        img = Image.new("RGB", (w, h), COLOR_BG)
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except Exception:
            font = ImageFont.load_default()
            font_small = font

        for gx in range(self.cols):
            for gy in range(self.rows):
                x0 = MARGIN + gx * CELL_SIZE
                y0 = MARGIN + gy * CELL_SIZE
                x1, y1 = x0 + CELL_SIZE, y0 + CELL_SIZE
                fill = COLOR_OBSTACLE if (gx, gy) in self.obstacles else None
                draw.rectangle([x0, y0, x1, y1], outline=COLOR_GRID, width=1, fill=fill)

        for gx in range(self.cols):
            draw.text((MARGIN + gx * CELL_SIZE + CELL_SIZE // 2 - 4, 6), str(gx), fill=COLOR_TEXT, font=font_small)
        for gy in range(self.rows):
            draw.text((6, MARGIN + gy * CELL_SIZE + CELL_SIZE // 2 - 6), str(gy), fill=COLOR_TEXT, font=font_small)

        for name, (gx, gy) in self.positions.items():
            cx = MARGIN + gx * CELL_SIZE + CELL_SIZE // 2
            cy = MARGIN + gy * CELL_SIZE + CELL_SIZE // 2
            kind = self.kinds.get(name, "character")
            color = {
                "character": COLOR_CHAR,
                "monster": COLOR_MONSTER,
                "monster_elite": COLOR_MONSTER_ELITE,
            }.get(kind, COLOR_CHAR)
            r = CELL_SIZE // 2 - 6
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color, outline=(0, 0, 0))
            label = name[:2]
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((cx - tw / 2, cy - th / 2 - 2), label, fill=(255, 255, 255), font=font)

        img.save(path)
        return path
