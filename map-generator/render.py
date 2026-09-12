import io
import os

import matplotlib

matplotlib.use("Agg")

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from staticmap import CircleMarker, Line, StaticMap

from gpx import Point

MAP_WIDTH = 1200
MAP_HEIGHT = 630
ELEVATION_WIDTH = 1200
ELEVATION_HEIGHT = 400

TRACK_COLOR = "#c1440e"
START_COLOR = "#2f6b3a"
END_COLOR = "#a3231f"

ATTRIBUTION_TEXT = "© OpenStreetMap contributors"
USER_AGENT = os.environ.get("MAP_GENERATOR_USER_AGENT", "scaiodellamontagna-map-generator/1.0")


def render_map_png(points: list[Point]) -> bytes:
    coordinates = [(lon, lat) for lat, lon, _ in points]

    m = StaticMap(
        MAP_WIDTH,
        MAP_HEIGHT,
        url_template="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
        headers={"User-Agent": USER_AGENT},
    )
    m.add_line(Line(coordinates, TRACK_COLOR, 4))
    m.add_marker(CircleMarker(coordinates[0], START_COLOR, 12))
    m.add_marker(CircleMarker(coordinates[-1], END_COLOR, 12))

    image = m.render()
    _draw_osm_attribution(image)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _draw_osm_attribution(image: Image.Image) -> None:
    # Required by OSM's tile usage policy: unlike an interactive map (which shows this
    # via a built-in control), a static image has no live UI, so the credit must be
    # composited into the pixels themselves.
    draw = ImageDraw.Draw(image, "RGBA")
    font_path = fm.findfont(fm.FontProperties(family="DejaVu Sans", weight="bold"))
    font = ImageFont.truetype(font_path, 13)
    padding = 6

    text_bbox = draw.textbbox((0, 0), ATTRIBUTION_TEXT, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    x1 = image.width - text_w - padding * 2
    y1 = image.height - text_h - padding * 2
    draw.rectangle([x1, y1, image.width, image.height], fill=(255, 255, 255, 170))
    draw.text((x1 + padding, y1 + padding - text_bbox[1]), ATTRIBUTION_TEXT, font=font, fill=(20, 20, 20, 255))


def _smooth(values: list[float], window: int) -> list[float]:
    if window <= 1:
        return values
    half = window // 2
    return [
        sum(values[max(0, i - half) : min(len(values), i + half + 1)])
        / len(values[max(0, i - half) : min(len(values), i + half + 1)])
        for i in range(len(values))
    ]


def render_elevation_png(distances_km: list[float], points: list[Point]) -> bytes:
    elevations = [ele for _, _, ele in points]
    window = max(3, len(elevations) // 50)
    smoothed = _smooth(elevations, window)

    ele_min, ele_max = min(smoothed), max(smoothed)
    margin = max((ele_max - ele_min) * 0.15, 10)
    baseline = ele_min - margin

    fig, ax = plt.subplots(figsize=(ELEVATION_WIDTH / 100, ELEVATION_HEIGHT / 100), dpi=100)
    ax.fill_between(distances_km, smoothed, baseline, color=TRACK_COLOR, alpha=0.15)
    ax.plot(distances_km, smoothed, color=TRACK_COLOR, linewidth=2)
    ax.set_ylim(baseline, ele_max + margin)
    ax.set_xlabel("Distanza (km)")
    ax.set_ylabel("Quota (m)")
    ax.grid(True, alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="PNG")
    plt.close(fig)
    return buffer.getvalue()
