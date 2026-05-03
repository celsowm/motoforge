from __future__ import annotations

import json
import math
import random
from dataclasses import replace
from pathlib import Path
from typing import Any, List, Tuple

from .config import BuildOptions, lod_path_for, manifest_path_for, preview_path_for, validate_options
from .geometry import (
    add_arc_fender,
    add_beveled_box,
    add_curve_tube,
    add_cylinder_between,
    add_disc_brake_assembly,
    add_ellipsoid,
    add_torus_wheel,
    add_wedge_panel,
    add_y_cylinder,
    move_objects_to_collection,
)
from .materials import build_materials
from .presets import BikePreset, get_preset

Point = Tuple[float, float, float]


DETAIL_PROFILES = {
    "low": {"wheel_segments": 32, "minor_segments": 6, "spokes": 10, "tread_blocks": 14, "curve_bevel": 2, "fender_segments": 14},
    "medium": {"wheel_segments": 44, "minor_segments": 8, "spokes": 16, "tread_blocks": 22, "curve_bevel": 3, "fender_segments": 20},
    "high": {"wheel_segments": 56, "minor_segments": 10, "spokes": 24, "tread_blocks": 32, "curve_bevel": 4, "fender_segments": 28},
}


def _clear_scene():
    import bpy

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for data_block in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.images):
        for item in list(data_block):
            if item.users == 0:
                data_block.remove(item)


def _setup_scene(style: str):
    import bpy

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.unit_settings.system = "METRIC"

    bpy.ops.object.light_add(type="AREA", location=(0.0, -4.5, 5.5))
    key = bpy.context.object
    key.name = "MF_key_area_light"
    key.data.energy = 560 if style in {"cyberpunk", "stylized"} else 450
    key.data.size = 4.0

    bpy.ops.object.light_add(type="POINT", location=(-2.8, 2.2, 2.2))
    rim = bpy.context.object
    rim.name = "MF_small_rim_light"
    rim.data.energy = 95

    bpy.ops.object.camera_add(location=(3.7, -5.0, 2.3), rotation=(math.radians(64), 0, math.radians(38)))
    bpy.context.scene.camera = bpy.context.object

    bpy.ops.mesh.primitive_plane_add(size=5.0, location=(0, 0, -0.005))
    ground = bpy.context.object
    ground.name = "MF_reference_ground_plane"
    return ground


def _tag(obj, part: str, version: str, preset_name: str):
    obj["motoforge_version"] = version
    obj["motoforge_preset"] = preset_name
    obj["motoforge_part"] = part
    return obj


def _append(objects: List, obj, part: str, version: str, preset_name: str):
    _tag(obj, part, version, preset_name)
    objects.append(obj)
    return obj


def _style_profile(style: str) -> dict[str, float]:
    if style == "cartoon":
        return {"bevel_scale": 1.35, "fairing_scale": 0.70, "tread_scale": 0.85}
    if style == "stylized":
        return {"bevel_scale": 1.15, "fairing_scale": 0.85, "tread_scale": 0.95}
    if style == "cyberpunk":
        return {"bevel_scale": 0.85, "fairing_scale": 1.15, "tread_scale": 1.05}
    return {"bevel_scale": 1.0, "fairing_scale": 1.0, "tread_scale": 1.0}




def _apply_seed_variation(preset: BikePreset, options: BuildOptions) -> BikePreset:
    """Apply small, deterministic proportion changes to avoid clone-like assets."""
    strength = float(options.variant_strength or 0.0)
    if options.seed is None or strength <= 0.0:
        return preset

    rng = random.Random(f"motoforge:{preset.name}:{options.seed}")

    def scaled(value: float, spread: float) -> float:
        return value * (1.0 + rng.uniform(-spread, spread) * strength)

    changes = {
        "wheelbase": scaled(preset.wheelbase, 0.045),
        "wheel_radius": scaled(preset.wheel_radius, 0.035),
        "tire_thickness": scaled(preset.tire_thickness, 0.10),
        "tank_length": scaled(preset.tank_length, 0.085),
        "tank_height": scaled(preset.tank_height, 0.10),
        "seat_length": scaled(preset.seat_length, 0.08),
        "handlebar_width": scaled(preset.handlebar_width, 0.08),
        "tail_lift": max(0.0, preset.tail_lift + rng.uniform(-0.035, 0.065) * strength),
        "fork_rake": max(0.10, scaled(preset.fork_rake, 0.10)),
    }
    return replace(preset, **changes)


