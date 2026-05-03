from __future__ import annotations

from typing import Tuple

Color = Tuple[float, float, float, float]


def _tint(color: Color, factor: float) -> Color:
    return (min(color[0] * factor, 1.0), min(color[1] * factor, 1.0), min(color[2] * factor, 1.0), color[3])


def make_material(name: str, color: Color, roughness: float = 0.55, metallic: float = 0.0, alpha: float | None = None):
    """Create a simple Principled BSDF material in Blender."""
    import bpy

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    if alpha is not None and alpha < 1.0:
        mat.blend_method = "BLEND"
        mat.use_screen_refraction = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        base = color if alpha is None else (color[0], color[1], color[2], alpha)
        bsdf.inputs["Base Color"].default_value = base
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if "Alpha" in bsdf.inputs and alpha is not None:
            bsdf.inputs["Alpha"].default_value = alpha
    return mat


def build_materials(preset, style: str = "realistic_lowpoly"):
    """Material palette used by the generator."""
    body = preset.body_color
    accent = preset.accent_color
    if style == "cyberpunk":
        body = _tint(body, 1.12)
        accent = _tint(accent, 1.35)
    elif style == "cartoon":
        body = _tint(body, 1.18)

    return {
        "body": make_material("MF_body_paint", body, roughness=0.38, metallic=0.08),
        "accent": make_material("MF_accent", accent, roughness=0.50, metallic=0.02),
        "metal": make_material("MF_brushed_metal", preset.metal_color, roughness=0.36, metallic=0.65),
        "dark_metal": make_material("MF_dark_metal", (0.08, 0.08, 0.085, 1.0), roughness=0.45, metallic=0.75),
        "rubber": make_material("MF_soft_rubber", preset.tire_color, roughness=0.82, metallic=0.0),
        "rubber_edge": make_material("MF_tread_edge_rubber", (0.018, 0.018, 0.020, 1.0), roughness=0.90, metallic=0.0),
        "leather": make_material("MF_dark_leather", preset.leather_color, roughness=0.68, metallic=0.0),
        "glass": make_material("MF_warm_headlight_glass", (1.0, 0.82, 0.36, 1.0), roughness=0.18, metallic=0.0),
        "smoked_glass": make_material("MF_smoked_windscreen", (0.06, 0.09, 0.11, 1.0), roughness=0.12, metallic=0.0, alpha=0.55),
        "red_light": make_material("MF_rear_lamp_red", (1.0, 0.04, 0.02, 1.0), roughness=0.22, metallic=0.0),
        "amber_light": make_material("MF_amber_turn_signal", (1.0, 0.48, 0.06, 1.0), roughness=0.20, metallic=0.0),
        "white_plate": make_material("MF_license_plate_white", (0.92, 0.92, 0.86, 1.0), roughness=0.44, metallic=0.0),
        "decal": make_material("MF_graphic_decal", (0.98, 0.98, 0.96, 1.0), roughness=0.30, metallic=0.0),
        "collision": make_material("MF_collision_proxy_transparent", (0.1, 0.45, 1.0, 1.0), roughness=0.35, metallic=0.0, alpha=0.22),
    }
