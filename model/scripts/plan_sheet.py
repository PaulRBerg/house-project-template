"""Shared black-on-white plan sheet: page layout, drawing primitives and the common frame.

Every sheet uses the same page grid, graphic scale and orientation, so the architectural and
structure plans of a floor overlay exactly.
"""

import math
from functools import cache
from itertools import pairwise
from pathlib import Path

import shapely
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import MultiPoint

# Layout units: an 1800-wide drawing field and a schedule column; PIXELS scales them to the
# 4800 × 2800 PNG, about A3 landscape at 290 dpi.
WIDTH, HEIGHT = 2400, 1400
FIELD = 1800
SIDE_LEFT, SIDE_RIGHT = 1880, 2320
PIXELS = 2
SCALE = 88  # Same model-to-page scale on every sheet; page units per metre.
TOP = 285  # Page y of the rear facade; the entrance garden sits at the bottom.
# Dash patterns in page units: alternating drawn and blank lengths.
DASHED = (5, 4)
DASH_DOT = (16, 4, 2, 4)


def hull(entry):
    return MultiPoint(entry["points"]).convex_hull


@cache
def load_font(pixel_size, bold=False):
    candidates = (
        ("Arial Bold.ttf" if bold else "Arial.ttf"),
        ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        str(
            Path("/System/Library/Fonts/Supplemental") / ("Arial Bold.ttf" if bold else "Arial.ttf")
        ),
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, pixel_size)
        except OSError:
            continue
    raise RuntimeError("PNG plans require Arial or DejaVu Sans for Romanian labels")