def _build_tire_tread(prefix: str, center: Point, preset: BikePreset, mats, objects: List, options: BuildOptions, version: str):
    """Add subtle tread ridges on the outer surface of the tire torus."""
    detail = DETAIL_PROFILES[options.detail]
    cx, cy, cz = center
    block_count = detail["tread_blocks"]

    if preset.name in ("dirt_bike", "cyber_scrambler"):
        # Chunky blocks, but properly sized so they don't look like giant paddles
        radius = preset.wheel_radius + preset.tire_thickness * 0.10
        block_width = preset.wheel_width * 0.70
        block_depth = preset.tire_thickness * 0.20
        block_arc = (2.0 * math.pi / block_count) * 0.60
        arc_width = block_arc * radius

        for i in range(block_count):
            angle = 2.0 * math.pi * i / block_count + block_arc / 2.0
            x = cx + math.cos(angle) * radius
            z = cz + math.sin(angle) * radius
            block = add_beveled_box(
                f"{prefix}_tread_{i:02d}",
                (x, cy, z),
                (block_depth, block_width, arc_width),
                mats["rubber_edge"],
                bevel=0.002,
                bevel_segments=1,
            )
            # Use rotation_mode = 'QUATERNION' for perfect radial alignment
            cy_ang = math.cos(-angle / 2.0)
            sy_ang = math.sin(-angle / 2.0)
            block.rotation_mode = 'QUATERNION'
            block.rotation_quaternion = (cy_ang, 0.0, sy_ang, 0.0)
            _append(objects, block, f"{prefix}_tread", version, preset.name)
    else:
        # Sport / Street / Cafe Racer: V-pattern subtle treads
        block_count = int(block_count * 1.5)
        block_width = preset.wheel_width * 0.42
        block_depth = preset.tire_thickness * 0.05
        block_arc = (2.0 * math.pi / block_count) * 0.85

        # Move them slightly inwards to wrap the tire curve
        y_offset = preset.wheel_width * 0.22
        radius = preset.wheel_radius + preset.tire_thickness * 0.02
        arc_width = block_arc * radius

        for i in range(block_count):
            angle = 2.0 * math.pi * i / block_count
            twist = 0.45 # ~25 degrees twist

            # Left block
            xl = cx + math.cos(angle) * radius
            zl = cz + math.sin(angle) * radius
            bl = add_beveled_box(
                f"{prefix}_tread_L_{i:02d}",
                (xl, cy - y_offset, zl),
                (block_depth, block_width, arc_width),
                mats["rubber_edge"],
                bevel=0.001,
                bevel_segments=1,
            )
            bl.rotation_mode = 'QUATERNION'
            cy_ang = math.cos(-angle / 2.0)
            sy_ang = math.sin(-angle / 2.0)
            cx_ang = math.cos(twist / 2.0)
            sx_ang = math.sin(twist / 2.0)
            w = cy_ang * cx_ang
            x = cy_ang * sx_ang
            y = sy_ang * cx_ang
            z = sy_ang * sx_ang
            bl.rotation_quaternion = (w, x, y, z)
            _append(objects, bl, f"{prefix}_tread", version, preset.name)

            # Right block (staggered slightly by shifting angle? No, keep V shape)
            xr = cx + math.cos(angle) * radius
            zr = cz + math.sin(angle) * radius
            br = add_beveled_box(
                f"{prefix}_tread_R_{i:02d}",
                (xr, cy + y_offset, zr),
                (block_depth, block_width, arc_width),
                mats["rubber_edge"],
                bevel=0.001,
                bevel_segments=1,
            )
            br.rotation_mode = 'QUATERNION'
            cx_ang2 = math.cos(-twist / 2.0)
            sx_ang2 = math.sin(-twist / 2.0)
            w2 = cy_ang * cx_ang2
            x2 = cy_ang * sx_ang2
            y2 = sy_ang * cx_ang2
            z2 = sy_ang * sx_ang2
            br.rotation_quaternion = (w2, x2, y2, z2)
            _append(objects, br, f"{prefix}_tread", version, preset.name)


def _build_wheel(prefix: str, center: Point, preset: BikePreset, mats, objects: List, options: BuildOptions, version: str):
    cx, cy, cz = center
    detail = DETAIL_PROFILES[options.detail]
    wheel_detail = options.wheel_detail or preset.default_wheel_detail

    tire = add_torus_wheel(
        f"{prefix}_tire",
        center,
        preset.wheel_radius,
        preset.tire_thickness,
        mats["rubber"],
        major_segments=detail["wheel_segments"],
        minor_segments=detail["minor_segments"],
    )
    _append(objects, tire, f"{prefix}_tire", version, preset.name)

    rim = add_torus_wheel(
        f"{prefix}_rim",
        center,
        preset.wheel_radius * 0.63,
        preset.tire_thickness * 0.22,
        mats["metal"],
        major_segments=max(28, detail["wheel_segments"] - 8),
        minor_segments=6,
    )
    _append(objects, rim, f"{prefix}_rim", version, preset.name)

    hub = add_y_cylinder(f"{prefix}_hub", center, preset.wheel_radius * 0.13, preset.wheel_width + 0.045, mats["dark_metal"], vertices=24)
    _append(objects, hub, f"{prefix}_hub", version, preset.name)

    if options.brake_disc:
        brake_parts = add_disc_brake_assembly(
            f"{prefix}_disc_brake",
            (cx, cy - preset.wheel_width * 0.62, cz),
            preset.wheel_radius * 0.34,
            mats["metal"],
            mats["dark_metal"],
            holes=8 if options.detail != "high" else 12,
        )
        for part in brake_parts:
            _append(objects, part, f"{prefix}_brake", version, preset.name)
        caliper = add_beveled_box(
            f"{prefix}_brake_caliper",
            (cx + preset.wheel_radius * 0.25, cy - preset.wheel_width * 0.70, cz + preset.wheel_radius * 0.23),
            (0.11, 0.055, 0.16),
            mats["accent"],
            bevel=0.015,
            bevel_segments=2,
        )
        caliper.rotation_euler[1] = -0.45
        _append(objects, caliper, f"{prefix}_brake_caliper", version, preset.name)

    rim_radius = preset.wheel_radius * 0.58
    if wheel_detail == "spokes":
        spoke_radius = preset.frame_tube_radius * 0.16
        for i in range(detail["spokes"]):
            angle = 2.0 * math.pi * i / detail["spokes"]
            target = (cx + math.cos(angle) * rim_radius, cy, cz + math.sin(angle) * rim_radius)
            source_y = cy + (0.035 if i % 2 == 0 else -0.035)
            spoke = add_cylinder_between(f"{prefix}_spoke_{i:02d}", (cx, source_y, cz), target, spoke_radius, mats["metal"], vertices=6)
            _append(objects, spoke, f"{prefix}_spoke", version, preset.name)
    elif wheel_detail == "alloy":
        for i in range(6):
            angle = 2.0 * math.pi * i / 6.0
            target = (cx + math.cos(angle) * rim_radius * 0.92, cy, cz + math.sin(angle) * rim_radius * 0.92)
            blade = add_cylinder_between(f"{prefix}_alloy_spoke_{i:02d}", (cx, cy, cz), target, preset.frame_tube_radius * 0.55, mats["metal"], vertices=8)
            _append(objects, blade, f"{prefix}_alloy_spoke", version, preset.name)

    _build_tire_tread(prefix, center, preset, mats, objects, options, version)


