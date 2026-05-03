from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import __version__
from .config import COLLISION_MODES, DETAIL_LEVELS, SILHOUETTES, STYLE_NAMES, WHEEL_DETAILS, manifest_path_for
from .presets import PRESETS


def parse_generate_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Wrapper that asks Blender to generate a MotoForge GLB asset.")
    parser.add_argument("--blender", default=None, help="Path to Blender executable. Defaults to BLENDER_PATH or 'blender' in PATH.")
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
    parser.add_argument("--collision", default=None, choices=COLLISION_MODES, help="Collision proxy mode.")
    parser.add_argument("--seed", type=int, default=None, help="Deterministic variation seed.")
    parser.add_argument("--variant-strength", type=float, default=None, help="0.0-1.0 deterministic proportion variation strength.")
    parser.add_argument("--lods", action="store_true", help="Export LOD0/LOD1/LOD2 .glb files.")
    parser.add_argument("--no-chain", action="store_true", help="Disable chain/belt details.")
    parser.add_argument("--no-brake-disc", action="store_true", help="Disable brake discs/calipers.")
    parser.add_argument("--no-mirrors", action="store_true", help="Disable mirrors.")
    parser.add_argument("--no-turn-signals", action="store_true", help="Disable turn signals.")
    parser.add_argument("--no-license-plate", action="store_true", help="Disable rear license plate.")
    parser.add_argument("--primary-color", default=None, help="Override body color, e.g. #111111.")
    parser.add_argument("--accent-color", default=None, help="Override accent color, e.g. #ff3b30.")
    parser.add_argument("--version", action="store_true", help="Print version and exit.")
    return parser.parse_args(argv)


def find_blender(explicit_path: str | None) -> str:
    candidate = explicit_path or os.environ.get("BLENDER_PATH") or shutil.which("blender")
    if not candidate:
        raise SystemExit(
            "Blender executable not found. Install Blender, add it to PATH, set BLENDER_PATH, "
            "or pass --blender /path/to/blender."
        )
    return candidate


def _append_optional(args: list[str], flag: str, value: Any):
    if value is not None:
        args.extend([flag, str(value)])


def generate_main(argv: list[str] | None = None) -> int:
    args = parse_generate_args(argv)
    if args.version:
        print(f"MotoForge {__version__}")
        return 0

    blender = find_blender(args.blender)
    entry = Path(__file__).resolve().with_name("blender_entry.py")
    src_root = Path(__file__).resolve().parents[1]

    blender_args = [blender, "--background", "--python", str(entry), "--"]
    _append_optional(blender_args, "--config", args.config)
    _append_optional(blender_args, "--preset", args.preset)
    _append_optional(blender_args, "--output", args.output)
    _append_optional(blender_args, "--save-blend", args.save_blend)
    _append_optional(blender_args, "--preview", args.preview)
    _append_optional(blender_args, "--manifest", args.manifest)
    _append_optional(blender_args, "--detail", args.detail)
    _append_optional(blender_args, "--style", args.style)
    _append_optional(blender_args, "--silhouette", args.silhouette)
    _append_optional(blender_args, "--wheel-detail", args.wheel_detail)
    _append_optional(blender_args, "--collision", args.collision)
    _append_optional(blender_args, "--seed", args.seed)
    _append_optional(blender_args, "--variant-strength", args.variant_strength)
    _append_optional(blender_args, "--primary-color", args.primary_color)
    _append_optional(blender_args, "--accent-color", args.accent_color)
    if args.lods:
        blender_args.append("--lods")
    if args.no_chain:
        blender_args.append("--no-chain")
    if args.no_brake_disc:
        blender_args.append("--no-brake-disc")
    if args.no_mirrors:
        blender_args.append("--no-mirrors")
    if args.no_turn_signals:
        blender_args.append("--no-turn-signals")
    if args.no_license_plate:
        blender_args.append("--no-license-plate")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_root}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    return subprocess.call(blender_args, env=env)


def batch_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run multiple MotoForge jobs from one JSON file.")
    parser.add_argument("config", help="Batch JSON with {'defaults': {...}, 'jobs': [{...}, ...]}.")
    parser.add_argument("--blender", default=None, help="Path to Blender executable.")
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        defaults: dict[str, Any] = {}
        jobs = payload
    else:
        defaults = payload.get("defaults", {})
        jobs = payload.get("jobs", [])
    if not isinstance(jobs, list) or not jobs:
        raise SystemExit("Batch config must contain a non-empty jobs list.")

    blender = find_blender(args.blender)
    rc = 0
    with tempfile.TemporaryDirectory(prefix="motoforge_batch_") as tmp:
        tmp_dir = Path(tmp)
        for index, job in enumerate(jobs, start=1):
            merged = dict(defaults)
            merged.update(job)
            cfg = tmp_dir / f"job_{index:03d}.json"
            cfg.write_text(json.dumps(merged, indent=2), encoding="utf-8")
            print(f"MotoForge batch: job {index}/{len(jobs)} -> {merged.get('output', '<default output>')}")
            rc = generate_main(["--blender", blender, "--config", str(cfg)]) or rc
    return rc


def presets_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List available MotoForge presets.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)
    names = sorted(PRESETS)
    if args.json:
        print(json.dumps({"version": __version__, "presets": names}, indent=2))
    else:
        print("Available presets:")
        for name in names:
            print(f"  - {name}")
    return 0


def validate_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate MotoForge output files without requiring Blender.")
    parser.add_argument("asset", help="Path to the exported .glb file.")
    parser.add_argument("--manifest", default=None, help="Optional manifest path. Defaults to output-stem_manifest.json.")
    args = parser.parse_args(argv)

    asset = Path(args.asset)
    manifest = Path(args.manifest or manifest_path_for(asset))
    errors: list[str] = []
    warnings: list[str] = []

    if not asset.exists():
        errors.append(f"Missing asset: {asset}")
    elif asset.stat().st_size <= 1024:
        warnings.append(f"Asset exists but is very small: {asset.stat().st_size} bytes")

    payload = None
    if not manifest.exists():
        warnings.append(f"Missing manifest: {manifest}")
    else:
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Manifest is not valid JSON: {exc}")

    if payload:
        version = payload.get("motoforge_version")
        if version != __version__:
            warnings.append(f"Manifest version is {version!r}, CLI version is {__version__!r}")
        stats = payload.get("stats", {})
        parts = set(stats.get("parts", []))
        required = {"fuel_tank", "seat", "engine_block", "front_fork", "radiator", "dashboard", "rear_suspension"}
        missing = sorted(required - parts)
        if missing:
            warnings.append(f"Manifest is missing expected v0.0.3 parts: {', '.join(missing)}")
        collision_mode = payload.get("options", {}).get("collision", "simple")
        if collision_mode != "none" and "collision_proxy" not in parts:
            warnings.append("Collision mode is enabled but no collision_proxy parts were found")
        if stats.get("object_count", 0) < 25:
            warnings.append("Object count is low for a detailed motorcycle asset")

    if errors:
        print("MotoForge validation failed:")
        for item in errors:
            print(f"  ERROR: {item}")
        for item in warnings:
            print(f"  WARN:  {item}")
        return 1

    print("MotoForge validation passed.")
    for item in warnings:
        print(f"  WARN: {item}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "validate":
        return validate_main(argv[1:])
    if argv and argv[0] == "batch":
        return batch_main(argv[1:])
    if argv and argv[0] == "presets":
        return presets_main(argv[1:])
    return generate_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
