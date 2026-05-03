from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Tuple

Color = Tuple[float, float, float, float]


def hex_to_rgba(value: str, alpha: float = 1.0) -> Color:
    """Convert '#rrggbb' or 'rrggbb' to Blender-friendly RGBA floats."""
    raw = value.strip().lstrip("#")
    if len(raw) != 6:
        raise ValueError(f"Expected a 6-digit hex color, got {value!r}")
    try:
        r = int(raw[0:2], 16) / 255.0
        g = int(raw[2:4], 16) / 255.0
        b = int(raw[4:6], 16) / 255.0
    except ValueError as exc:
        raise ValueError(f"Invalid hex color {value!r}") from exc
    return (r, g, b, alpha)


@dataclass(frozen=True)
class BikePreset:
    """High-level proportions for a procedural motorcycle asset."""

    name: str
    wheelbase: float = 2.65
    wheel_radius: float = 0.46
    tire_thickness: float = 0.085
    wheel_width: float = 0.18
    frame_tube_radius: float = 0.035
    fork_rake: float = 0.18
    ground_clearance: float = 0.18
    tank_length: float = 0.74
    tank_height: float = 0.25
    tank_width: float = 0.38
    seat_length: float = 0.72
    seat_height: float = 0.12
    handlebar_width: float = 0.72
    fender_width: float = 0.26
    fairing_scale: float = 0.0
    tail_lift: float = 0.0
    default_wheel_detail: str = "spokes"
    body_color: Color = (0.72, 0.08, 0.05, 1.0)
    accent_color: Color = (0.08, 0.09, 0.10, 1.0)
    metal_color: Color = (0.55, 0.53, 0.50, 1.0)
    tire_color: Color = (0.01, 0.01, 0.012, 1.0)
    leather_color: Color = (0.055, 0.035, 0.022, 1.0)

    def with_color_overrides(self, primary: str | None = None, accent: str | None = None) -> "BikePreset":
        changes = {}
        if primary:
            changes["body_color"] = hex_to_rgba(primary)
        if accent:
            changes["accent_color"] = hex_to_rgba(accent)
        return replace(self, **changes) if changes else self


PRESETS: Dict[str, BikePreset] = {
    "cafe_racer": BikePreset(
        name="cafe_racer",
        wheelbase=2.58,
        wheel_radius=0.45,
        tank_length=0.82,
        tank_height=0.24,
        tank_width=0.36,
        seat_length=0.70,
        handlebar_width=0.64,
        default_wheel_detail="spokes",
        body_color=(0.80, 0.12, 0.06, 1.0),
        accent_color=(0.025, 0.027, 0.03, 1.0),
    ),
    "dirt_bike": BikePreset(
        name="dirt_bike",
        wheelbase=2.72,
        wheel_radius=0.50,
        tire_thickness=0.10,
        wheel_width=0.16,
        frame_tube_radius=0.032,
        fork_rake=0.24,
        ground_clearance=0.30,
        tank_length=0.62,
        tank_height=0.22,
        tank_width=0.32,
        seat_length=0.92,
        seat_height=0.10,
        handlebar_width=0.86,
        fender_width=0.22,
        tail_lift=0.08,
        default_wheel_detail="spokes",
        body_color=(0.96, 0.42, 0.04, 1.0),
        accent_color=(0.04, 0.04, 0.045, 1.0),
    ),
    "cyber_scrambler": BikePreset(
        name="cyber_scrambler",
        wheelbase=2.70,
        wheel_radius=0.47,
        tire_thickness=0.095,
        wheel_width=0.21,
        frame_tube_radius=0.04,
        fork_rake=0.20,
        tank_length=0.78,
        tank_height=0.28,
        tank_width=0.42,
        seat_length=0.76,
        handlebar_width=0.80,
        fender_width=0.30,
        fairing_scale=0.35,
        default_wheel_detail="alloy",
        body_color=(0.08, 0.68, 0.92, 1.0),
        accent_color=(0.015, 0.015, 0.02, 1.0),
        metal_color=(0.66, 0.70, 0.74, 1.0),
    ),

    "streetfighter": BikePreset(
        name="streetfighter",
        wheelbase=2.62,
        wheel_radius=0.45,
        tire_thickness=0.082,
        wheel_width=0.23,
        frame_tube_radius=0.036,
        fork_rake=0.16,
        ground_clearance=0.17,
        tank_length=0.80,
        tank_height=0.30,
        tank_width=0.43,
        seat_length=0.62,
        seat_height=0.105,
        handlebar_width=0.74,
        fender_width=0.29,
        fairing_scale=0.45,
        tail_lift=0.13,
        default_wheel_detail="alloy",
        body_color=(0.02, 0.02, 0.025, 1.0),
        accent_color=(0.82, 0.95, 0.18, 1.0),
        metal_color=(0.58, 0.60, 0.62, 1.0),
    ),
    "sport_bike": BikePreset(
        name="sport_bike",
        wheelbase=2.66,
        wheel_radius=0.44,
        tire_thickness=0.078,
        wheel_width=0.22,
        frame_tube_radius=0.032,
        fork_rake=0.14,
        ground_clearance=0.16,
        tank_length=0.86,
        tank_height=0.28,
        tank_width=0.42,
        seat_length=0.66,
        seat_height=0.10,
        handlebar_width=0.58,
        fender_width=0.28,
        fairing_scale=1.0,
        tail_lift=0.12,
        default_wheel_detail="alloy",
        body_color=(0.06, 0.07, 0.08, 1.0),
        accent_color=(1.0, 0.12, 0.07, 1.0),
        metal_color=(0.60, 0.61, 0.62, 1.0),
    ),
}


def get_preset(name: str) -> BikePreset:
    try:
        return PRESETS[name]
    except KeyError as exc:
        available = ", ".join(sorted(PRESETS))
        raise ValueError(f"Unknown preset '{name}'. Available presets: {available}") from exc