def _build_frame(rear: Point, front: Point, preset: BikePreset, mats, objects: List, options: BuildOptions, version: str):
    rear_x, _, wheel_z = rear
    front_x, _, _ = front
    r = preset.frame_tube_radius
    sport_bias = 1.0 if (options.silhouette == "sporty" or preset.name == "sport_bike") else 0.0

    bottom = (-0.22, 0.0, wheel_z + preset.ground_clearance + 0.22)
    seat_front = (-0.35, 0.0, 1.36 + preset.ground_clearance * 0.25 + sport_bias * 0.03)
    seat_back = (-0.98, 0.0, 1.32 + preset.ground_clearance * 0.20 + preset.tail_lift)
    head = (front_x - preset.fork_rake - 0.22, 0.0, 1.42 + preset.ground_clearance * 0.10 - sport_bias * 0.04)
    pivot = (-0.62, 0.0, 0.93 + preset.ground_clearance * 0.35)

    for y in (-0.055, 0.055):
        tubes = [
            (f"frame_spine_{y:+.2f}", seat_front, head),
            (f"frame_down_{y:+.2f}", head, bottom),
            (f"frame_lower_{y:+.2f}", bottom, pivot),
            (f"frame_seat_rail_{y:+.2f}", seat_back, seat_front),
            (f"frame_sub_{y:+.2f}", seat_back, pivot),
            (f"swingarm_upper_{y:+.2f}", (rear_x, y, wheel_z), pivot),
            (f"swingarm_lower_{y:+.2f}", (rear_x, y, wheel_z - 0.03), (pivot[0], y, pivot[2] - 0.08)),
        ]
        for name, a, b in tubes:
            aa = (a[0], y, a[2])
            bb = (b[0], y, b[2])
            tube = add_cylinder_between(f"MF_{name}", aa, bb, r, mats["dark_metal"], vertices=10)
            _append(objects, tube, "frame", version, preset.name)

    _append(objects, add_cylinder_between("MF_head_tube", (head[0] - 0.05, 0, head[2] - 0.16), (head[0] + 0.05, 0, head[2] + 0.16), r * 1.18, mats["dark_metal"], vertices=12), "frame_head_tube", version, preset.name)
    _append(objects, add_cylinder_between("MF_cross_brace_rear", (pivot[0], -0.085, pivot[2]), (pivot[0], 0.085, pivot[2]), r * 0.75, mats["metal"], vertices=10), "frame_cross_brace", version, preset.name)

    return {"bottom": bottom, "seat_front": seat_front, "seat_back": seat_back, "head": head, "pivot": pivot}


