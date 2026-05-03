import json
from pathlib import Path

from motoforge.config import (
    BuildOptions,
    lod_path_for,
    manifest_path_for,
    preview_path_for,
    validate_options,
    load_build_options,
)
from motoforge.presets import PRESETS, get_preset, hex_to_rgba
from motoforge.bike_builder import _apply_seed_variation, _lod_detail_plan


def test_presets_exist():
    assert "cafe_racer" in PRESETS
    assert "dirt_bike" in PRESETS
    assert "cyber_scrambler" in PRESETS
    assert "sport_bike" in PRESETS
    assert "streetfighter" in PRESETS


def test_get_preset():
    preset = get_preset("sport_bike")
    assert preset.wheelbase > 2.0
    assert preset.wheel_radius > 0.3
    assert preset.fairing_scale > 0.8
    assert preset.default_wheel_detail == "alloy"


def test_streetfighter_preset():
    preset = get_preset("streetfighter")
    assert preset.handlebar_width > get_preset("sport_bike").handlebar_width
    assert preset.tail_lift > 0.1


def test_hex_to_rgba():
    assert hex_to_rgba("#ff0000") == (1.0, 0.0, 0.0, 1.0)
    assert hex_to_rgba("00ff00") == (0.0, 1.0, 0.0, 1.0)


def test_paths_for_output():
    assert preview_path_for("dist/moto.glb") == str(Path("dist/moto_preview.png"))
    assert manifest_path_for("dist/moto.glb") == str(Path("dist/moto_manifest.json"))
    assert lod_path_for("dist/moto.glb", "lod1") == str(Path("dist/moto_lod1.glb"))


def test_options_validate():
    options = BuildOptions(
        preset="sport_bike",
        detail="high",
        style="cyberpunk",
        wheel_detail="alloy",
        collision="detailed",
        seed=42,
        variant_strength=0.35,
    )
    validate_options(options)


def test_config_aliases(tmp_path: Path):
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "preset": "streetfighter",
                "output": "dist/street.glb",
                "wheelDetail": "alloy",
                "variantStrength": 0.5,
                "licensePlate": False,
                "turnSignals": False,
            }
        ),
        encoding="utf-8",
    )
    options = load_build_options(config)
    assert options.preset == "streetfighter"
    assert options.wheel_detail == "alloy"
    assert options.variant_strength == 0.5
    assert options.license_plate is False
    assert options.turn_signals is False


def test_seed_variation_is_deterministic():
    base = get_preset("streetfighter")
    options = BuildOptions(preset="streetfighter", seed=123, variant_strength=0.6)
    a = _apply_seed_variation(base, options)
    b = _apply_seed_variation(base, options)
    assert a == b
    assert a.wheelbase != base.wheelbase


def test_lod_plan():
    assert _lod_detail_plan("high") == [("lod0", "high"), ("lod1", "medium"), ("lod2", "low")]
    assert _lod_detail_plan("medium")[-1] == ("lod2", "low")