class Sheet:
    """One plan page centred on a floor's wall bounds (x0, y0, x1, y1) in house-local metres."""

    def __init__(self, bounds):
        x0, _, x1, y1 = bounds
        self.bounds = bounds
        # The page is rotated 180° from the local frame so the living rooms face the viewer.
        self.origin = (FIELD / 2 + (x0 + x1) / 2 * SCALE, TOP + y1 * SCALE)
        self.image = Image.new("RGB", (WIDTH * PIXELS, HEIGHT * PIXELS), "white")
        self.draw = ImageDraw.Draw(self.image)

    def pt(self, p):
        return (self.origin[0] - p[0] * SCALE, self.origin[1] - p[1] * SCALE)

    def pixels(self, point):
        return tuple(round(v * PIXELS) for v in point)

    def font(self, size, bold=False):
        return load_font(round(size * PIXELS), bold)

    def text(self, value, x, y, size=16, color="#171717", anchor="middle", weight="400"):
        self.draw.text(
            self.pixels((x, y)),
            value,
            fill=color,
            font=self.font(size, int(weight) >= 500),
            anchor={"start": "ls", "middle": "ms", "end": "rs", "center": "mm"}[anchor],
        )

    def text_width(self, value, size, bold=False):
        return self.font(size, bold).getlength(value) / PIXELS

    def rotated_text(self, value, x, y, size, color, angle):
        """Center text at (x, y), turned counter-clockwise by angle degrees."""
        face = self.font(size)
        left, top, right, bottom = face.getbbox(value)
        stamp = Image.new("RGBA", (right - left + 4, bottom - top + 4), (255, 255, 255, 0))
        ImageDraw.Draw(stamp).text((2 - left, 2 - top), value, fill=color, font=face)
        stamp = stamp.rotate(angle, expand=True, resample=Image.BICUBIC)
        x, y = self.pixels((x, y))
        self.image.paste(stamp, (round(x - stamp.width / 2), round(y - stamp.height / 2)), stamp)

    def polyline(self, points, stroke, width, dash=None):
        points = [self.pixels(point) for point in points]
        width = max(1, round(width * PIXELS))
        if not dash:
            self.draw.line(points, fill=stroke, width=width, joint="curve")
            return
        period = sum(dash) * PIXELS
        for a, b in pairwise(points):
            length = math.dist(a, b)
            for base in range(0, math.ceil(length), period):
                offset = base
                for index, part in enumerate(dash):
                    end = min(length, offset + part * PIXELS)
                    if index % 2 == 0 and end > offset:
                        segment = [
                            tuple(a[i] + (b[i] - a[i]) * t / length for i in (0, 1))
                            for t in (offset, end)
                        ]
                        self.draw.line(segment, fill=stroke, width=width)
                    offset += part * PIXELS

    def line(self, a, b, stroke="#111", width=1.6, dash=None):
        self.polyline([self.pt(a), self.pt(b)], stroke, width, dash)

    def shape(self, geometry, fill, stroke=None, width=1, dash=None):
        for poly in shapely.get_parts(geometry):
            if fill and not poly.interiors:
                self.draw.polygon(
                    [self.pixels(self.pt(p)) for p in poly.exterior.coords], fill=fill
                )
            elif fill:
                mask = Image.new("L", self.image.size, 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.polygon([self.pixels(self.pt(p)) for p in poly.exterior.coords], fill=255)
                for ring in poly.interiors:
                    mask_draw.polygon([self.pixels(self.pt(p)) for p in ring.coords], fill=0)
                self.image.paste(fill, mask=mask)
            if stroke:
                for ring in [poly.exterior, *poly.interiors]:
                    self.polyline([self.pt(p) for p in ring.coords], stroke, width, dash)

    def tick(self, p, size, stroke, width):
        """Architectural 45° tick closing a dimension line."""
        self.polyline([(p[0] - size, p[1] + size), (p[0] + size, p[1] - size)], stroke, width)

    def dimension(self, a, b, offset, label, size=12, color="#555"):
        """Page-space dimension line from a to b, with the label on its outer side."""
        horizontal = abs(a[1] - b[1]) < 0.5
        self.polyline([a, b], "#777", 1)
        for p in (a, b):
            self.tick(p, 4, "#333", 1.2)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if horizontal:
            self.rotated_text(label, mx, my + offset, size, color, 0)
        else:
            self.rotated_text(label, mx + offset, my, size, color, 90)

    def heading(self, value, y):
        self.text(value, SIDE_LEFT, y, 13, "#111", "start", "600")
        self.polyline([(SIDE_LEFT, y + 9), (SIDE_RIGHT, y + 9)], "#111", 1)

    def table_row(self, columns, values, y, header=False):
        """One schedule row at the column x positions: grey headings, or values led by a bold cell."""
        for x, value in zip(columns, values, strict=True):
            if header:
                self.text(value, x, y, 11, "#666", "start", "600")
            else:
                self.text(value, x, y, 12, "#222", "start", "600" if x == columns[0] else "400")

    def legend_box(self, y, fill, stroke=None):
        """A 34-unit filled legend sample on the row whose text baseline is y."""
        self.draw.rectangle(
            [*self.pixels((SIDE_LEFT, y - 11)), *self.pixels((SIDE_LEFT + 34, y + 1))],
            fill=fill,
            outline=stroke,
            width=PIXELS,
        )

    def legend_lines(self, y, stroke, dash, count=2):
        """A 34-unit legend sample of one or two parallel lines in the given dash."""
        for offset in (-9, -1) if count == 2 else (-5,):
            self.polyline(
                [(SIDE_LEFT, y + offset), (SIDE_LEFT + 34, y + offset)], stroke, 0.9, dash
            )

    def column_swatch(self, y, solid):
        """Legend sample of a column: solid black, or white with a diagonal cross."""
        left, top = SIDE_LEFT + 11, y - 11
        box = [(left, top), (left + 12, top), (left + 12, top + 12), (left, top + 12)]
        self.draw.polygon([self.pixels(p) for p in box], fill="#111" if solid else "white")
        self.polyline([*box, box[0]], "#111", 1.1)
        if not solid:
            self.polyline([box[0], box[2]], "#111", 0.9)
            self.polyline([box[1], box[3]], "#111", 0.9)

    def frame(self, title, kicker, elevation_m, notes, north_local, project_name):
        """Title block, graphic scale, footer notes and, with a known bearing, the compass."""
        text = self.text
        self.polyline([(FIELD + 40, 60), (FIELD + 40, HEIGHT - 50)], "#d8d8d8", 1)
        text(project_name.upper(), 100, 78, 17, "#666", "start", "600")
        text(title, 100, 132, 40, anchor="start", weight="500")
        text(kicker, SIDE_RIGHT, 86, 14, "#666", "end")
        elevation = f"+{elevation_m:.2f} m" if elevation_m else "±0.00 m"
        text(elevation, SIDE_RIGHT, 118, 19, anchor="end")
        # A graphic scale remains valid in PNG, on zoom and after arbitrary printing.
        bx, by = 110, 1262
        for i in range(5):
            self.draw.rectangle(
                [self.pixels((bx + i * SCALE, by)), self.pixels((bx + (i + 1) * SCALE, by + 9))],
                fill="#111" if i % 2 == 0 else "white",
                outline="#111",
                width=PIXELS,
            )
            text(str(i), bx + i * SCALE, by - 10, 13, anchor="start")
        text("5 m", bx + 5 * SCALE, by - 10, 13, anchor="start")
        for index, note in enumerate(notes):
            text(note, 110, 1310 + 26 * index, 14, "#666", "start")

        # Compass rose from the cadastral grid north; without a recorded bearing there is none.
        if north_local is None:
            return
        cx, cy, radius = FIELD - 330, 1262, 44
        self.draw.ellipse(
            [*self.pixels((cx - radius, cy - radius)), *self.pixels((cx + radius, cy + radius))],
            outline="#999",
            width=PIXELS,
        )
        north = (-north_local[0], -north_local[1])  # Local directions flip with the page rotation.
        for label, (dx, dy) in {
            "N": north,
            "E": (-north[1], north[0]),
            "S": (-north[0], -north[1]),
            "V": (north[1], -north[0]),
        }.items():
            self.polyline([(cx, cy), (cx + dx * radius, cy + dy * radius)], "#999", 1)
            self.rotated_text(
                label,
                cx + dx * (radius + 14),
                cy + dy * (radius + 14),
                15 if label == "N" else 12,
                "#111" if label == "N" else "#666",
                0,
            )
        nx, ny = north
        tip = (cx + nx * radius, cy + ny * radius)
        side_a = (cx - ny * 9, cy + nx * 9)
        side_b = (cx + ny * 9, cy - nx * 9)
        self.draw.polygon([self.pixels(p) for p in (tip, side_a, (cx, cy))], fill="#111")
        self.draw.polygon(
            [self.pixels(p) for p in (tip, (cx, cy), side_b)], fill="white", outline="#111"
        )
        text("Nord aproximativ, după extrasul", cx + 90, cy - 4, 12, "#666", "start")
        text("cadastral Stereo 70", cx + 90, cy + 14, 12, "#666", "start")