def _build_fork_and_handlebar(front: Point, frame_points, preset: BikePreset, mats, objects: List, options: BuildOptions, version: str):
    front_x, _, wheel_z = front
    head = frame_points["head"]
    r = preset.frame_tube_radius
    sport_bias = 1.0 if (options.silhouette == "sporty" or preset.name == "sport_bike") else 0.0
    fork_top_z = head[2] + 0.10
    fork_top_x = head[0] + 0.10

    for y in (-preset.wheel_width * 0.62, preset.wheel_width * 0.62):
        lower = (front_x, y, wheel_z)
        upper = (fork_top_x, y, fork_top_z)
        _append(objects, add_cylinder_between(f"MF_fork_outer_{y:+.2f}", lower, upper, r * 0.90, mats["metal"], vertices=14), "front_fork", version, preset.name)
        _append(objects, add_cylinder_between(f"MF_fork_inner_{y:+.2f}", (front_x - 0.035, y, wheel_z + 0.20), (fork_top_x - 0.03, y, fork_top_z - 0.18), r * 0.55, mats["dark_metal"], vertices=12), "front_fork", version, preset.name)

    bar_stem_top = (head[0] + 0.03, 0, head[2] + 0.32 - sport_bias * 0.16)
    _append(objects, add_cylinder_between("MF_handlebar_stem", (head[0], 0, head[2] + 0.08), bar_stem_top, r * 0.70, mats["metal"], vertices=12), "handlebar", version, preset.name)
    half_w = preset.handlebar_width / 2
    drop = -0.05 * sport_bias
    handle_points = [
        (bar_stem_top[0], -half_w * 0.25, bar_stem_top[2]),
        (bar_stem_top[0] + 0.07 + sport_bias * 0.08, -half_w, bar_stem_top[2] + 0.04 + drop),
    ]
    _append(objects, add_curve_tube("MF_handlebar_left", handle_points, r * 0.52, mats["metal"], bevel_resolution=DETAIL_PROFILES[options.detail]["curve_bevel"]), "handlebar", version, preset.name)
    _append(objects, add_curve_tube("MF_handlebar_right", [(p[0], -p[1], p[2]) for p in handle_points], r * 0.52, mats["metal"], bevel_resolution=DETAIL_PROFILES[options.detail]["curve_bevel"]), "handlebar", version, preset.name)
    _append(objects, add_cylinder_between("MF_left_grip", (handle_points[-1][0], handle_points[-1][1], handle_points[-1][2]), (handle_points[-1][0], handle_points[-1][1] - 0.16, handle_points[-1][2]), r * 0.75, mats["rubber"], vertices=12), "handlebar_grip", version, preset.name)
    _append(objects, add_cylinder_between("MF_right_grip", (handle_points[-1][0], -handle_points[-1][1], handle_points[-1][2]), (handle_points[-1][0], -handle_points[-1][1] + 0.16, handle_points[-1][2]), r * 0.75, mats["rubber"], vertices=12), "handlebar_grip", version, preset.name)


def _build_chain(rear: Point, frame_points, preset: BikePreset, mats, objects: List, options: BuildOptions, version: str):
    if not options.chain:
        return
    rear_x, _, wheel_z = rear
    pivot = frame_points["pivot"]
    y = -preset.wheel_width * 0.86
    top_a = (rear_x + 0.05, y, wheel_z + 0.05)
    top_b = (pivot[0] - 0.02, y, pivot[2] - 0.03)
    bot_a = (rear_x + 0.02, y, wheel_z - 0.07)
    bot_b = (pivot[0] - 0.10, y, pivot[2] - 0.15)
    _append(objects, add_cylinder_between("MF_chain_top_run", top_a, top_b, 0.012, mats["dark_metal"], vertices=6), "drive_chain", version, preset.name)
    _append(objects, add_cylinder_between("MF_chain_bottom_run", bot_a, bot_b, 0.012, mats["dark_metal"], vertices=6), "drive_chain", version, preset.name)
    for i in range(10 if options.detail != "high" else 16):
        t = i / (9 if options.detail != "high" else 15)
        x = top_a[0] + (top_b[0] - top_a[0]) * t
        z = top_a[2] + (top_b[2] - top_a[2]) * t
        link = add_beveled_box(f"MF_chain_link_{i:02d}", (x, y, z), (0.045, 0.020, 0.018), mats["metal"], bevel=0.004, bevel_segments=1)
        link.rotation_euler[1] = -0.15
        _append(objects, link, "drive_chain_link", version, preset.name)




