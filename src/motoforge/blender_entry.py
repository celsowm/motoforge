from __future__ import annotations

import argparse
import sys
from pathlib import Path

# When Blender runs this file directly, make sure the package root is importable.
SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from motoforge import __version__
from motoforge.bike_builder import build_asset_set_from_options
from motoforge.config import (
    BuildOptions,
    COLLISION_MODES,
    DETAIL_LEVELS,
    SILHOUETTES,
    STYLE_NAMES,
    WHEEL_DETAILS,
    load_build_options,
    validate_options,
)
from motoforge.presets import PRESETS


def _argv_after_double_dash() -> list[str]:
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1 :]
    return []


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Generate a procedural motorcycle GLB with Blender.")
    parser.add_argument("--config", default=None, help="JSON config file. CLI flags override values from the file.")
    parser.add_argument("--preset", default=None, choices=sorted(PRESETS), help="Bike style preset.")
    parser.add_argument("--output", default=None, help="Output .glb path.")
    parser.add_argument("--save-blend", default=None, help="Optional .blend path for debugging/refinement.")
    parser.add_argument("--preview", default=None, help="Preview .png path. Use empty string to disable.")
    parser.add_argument("--manifest", default=None, help="Manifest .json path. Use empty string to disable.")
    parser.add_argument("--detail", default=None, choices=DETAIL_LEVELS, help="Geometry detail level.")
    parser.add_argument("--style", default=None, choices=STYLE_NAMES, help="Visual style.")
    parser.add_argument("--silhouette", default=None, choices=SILHOUETTES, help="Optional silhouette bias.")
    parser.add_argument("--wheel-detail", default=None, choices=WHEEL_DETAILS, help="Wheel style.")
    parser.add_argument("--no-chain", action="store_true", help="Disable chain/belt details.")
    parser.add_argument("--no-brake-disc", action="store_true", help="Disable brake discs/calipers.")
    parser.add_argument("--no-mirrors", action="store_true", help="Disable mirrors.")
    parser.add_argument("--no-turn-signals", action="store_true", help="Disable turn signals.")
    parser.add_argument("--no-license-plate", action="store_true", help="Disable rear license plate.")
    parser.add_argument("--collision", default=None, choices=COLLISION_MODES, help="Collision proxy mode.")
    parser.add_argument("--lods", action="store_true", help="Export a LOD set next to the main output.")
    parser.add_argument("--seed", type=int, default=None, help="Deterministic variation seed.")
    parser.add_argument("--variant-strength", type=float, default=None, help="0.0-1.0 deterministic proportion variation strength.")
    parser.add_argument("--primary-color", default=None, help="Override body color, e.g. #111111.")
    parser.add_argument("--accent-color", default=None, help="Override accent color, e.g. #ff3b30.")
    parser.add_argument("--version", action="store_true", help="Print version and exit.")
    return parser.parse_args(_argv_after_double_dash() if argv is None else argv)


def options_from_args(args) -> BuildOptions:
    options = load_build_options(args.config) if args.config else BuildOptions()
    for field_name in (
        "preset",
        "output",
        "save_blend",
        "preview",
        "manifest",
        "detail",
        "style",
        "silhouette",
        "wheel_detail",
        "primary_color",
        "accent_color",
        "collision",
        "seed",
        "variant_strength",
    ):
        value = getattr(args, field_name)
        if value is not None:
            setattr(options, field_name, value)
    if args.no_chain:
        options.chain = False
    if args.no_brake_disc:
        options.brake_disc = False
    if args.no_mirrors:
        options.mirrors = False
    if args.no_turn_signals:
        options.turn_signals = False
    if args.no_license_plate:
        options.license_plate = False
    if args.lods:
        options.lods = True
    validate_options(options)
    return options


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.version:
        print(f"MotoForge {__version__}")
        return 0

    options = options_from_args(args)
    outputs = build_asset_set_from_options(options)
    rendered = ", ".join(str(path) for path in outputs)
    print(f"MotoForge {__version__}: exported {rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
