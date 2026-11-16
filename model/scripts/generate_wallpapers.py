"""Generate the project-authored, seamless wallpaper and tile textures in ``assets/interior``.

uv run --project model python model/scripts/generate_wallpapers.py

Where no CC0 wallpaper source fits the brief, these seeded tiles are drawn here: a
delicate sage botanical, a deep green leaf wallpaper and a sober charcoal grasscloth,
plus two mountain murals for a child's room and a vertical sage tile. Output is
deterministic for a given Pillow version.
"""

import math
import random

from PIL import Image, ImageDraw, ImageFilter
from project_paths import ASSETS

OUT = ASSETS / "interior"
SIZE = 1024
SUPER = 2
# 3.2 m horizontal repeat by 2.7 m wall height (32:27), so a square-pixel canvas maps
# onto the wall without stretching the painted mountains.
MURAL_WIDTH = 2048
MURAL_HEIGHT = 1728


def _wrapped(draw_motif, canvas: Image.Image) -> None:
    """Draw a motif at every tile offset so it wraps seamlessly."""
    span = canvas.size[0]
    for dx in (-span, 0, span):
        for dy in (-span, 0, span):
            draw_motif(dx, dy)


def _bent_spine(x, y, length, angle, bend, steps):
    """Centreline curving ``bend × length`` sideways by its tip, as ``steps + 1`` points."""
    points = []
    for step in range(steps + 1):
        t = step / steps
        curve = bend * length * t * t
        points.append(
            (
                x + math.cos(angle) * length * t - math.sin(angle) * curve,
                y + math.sin(angle) * length * t + math.cos(angle) * curve,
            )
        )
    return points


def _leaf_polygon(x, y, length, width, angle, steps=10, bend=0.0):
    left, right = [], []
    for step in range(steps + 1):
        t = step / steps
        half = width / 2 * math.sin(math.pi * t**0.85) ** 0.9
        along = length * t
        curve = bend * length * t * t
        cx = x + math.cos(angle) * along - math.sin(angle) * curve
        cy = y + math.sin(angle) * along + math.cos(angle) * curve
        nx, ny = -math.sin(angle), math.cos(angle)
        left.append((cx + nx * half, cy + ny * half))
        right.append((cx - nx * half, cy - ny * half))
    return left + right[::-1]


def botanical_soft() -> Image.Image:
    rng = random.Random(24)
    size = SIZE * SUPER
    image = Image.new("RGB", (size, size), (234, 227, 214))
    draw = ImageDraw.Draw(image)
    greens = [(166, 172, 148), (143, 150, 124), (182, 184, 164), (126, 134, 112)]
    clay = (196, 160, 140)
    for _ in range(26):
        x0, y0 = rng.uniform(0, size), rng.uniform(0, size)
        angle = rng.uniform(-math.pi, math.pi)
        stem = rng.uniform(0.09, 0.16) * size
        color = rng.choice(greens)
        leaves = [
            (rng.uniform(0.15, 0.95), rng.choice((-1, 1)), rng.uniform(0.35, 0.8))
            for _ in range(rng.randint(6, 10))
        ]
        # Draw offsets once per stem so every wrapped copy of a berry cluster matches.
        berry_offsets = (
            [(rng.uniform(-14, 14) * SUPER, rng.uniform(-14, 14) * SUPER) for _ in range(3)]
            if rng.random() < 0.35
            else []
        )

        def motif(
            dx,
            dy,
            x0=x0,
            y0=y0,
            angle=angle,
            stem=stem,
            color=color,
            leaves=leaves,
            berry_offsets=berry_offsets,
        ):
            points = _bent_spine(x0 + dx, y0 + dy, stem, angle, 0.18, 20)
            draw.line(points, fill=color, width=3 * SUPER)
            for t, side, spread in leaves:
                index = min(int(t * 20), 20)
                px, py = points[index]
                draw.polygon(
                    _leaf_polygon(
                        px, py, stem * 0.26, stem * 0.1, angle + side * spread, bend=0.08 * side
                    ),
                    fill=color,
                )
            bx, by = points[-1]
            r = 5 * SUPER
            for ox, oy in berry_offsets:
                draw.ellipse((bx + ox - r, by + oy - r, bx + ox + r, by + oy + r), fill=clay)

        _wrapped(motif, image)
    return image.resize((SIZE, SIZE), Image.LANCZOS)