def _build_suspension_and_accessories(rear: Point, front: Point, frame_points, preset: BikePreset, mats, objects: List, options: BuildOptions, version: str):
    """Small visual details that make the bike feel like a usable game asset, not a toy."""
    rear_x, _, wheel_z = rear
    front_x, _, _ = front
    r = preset.frame_tube_radius
    ground = preset.ground_clearance
    pivot = frame_points["pivot"]
    seat_back = frame_points["seat_back"]
    head = frame_points["head"]

    # Rear suspension: two angled shocks with coil markers.
    for side, y in (("left", -preset.wheel_width * 0.50), ("right", preset.wheel_width * 0.50)):
        lower = (rear_x + 0.26, y, wheel_z + 0.30)
        upper = (seat_back[0] + 0.10, y, seat_back[2] - 0.12)
        _append(objects, add_cylinder_between(f"MF_{side}_rear_shock_core", lower, upper, r * 0.34, mats["metal"], vertices=10), "rear_suspension", version, preset.name)
        for i in range(6 if options.detail != "low" else 4):
            t = (i + 1) / (7 if options.detail != "low" else 5)
            x = lower[0] + (upper[0] - lower[0]) * t
            z = lower[2] + (upper[2] - lower[2]) * t
            rib = add_beveled_box(
                f"MF_{side}_rear_shock_coil_{i:02d}",
                (x, y, z),
                (0.055, 0.012, 0.026),
                mats["accent"],
                bevel=0.004,
                bevel_segments=1,
            )
            rib.rotation_euler[1] = -0.42
            _append(objects, rib, "rear_suspension_coil", version, preset.name)

    # Radiator and fins, especially visible on sporty/streetfighter silhouettes.
    radiator_z = wheel_z + ground + 0.42
    radiator = add_beveled_box("MF_front_radiator_core", (0.36, 0.0, radiator_z), (0.12, 0.38, 0.34), mats["dark_metal"], bevel=0.018)
    radiator.rotation_euler[1] = -0.08
    _append(objects, radiator, "radiator", version, preset.name)
    for i in range(5):
        fin = add_beveled_box(f"MF_radiator_louver_{i:02d}", (0.295, -0.205, radiator_z - 0.12 + i * 0.06), (0.022, 0.020, 0.032), mats["metal"], bevel=0.002, bevel_segments=1)
        _append(objects, fin, "radiator_louver", version, preset.name)

    # Small dashboard/instrument cluster.
    dash = add_beveled_box("MF_compact_dashboard", (head[0] - 0.03, 0.0, head[2] + 0.20), (0.11, 0.18, 0.045), mats["dark_metal"], bevel=0.012)
    dash.rotation_euler[1] = -0.28
    _append(objects, dash, "dashboard", version, preset.name)

    if options.mirrors:
        mirror_z = head[2] + 0.34
        for side, sign in (("left", -1.0), ("right", 1.0)):
            stem_a = (head[0] + 0.06, sign * preset.handlebar_width * 0.31, mirror_z - 0.05)
            stem_b = (head[0] + 0.12, sign * (preset.handlebar_width * 0.52), mirror_z + 0.05)
            _append(objects, add_cylinder_between(f"MF_{side}_mirror_stem", stem_a, stem_b, r * 0.22, mats["metal"], vertices=8), "mirror_stem", version, preset.name)
            mirror = add_beveled_box(f"MF_{side}_mirror_shell", stem_b, (0.055, 0.14, 0.072), mats["smoked_glass"], bevel=0.012, bevel_segments=2)
            mirror.rotation_euler[2] = sign * 0.08
            _append(objects, mirror, "mirror", version, preset.name)

    if options.turn_signals:
        for side, sign in (("left", -1.0), ("right", 1.0)):
            front_sig = add_beveled_box(f"MF_{side}_front_turn_signal", (front_x - 0.42, sign * 0.24, head[2] - 0.03), (0.050, 0.040, 0.030), mats["amber_light"], bevel=0.010)
            _append(objects, front_sig, "turn_signal", version, preset.name)
            rear_sig = add_beveled_box(f"MF_{side}_rear_turn_signal", (rear_x - 0.24, sign * 0.23, seat_back[2] - 0.06), (0.050, 0.040, 0.030), mats["amber_light"], bevel=0.010)
            _append(objects, rear_sig, "turn_signal", version, preset.name)

    if options.license_plate:
        plate = add_beveled_box("MF_rear_license_plate", (rear_x - 0.36, 0.0, seat_back[2] - 0.18), (0.026, 0.26, 0.12), mats["white_plate"], bevel=0.006, bevel_segments=1)
        plate.rotation_euler[1] = 0.18
        _append(objects, plate, "license_plate", version, preset.name)

    # Minimal side graphic/decal planes as geometry, not texture files.
    for side, sign in (("left", -1.0), ("right", 1.0)):
        decal = add_beveled_box(f"MF_{side}_tank_slash_decal", (0.09, sign * (preset.tank_width * 0.52 + 0.006), 1.43 + ground * 0.15), (0.30, 0.010, 0.045), mats["decal"], bevel=0.003, bevel_segments=1)
        decal.rotation_euler[2] = sign * 0.18
        _append(objects, decal, "tank_decal", version, preset.name)


def _build_collision_proxies(rear: Point, front: Point, frame_points, preset: BikePreset, mats, objects: List, options: BuildOptions, version: str):
    if options.collision == "none":
        return
    rear_x, _, wheel_z = rear
    front_x, _, _ = front
    ground = preset.ground_clearance
    chassis_z = wheel_z + ground + 0.62
    proxies = [
        ("UCX_MF_chassis_01", (-0.18, 0.0, chassis_z), (1.55, 0.44, 0.78)),
        ("UCX_MF_rear_wheel_01", (rear_x, 0.0, wheel_z), (preset.wheel_radius * 2.05, preset.wheel_width * 1.35, preset.wheel_radius * 2.05)),
        ("UCX_MF_front_wheel_01", (front_x, 0.0, wheel_z), (preset.wheel_radius * 2.05, preset.wheel_width * 1.35, preset.wheel_radius * 2.05)),
    ]
    if options.collision == "detailed":
        proxies.extend(
            [
                ("UCX_MF_tank_01", (0.08, 0.0, 1.39 + ground * 0.20), (preset.tank_length, preset.tank_width, preset.tank_height)),
                ("UCX_MF_seat_01", (-0.70, 0.0, 1.31 + ground * 0.30 + preset.tail_lift * 0.4), (preset.seat_length, 0.34, preset.seat_height)),
                ("UCX_MF_front_fork_01", (front_x - 0.22, 0.0, 1.02), (0.20, 0.34, 0.92)),
                ("UCX_MF_tail_01", (rear_x - 0.16, 0.0, frame_points["seat_back"][2] - 0.08), (0.52, 0.36, 0.26)),
            ]
        )
    for name, location, dimensions in proxies:
        proxy = add_beveled_box(name, location, dimensions, mats["collision"], bevel=0.0, bevel_segments=0)
        proxy.display_type = "WIRE"
        _append(objects, proxy, "collision_proxy", version, preset.name)


