from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DETAIL_LEVELS = ("low", "medium", "high")
STYLE_NAMES = ("realistic_lowpoly", "stylized", "cyberpunk", "cartoon")
SILHOUETTES = ("cafe", "scrambler", "sporty", "dirt", "chopper", "streetfighter")
WHEEL_DETAILS = ("none", "spokes", "alloy")
COLLISION_MODES = ("none", "simple", "detailed")


@dataclass
class BuildOptions:
    preset: str = "cafe_racer"
    output: str = "dist/moto_cafe_racer.glb"
    save_blend: str | None = None
    preview: str | None = None
    manifest: str | None = None
    detail: str = "medium"
    style: str = "realistic_lowpoly"
    silhouette: str | None = None
    wheel_detail: str | None = None
    chain: bool = True
    brake_disc: bool = True
    mirrors: bool = True
    turn_signals: bool = True
    license_plate: bool = True
    collision: str = "simple"
    lods: bool = False
    seed: int | None = None
    variant_strength: float = 0.0
    primary_color: str | None = None
    accent_color: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _snake_keys(data: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "saveBlend": "save_blend",
        "wheelDetail": "wheel_detail",
        "primaryColor": "primary_color",
        "accentColor": "accent_color",
        "brakeDisc": "brake_disc",
        "turnSignals": "turn_signals",
        "licensePlate": "license_plate",
        "variantStrength": "variant_strength",
    }
    normalized = {}
    for key, value in data.items():
        normalized[aliases.get(key, key)] = value
    return normalized


def load_build_options(path: str | Path) -> BuildOptions:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("MotoForge config must be a JSON object")
    allowed = set(BuildOptions.__dataclass_fields__)
    data = {key: value for key, value in _snake_keys(raw).items() if key in allowed}
    options = BuildOptions(**data)
    validate_options(options)
    return options


def preview_path_for(output: str | Path) -> str:
    path = Path(output)
    return str(path.with_name(f"{path.stem}_preview.png"))


def manifest_path_for(output: str | Path) -> str:
    path = Path(output)
    return str(path.with_name(f"{path.stem}_manifest.json"))


def lod_path_for(output: str | Path, lod_name: str) -> str:
    path = Path(output)
    return str(path.with_name(f"{path.stem}_{lod_name}{path.suffix or '.glb'}"))


def validate_options(options: BuildOptions) -> None:
    if options.detail not in DETAIL_LEVELS:
        raise ValueError(f"Invalid detail {options.detail!r}; use one of: {', '.join(DETAIL_LEVELS)}")
    if options.style not in STYLE_NAMES:
        raise ValueError(f"Invalid style {options.style!r}; use one of: {', '.join(STYLE_NAMES)}")
    if options.silhouette is not None and options.silhouette not in SILHOUETTES:
        raise ValueError(f"Invalid silhouette {options.silhouette!r}; use one of: {', '.join(SILHOUETTES)}")
    if options.wheel_detail is not None and options.wheel_detail not in WHEEL_DETAILS:
        raise ValueError(f"Invalid wheel_detail {options.wheel_detail!r}; use one of: {', '.join(WHEEL_DETAILS)}")
    if options.collision not in COLLISION_MODES:
        raise ValueError(f"Invalid collision {options.collision!r}; use one of: {', '.join(COLLISION_MODES)}")
    if options.seed is not None and not isinstance(options.seed, int):
        raise ValueError("seed must be an integer when provided")
    if not 0.0 <= float(options.variant_strength) <= 1.0:
        raise ValueError("variant_strength must be between 0.0 and 1.0")