def botanical_green() -> Image.Image:
    rng = random.Random(7)
    size = SIZE * SUPER
    image = Image.new("RGB", (size, size), (38, 52, 42))
    draw = ImageDraw.Draw(image)
    tones = [(52, 72, 55), (66, 88, 64), (82, 104, 76), (97, 118, 86), (45, 62, 48)]
    for layer in range(3):
        for _ in range(16 + 6 * layer):
            x0, y0 = rng.uniform(0, size), rng.uniform(0, size)
            angle = rng.uniform(-math.pi, math.pi)
            length = rng.uniform(0.18, 0.34) * size * (1.0 - 0.18 * layer)
            width = length * rng.uniform(0.26, 0.4)
            color = tones[min(layer + rng.randint(0, 2), len(tones) - 1)]
            vein = tuple(min(255, value + 26) for value in color)
            bend = rng.uniform(-0.25, 0.25)

            def motif(
                dx,
                dy,
                x0=x0,
                y0=y0,
                angle=angle,
                length=length,
                width=width,
                color=color,
                vein=vein,
                bend=bend,
            ):
                draw.polygon(
                    _leaf_polygon(x0 + dx, y0 + dy, length, width, angle, steps=16, bend=bend),
                    fill=color,
                )
                spine = _bent_spine(x0 + dx, y0 + dy, length, angle, bend, 16)
                draw.line(spine, fill=vein, width=2 * SUPER)
                for step in range(2, 15, 2):
                    sx, sy = spine[step]
                    for side in (-1, 1):
                        a = angle + side * 1.0
                        reach = width * 0.42 * math.sin(math.pi * step / 16)
                        draw.line(
                            (sx, sy, sx + math.cos(a) * reach, sy + math.sin(a) * reach),
                            fill=vein,
                            width=SUPER,
                        )

            _wrapped(motif, image)
    return image.resize((SIZE, SIZE), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))


def grasscloth() -> Image.Image:
    rng = random.Random(11)
    image = Image.new("RGB", (SIZE, SIZE), (70, 66, 62))
    draw = ImageDraw.Draw(image)
    x = 0.0
    while x < SIZE:
        width = rng.uniform(1.0, 3.5)
        shade = rng.randint(-14, 16)
        base = (74 + shade, 69 + shade, 64 + shade)
        draw.rectangle((x, 0, x + width, SIZE), fill=base)
        for _ in range(rng.randint(0, 3)):
            y = rng.uniform(0, SIZE)
            draw.line(
                (x, y, x + width, y + rng.uniform(-2, 2)), fill=tuple(value + 10 for value in base)
            )
        x += width
    for y in range(0, SIZE, 128):
        draw.line((0, y, SIZE, y), fill=(60, 56, 53), width=1)
    return image.filter(ImageFilter.GaussianBlur(0.4))


def _tiled_ridge_mask(width, height, rng, baseline_y, amplitude, harmonics=3, step=4):
    """A ridge-line mask whose wavy skyline tiles seamlessly across ``width``.

    Each harmonic uses an integer number of periods across the canvas, so the
    sine sum returns to the same value at ``x=0`` and ``x=width``.
    """
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    freqs = rng.sample(range(2, 7), k=harmonics)
    phases = [rng.uniform(0, 2 * math.pi) for _ in freqs]
    weights = [amplitude / (index + 1) ** 1.3 for index in range(harmonics)]
    points = []
    for x in range(0, width + 1, step):
        t = x / width
        y = baseline_y
        for freq, phase, weight in zip(freqs, phases, weights, strict=True):
            y += weight * math.sin(2 * math.pi * freq * t + phase)
        points.append((x, y))
    draw.polygon(points + [(width, height), (0, height)], fill=255)
    return mask, points


def _pine(draw, x, y, height, width, color):
    """A small two-tier pine silhouette with its base at ``(x, y)``."""
    draw.polygon([(x, y - height), (x - width / 2, y), (x + width / 2, y)], fill=color)
    draw.polygon([(x, y - height * 0.6), (x - width * 0.38, y), (x + width * 0.38, y)], fill=color)


def _bird(draw, cx, cy, span, color):
    """A minimal two-stroke bird mark, wings meeting at ``(cx, cy)``."""
    draw.line([(cx - span, cy), (cx - span * 0.5, cy - span * 0.6), (cx, cy)], fill=color, width=2)
    draw.line([(cx, cy), (cx + span * 0.5, cy - span * 0.6), (cx + span, cy)], fill=color, width=2)