def _build_fairings(front: Point, frame_points, preset: BikePreset, mats, objects: List, options: BuildOptions, version: str):
    style = _style_profile(options.style)
    scale = preset.fairing_scale * style["fairing_scale"]
    if options.silhouette == "sporty":
        scale = max(scale, 0.85)
    if scale <= 0.05:
        return

    ground = preset.ground_clearance
    front_x, _, _ = front
    # Main side fairings: flat/angular surfaces, not blocky cubes.
    for side, y in (("left", -0.235), ("right", 0.235)):
        panel = add_wedge_panel(
            f"MF_{side}_main_fairing",
            (0.34, y, 1.03 + ground * 0.15),
            0.96 * scale,
            0.045,
            0.46 * scale,
            mats["body"],
            slope=0.42,
        )
        panel.rotation_euler[2] = 0.05 if y < 0 else -0.05
        _append(objects, panel, "side_fairing", version, preset.name)

        vent = add_beveled_box(
            f"MF_{side}_fairing_vent",
            (0.18, y + (-0.028 if y < 0 else 0.028), 0.99 + ground * 0.12),
            (0.20, 0.018, 0.055),
            mats["accent"],
            bevel=0.012,
            bevel_segments=1,
        )
        vent.rotation_euler[2] = 0.10 if y < 0 else -0.10
        _append(objects, vent, "fairing_vent", version, preset.name)

    nose = add_wedge_panel(
        "MF_sport_nose_cowl",
        (front_x - 0.42, 0.0, 1.28 + ground * 0.10),
        0.48 * scale,
        0.44,
        0.30 * scale,
        mats["body"],
        slope=0.72,
    )
    nose.rotation_euler[1] = -0.10
    _append(objects, nose, "front_nose_cowl", version, preset.name)

    windscreen = add_wedge_panel(
        "MF_dark_windscreen",
        (front_x - 0.50, 0.0, 1.50 + ground * 0.10),
        0.25 * scale,
        0.31,
        0.16 * scale,
        mats["smoked_glass"],
        slope=0.45,
    )
    windscreen.rotation_euler[1] = -0.35
    _append(objects, windscreen, "windscreen", version, preset.name)