def _mountain_mural(seed, sky_top, sky_low, layers, pine_color, bird_color) -> Image.Image:
    """A soft watercolour mountain-range mural, seamless horizontally.

    ``layers`` runs from the farthest, palest ridge to the nearest, most
    saturated one, as ``(color, baseline_frac, amplitude_frac, blur)``.
    """
    rng = random.Random(seed)
    width, height = MURAL_WIDTH, MURAL_HEIGHT
    image = Image.new("RGB", (width, height), sky_top)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = min(y / height / 0.62, 1.0)
        color = tuple(
            round(sky_top[channel] + (sky_low[channel] - sky_top[channel]) * t)
            for channel in range(3)
        )
        draw.line((0, y, width, y), fill=color)

    nearest_points = None
    for color, baseline_frac, amplitude_frac, blur in layers:
        mask, points = _tiled_ridge_mask(
            width, height, rng, height * baseline_frac, height * amplitude_frac
        )
        if blur:
            mask = mask.filter(ImageFilter.GaussianBlur(blur))
        image.paste(Image.new("RGB", (width, height), color), (0, 0), mask)
        nearest_points = points

    draw = ImageDraw.Draw(image)
    for frac in (0.06, 0.19, 0.34, 0.47, 0.63, 0.78, 0.91):
        px = frac * width
        base_y = nearest_points[min(int(px // 4), len(nearest_points) - 1)][1]
        pine_height = rng.uniform(0.018, 0.03) * height
        pine_width = pine_height * 0.55
        for dx in (-width, 0, width):
            _pine(draw, px + dx, base_y + 2, pine_height, pine_width, pine_color)

    for _ in range(2):
        bx = rng.uniform(0.2, 0.8) * width
        by = rng.uniform(0.1, 0.3) * height
        _bird(draw, bx, by, rng.uniform(0.008, 0.012) * width, bird_color)

    return image.filter(ImageFilter.GaussianBlur(1.4))


def mural_mountains_sage() -> Image.Image:
    return _mountain_mural(
        seed=61,
        sky_top=(250, 245, 231),
        sky_low=(222, 224, 205),
        layers=[
            ((198, 206, 190), 0.44, 0.03, 10),
            ((170, 184, 157), 0.50, 0.04, 7),
            ((138, 156, 119), 0.57, 0.045, 4),
            ((96, 112, 80), 0.65, 0.04, 1.5),
        ],
        pine_color=(61, 74, 52),
        bird_color=(90, 84, 70),
    )


def mural_mountains_dusk() -> Image.Image:
    return _mountain_mural(
        seed=62,
        sky_top=(250, 232, 214),
        sky_low=(214, 205, 205),
        layers=[
            ((196, 202, 211), 0.44, 0.03, 10),
            ((162, 175, 190), 0.50, 0.04, 7),
            ((123, 140, 158), 0.57, 0.045, 4),
            ((79, 96, 116), 0.65, 0.04, 1.5),
        ],
        pine_color=(48, 60, 76),
        bird_color=(86, 82, 90),
    )


def tile_vertical_sage() -> Image.Image:
    """Stack-bond 7.5 x 30 cm sage tiles; an 8x2 grid covers a square 60 cm block."""
    rng = random.Random(53)
    cols, rows = 8, 2
    tile_w, tile_h = SIZE // cols, SIZE // rows
    grout = 4
    grout_color = (150, 149, 144)
    base = (163, 174, 147)
    image = Image.new("RGB", (SIZE, SIZE), grout_color)
    draw = ImageDraw.Draw(image)
    for row in range(rows):
        for col in range(cols):
            shift = rng.uniform(-10, 10)
            fill = tuple(max(0, min(255, round(channel + shift))) for channel in base)
            x0, y0 = col * tile_w + grout, row * tile_h + grout
            x1, y1 = (col + 1) * tile_w - grout, (row + 1) * tile_h - grout
            draw.rectangle((x0, y0, x1, y1), fill=fill)
            edge = tuple(max(0, channel - 22) for channel in fill)
            draw.rectangle((x0, y0, x1, y1), outline=edge, width=3)
    return image.filter(ImageFilter.GaussianBlur(0.5))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, build in (
        ("wallpaper_botanical_soft.png", botanical_soft),
        ("wallpaper_botanical_green.png", botanical_green),
        ("wallpaper_grasscloth_charcoal.png", grasscloth),
        ("mural_mountains_sage.png", mural_mountains_sage),
        ("mural_mountains_dusk.png", mural_mountains_dusk),
        ("tile_vertical_sage.png", tile_vertical_sage),
    ):
        build().save(OUT / name, optimize=True)
        print(OUT / name)


if __name__ == "__main__":
    main()