def _build_body(rear: Point, front: Point, frame_points, preset: BikePreset, mats, objects: List, options: BuildOptions, version: str):
    rear_x, _, wheel_z = rear
    front_x, _, _ = front
    ground = preset.ground_clearance
    style = _style_profile(options.style)
    detail = DETAIL_PROFILES[options.detail]

    tank_center = (0.08, 0.0, 1.39 + ground * 0.20)
    tank = add_ellipsoid(
        "MF_tank_sculpted_lowpoly",
        tank_center,
        (preset.tank_length / 2.0, preset.tank_width / 2.0, preset.tank_height / 2.0),
        mats["body"],
        segments=20 if options.detail != "high" else 28,
        ring_count=8 if options.detail != "high" else 10,
    )
    _append(objects, tank, "fuel_tank", version, preset.name)

    _append(objects, add_beveled_box("MF_tank_lower_shadow", (tank_center[0] - 0.03, 0, tank_center[2] - preset.tank_height * 0.43), (preset.tank_length * 0.72, preset.tank_width * 0.86, 0.035), mats["accent"], bevel=0.025 * style["bevel_scale"]), "tank_shadow", version, preset.name)

    seat_center = (-0.70, 0.0, 1.31 + ground * 0.30 + preset.tail_lift * 0.4)
    seat = add_beveled_box("MF_seat_tapered_block", seat_center, (preset.seat_length, 0.34, preset.seat_height), mats["leather"], bevel=0.06 * style["bevel_scale"])
    seat.rotation_euler[1] = -0.07 if preset.tail_lift else 0.0
    _append(objects, seat, "seat", version, preset.name)
    _append(objects, add_ellipsoid("MF_tail_cowl", (-1.12, 0, seat_center[2] + 0.02 + preset.tail_lift * 0.35), (0.23, 0.17, 0.10), mats["body"], segments=16, ring_count=6), "tail_cowl", version, preset.name)

    engine_z = wheel_z + ground + 0.24
    _append(objects, add_beveled_box("MF_engine_block", (-0.18, 0.0, engine_z), (0.48, 0.36, 0.34), mats["dark_metal"], bevel=0.045), "engine_block", version, preset.name)
    _append(objects, add_y_cylinder("MF_crankcase_round", (-0.24, -0.19, engine_z - 0.02), 0.18, 0.035, mats["metal"], vertices=24), "engine_crankcase", version, preset.name)
    _append(objects, add_y_cylinder("MF_clutch_cover_round", (-0.02, 0.19, engine_z + 0.02), 0.14, 0.035, mats["metal"], vertices=24), "engine_clutch_cover", version, preset.name)
    for i in range(4):
        fin = add_beveled_box(f"MF_engine_cooling_fin_{i:02d}", (-0.18, -0.205, engine_z - 0.11 + i * 0.065), (0.42, 0.030, 0.018), mats["metal"], bevel=0.004, bevel_segments=1)
        _append(objects, fin, "engine_cooling_fin", version, preset.name)

    exhaust_points = [
        (0.08, -0.20, engine_z + 0.08),
        (-0.10, -0.22, engine_z - 0.13),
        (-0.58, -0.23, wheel_z + 0.15),
        (rear_x - 0.02, -0.22, wheel_z + 0.18),
    ]
    _append(objects, add_curve_tube("MF_exhaust_header_to_pipe", exhaust_points, 0.032, mats["metal"], bevel_resolution=detail["curve_bevel"]), "exhaust_pipe", version, preset.name)
    _append(objects, add_cylinder_between("MF_exhaust_tip", (rear_x - 0.04, -0.22, wheel_z + 0.18), (rear_x - 0.34, -0.22, wheel_z + 0.22), 0.055, mats["dark_metal"], vertices=14), "exhaust_tip", version, preset.name)

    _append(objects, add_arc_fender("MF_front_fender", front, preset.wheel_radius + preset.tire_thickness + 0.06, preset.fender_width, 0.035, 55, 125, mats["body"], segments=detail["fender_segments"]), "front_fender", version, preset.name)
    _append(objects, add_arc_fender("MF_rear_fender", rear, preset.wheel_radius + preset.tire_thickness + 0.06, preset.fender_width, 0.035, 50, 130, mats["body"], segments=detail["fender_segments"]), "rear_fender", version, preset.name)

    headlight_center = (front_x - 0.40, 0.0, 1.27 + ground * 0.20)
    if preset.name == "sport_bike" or options.silhouette == "sporty":
        _append(objects, add_beveled_box("MF_left_projector_headlight", (headlight_center[0], -0.09, headlight_center[2]), (0.075, 0.10, 0.055), mats["glass"], bevel=0.018), "headlight", version, preset.name)
        _append(objects, add_beveled_box("MF_right_projector_headlight", (headlight_center[0], 0.09, headlight_center[2]), (0.075, 0.10, 0.055), mats["glass"], bevel=0.018), "headlight", version, preset.name)
    else:
        _append(objects, add_cylinder_between("MF_headlight_bucket", (headlight_center[0] - 0.05, 0, headlight_center[2]), (headlight_center[0] + 0.10, 0, headlight_center[2]), 0.115, mats["dark_metal"], vertices=24), "headlight_bucket", version, preset.name)
        _append(objects, add_cylinder_between("MF_headlight_lens", (headlight_center[0] + 0.09, 0, headlight_center[2]), (headlight_center[0] + 0.105, 0, headlight_center[2]), 0.095, mats["glass"], vertices=24), "headlight_lens", version, preset.name)

    _append(objects, add_beveled_box("MF_tail_light", (rear_x - 0.28, 0.0, seat_center[2] - 0.02), (0.05, 0.18, 0.055), mats["red_light"], bevel=0.015), "tail_light", version, preset.name)
    _append(objects, add_cylinder_between("MF_left_footpeg", (-0.32, -0.17, engine_z - 0.02), (-0.32, -0.36, engine_z - 0.02), 0.022, mats["rubber"], vertices=10), "footpeg", version, preset.name)
    _append(objects, add_cylinder_between("MF_right_footpeg", (-0.32, 0.17, engine_z - 0.02), (-0.32, 0.36, engine_z - 0.02), 0.022, mats["rubber"], vertices=10), "footpeg", version, preset.name)

    _build_fairings(front, frame_points, preset, mats, objects, options, version)


def _convert_curves_to_mesh(objects: List):
    import bpy

    converted = []
    for obj in objects:
        if obj.type == "CURVE":
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.convert(target="MESH")
            converted.append(bpy.context.object)
        else:
            converted.append(obj)
    return converted


def _render_preview(path: Path):
    import bpy

    path.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.film_transparent = False
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def _object_stats(objects: List) -> dict[str, Any]:
    mesh_count = 0
    curve_count = 0
    polygon_count = 0
    vertices_count = 0
    materials = set()
    parts = set()
    for obj in objects:
        if obj.type == "MESH":
            mesh_count += 1
            polygon_count += len(obj.data.polygons)
            vertices_count += len(obj.data.vertices)
        elif obj.type == "CURVE":
            curve_count += 1
        for slot in getattr(obj, "material_slots", []):
            if slot.material:
                materials.add(slot.material.name)
        part = obj.get("motoforge_part")
        if part:
            parts.add(part)
    return {
        "object_count": len(objects),
        "mesh_count": mesh_count,
        "curve_count": curve_count,
        "polygon_count": polygon_count,
        "vertices_count": vertices_count,
        "material_count": len(materials),
        "materials": sorted(materials),
        "parts": sorted(parts),
    }


def _write_manifest(path: Path, version: str, options: BuildOptions, output: Path, preview: Path | None, objects: List):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "motoforge_version": version,
        "schema_version": 2,
        "asset": {
            "type": "motorcycle",
            "preset": options.preset,
            "output": str(output),
            "preview": str(preview) if preview else None,
        },
        "game_pipeline": {
            "collision": options.collision,
            "lods_requested": options.lods,
            "seed": options.seed,
            "variant_strength": options.variant_strength,
            "recommended_import_scale": 1.0,
            "forward_axis": "-Y",
            "up_axis": "Z",
        },
        "options": options.to_dict(),
        "stats": _object_stats(objects),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_motorcycle_from_options(options: BuildOptions):
    from . import __version__
    import bpy

    validate_options(options)
    output = Path(options.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    preview = Path(options.preview or preview_path_for(output)) if options.preview != "" else None
    manifest = Path(options.manifest or manifest_path_for(output)) if options.manifest != "" else None

    preset = get_preset(options.preset).with_color_overrides(options.primary_color, options.accent_color)
    preset = _apply_seed_variation(preset, options)

    _clear_scene()
    ground = _setup_scene(options.style)
    mats = build_materials(preset, style=options.style)
    ground.data.materials.append(mats["accent"])

    objects: List = []
    rear = (-preset.wheelbase / 2.0, 0.0, preset.wheel_radius)
    front = (preset.wheelbase / 2.0, 0.0, preset.wheel_radius)

    _build_wheel("MF_rear", rear, preset, mats, objects, options, __version__)
    _build_wheel("MF_front", front, preset, mats, objects, options, __version__)
    frame_points = _build_frame(rear, front, preset, mats, objects, options, __version__)
    _build_fork_and_handlebar(front, frame_points, preset, mats, objects, options, __version__)
    _build_chain(rear, frame_points, preset, mats, objects, options, __version__)
    _build_body(rear, front, frame_points, preset, mats, objects, options, __version__)
    _build_suspension_and_accessories(rear, front, frame_points, preset, mats, objects, options, __version__)
    _build_collision_proxies(rear, front, frame_points, preset, mats, objects, options, __version__)

    objects = _convert_curves_to_mesh(objects)
    move_objects_to_collection(objects, f"MotoForge_{preset.name}_v003")

    if preview is not None:
        _render_preview(preview)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]

    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_materials="EXPORT",
    )

    if manifest is not None:
        _write_manifest(manifest, __version__, options, output, preview, objects)

    if options.save_blend is not None:
        save_blend = Path(options.save_blend)
        save_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(save_blend))

    return output



def _lod_detail_plan(detail: str) -> list[tuple[str, str]]:
    if detail == "high":
        return [("lod0", "high"), ("lod1", "medium"), ("lod2", "low")]
    if detail == "medium":
        return [("lod0", "medium"), ("lod1", "low"), ("lod2", "low")]
    return [("lod0", "low"), ("lod1", "low"), ("lod2", "low")]


def _optional_lod_path(value: str | None, lod_name: str) -> str | None:
    if value is None:
        return None
    if value == "":
        return ""
    return lod_path_for(value, lod_name)


def build_asset_set_from_options(options: BuildOptions) -> list[Path]:
    """Build one asset, or a small LOD set when options.lods is enabled."""
    validate_options(options)
    if not options.lods:
        return [build_motorcycle_from_options(options)]

    outputs: list[Path] = []
    for lod_name, detail in _lod_detail_plan(options.detail):
        lod_options = replace(
            options,
            output=lod_path_for(options.output, lod_name),
            preview=_optional_lod_path(options.preview, lod_name),
            manifest=_optional_lod_path(options.manifest, lod_name),
            detail=detail,
            lods=False,
        )
        outputs.append(build_motorcycle_from_options(lod_options))
    return outputs



def build_motorcycle(
    preset_name: str,
    output: str | Path,
    save_blend: str | Path | None = None,
    *,
    preview: str | Path | None = None,
    manifest: str | Path | None = None,
    detail: str = "medium",
    style: str = "realistic_lowpoly",
    silhouette: str | None = None,
    wheel_detail: str | None = None,
    chain: bool = True,
    brake_disc: bool = True,
    primary_color: str | None = None,
    accent_color: str | None = None,
    mirrors: bool = True,
    turn_signals: bool = True,
    license_plate: bool = True,
    collision: str = "simple",
    lods: bool = False,
    seed: int | None = None,
    variant_strength: float = 0.0,
):
    """Build and export a procedural motorcycle asset."""
    options = BuildOptions(
        preset=preset_name,
        output=str(output),
        save_blend=str(save_blend) if save_blend is not None else None,
        preview=str(preview) if preview is not None else None,
        manifest=str(manifest) if manifest is not None else None,
        detail=detail,
        style=style,
        silhouette=silhouette,
        wheel_detail=wheel_detail,
        chain=chain,
        brake_disc=brake_disc,
        primary_color=primary_color,
        accent_color=accent_color,
        mirrors=mirrors,
        turn_signals=turn_signals,
        license_plate=license_plate,
        collision=collision,
        lods=lods,
        seed=seed,
        variant_strength=variant_strength,
    )
    outputs = build_asset_set_from_options(options)
    return outputs[0] if len(outputs) == 1 else outputs
