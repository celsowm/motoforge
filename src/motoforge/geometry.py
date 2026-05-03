from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple

Point = Tuple[float, float, float]


def assign_material(obj, mat):
    if mat is not None:
        obj.data.materials.append(mat)
    return obj


def shade_smooth(obj):
    import bpy

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    try:
        bpy.ops.object.shade_smooth()
    finally:
        obj.select_set(False)
    return obj


def add_cylinder_between(name: str, start: Point, end: Point, radius: float, mat=None, vertices: int = 12):
    """Add a cylinder whose local Z axis runs from start to end."""
    import bpy
    from mathutils import Vector

    a = Vector(start)
    b = Vector(end)
    direction = b - a
    length = direction.length
    if length <= 1e-6:
        raise ValueError(f"Cylinder '{name}' has zero length")

    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=length, location=a + direction * 0.5)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    assign_material(obj, mat)
    return obj


def add_y_cylinder(name: str, location: Point, radius: float, depth: float, mat=None, vertices: int = 32):
    import bpy

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=(math.pi / 2, 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, mat)
    return obj


def add_torus_wheel(name: str, location: Point, outer_radius: float, tube_radius: float, mat=None, major_segments: int = 40, minor_segments: int = 8):
    import bpy

    major_radius = max(outer_radius - tube_radius, tube_radius * 1.5)
    bpy.ops.mesh.primitive_torus_add(
        major_segments=major_segments,
        minor_segments=minor_segments,
        major_radius=major_radius,
        minor_radius=tube_radius,
        location=location,
        rotation=(math.pi / 2, 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, mat)
    return obj


def add_beveled_box(name: str, location: Point, dimensions: Point, mat=None, bevel: float = 0.04, bevel_segments: int = 3):
    import bpy

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    if bevel > 0:
        modifier = obj.modifiers.new(name="MF_bevel", type="BEVEL")
        modifier.width = bevel
        modifier.segments = bevel_segments
        modifier.affect = "EDGES"
        obj.modifiers.new(name="MF_weighted_normals", type="WEIGHTED_NORMAL")
    assign_material(obj, mat)
    return obj


def add_ellipsoid(name: str, location: Point, scale: Point, mat=None, segments: int = 24, ring_count: int = 8):
    import bpy

    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=ring_count, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign_material(obj, mat)
    shade_smooth(obj)
    return obj


def add_curve_tube(name: str, points: Sequence[Point], radius: float, mat=None, resolution: int = 3, bevel_resolution: int = 4):
    import bpy

    if len(points) < 2:
        raise ValueError("A tube curve needs at least two points")

    curve = bpy.data.curves.new(name=name, type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = resolution
    curve.bevel_depth = radius
    curve.bevel_resolution = bevel_resolution

    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coords in zip(spline.points, points):
        point.co = (coords[0], coords[1], coords[2], 1.0)

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    if mat:
        curve.materials.append(mat)
    return obj


def add_arc_fender(
    name: str,
    center: Point,
    radius: float,
    width: float,
    thickness: float,
    angle_start_deg: float,
    angle_end_deg: float,
    mat=None,
    segments: int = 18,
):
    """Create a curved strip in the XZ plane, with width along Y."""
    import bpy

    verts = []
    faces = []
    c_x, c_y, c_z = center
    outer = radius + thickness
    inner = radius
    y0 = c_y - width / 2.0
    y1 = c_y + width / 2.0

    for i in range(segments + 1):
        t = i / segments
        angle = math.radians(angle_start_deg + (angle_end_deg - angle_start_deg) * t)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        verts.extend(
            [
                (c_x + outer * cos_a, y0, c_z + outer * sin_a),
                (c_x + outer * cos_a, y1, c_z + outer * sin_a),
                (c_x + inner * cos_a, y1, c_z + inner * sin_a),
                (c_x + inner * cos_a, y0, c_z + inner * sin_a),
            ]
        )

    for i in range(segments):
        a = i * 4
        b = (i + 1) * 4
        faces.extend(
            [
                (a, b, b + 1, a + 1),
                (a + 1, b + 1, b + 2, a + 2),
                (a + 2, b + 2, b + 3, a + 3),
                (a + 3, b + 3, b, a),
            ]
        )

    faces.append((0, 1, 2, 3))
    n = segments * 4
    faces.append((n, n + 3, n + 2, n + 1))

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign_material(obj, mat)
    obj.modifiers.new(name="MF_fender_normals", type="WEIGHTED_NORMAL")
    return obj


def add_disc_brake_assembly(name: str, location: Point, radius: float, disc_mat=None, dark_mat=None, holes: int = 8):
    """Disc brake with visible vent markers and a caliper-friendly side face."""
    parts = []
    disc = add_y_cylinder(name, location, radius, 0.014, disc_mat, vertices=32)
    parts.append(disc)
    c_x, c_y, c_z = location
    for i in range(holes):
        angle = 2 * math.pi * i / holes
        hole_x = c_x + math.cos(angle) * radius * 0.58
        hole_z = c_z + math.sin(angle) * radius * 0.58
        hole = add_y_cylinder(f"{name}_vent_{i:02d}", (hole_x, c_y + 0.012, hole_z), radius * 0.055, 0.006, dark_mat or disc_mat, vertices=8)
        parts.append(hole)
    return parts


def add_panel_mesh(name: str, verts: Sequence[Point], faces: Sequence[Sequence[int]], mat=None):
    import bpy

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(list(verts), [], [tuple(face) for face in faces])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign_material(obj, mat)
    obj.modifiers.new(name="MF_panel_normals", type="WEIGHTED_NORMAL")
    return obj


def add_wedge_panel(name: str, location: Point, length: float, width: float, height: float, mat=None, slope: float = 0.35):
    """A small angular fairing-like wedge, useful for sport-bike panels."""
    x, y, z = location
    lx = length / 2
    wy = width / 2
    hz = height / 2
    front_raise = height * slope
    verts = [
        (x - lx, y - wy, z - hz),
        (x - lx, y + wy, z - hz),
        (x + lx, y + wy, z - hz + front_raise),
        (x + lx, y - wy, z - hz + front_raise),
        (x - lx * 0.72, y - wy * 0.82, z + hz),
        (x - lx * 0.72, y + wy * 0.82, z + hz),
        (x + lx, y + wy * 0.62, z + hz + front_raise * 0.45),
        (x + lx, y - wy * 0.62, z + hz + front_raise * 0.45),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]
    return add_panel_mesh(name, verts, faces, mat)


def collection_link_only(obj, collection):
    """Move object into a collection without leaving it scattered in the scene collection."""
    collection.objects.link(obj)
    for col in list(obj.users_collection):
        if col != collection:
            col.objects.unlink(obj)
    return obj


def move_objects_to_collection(objects: Iterable, collection_name: str):
    import bpy

    existing = bpy.data.collections.get(collection_name)
    if existing:
        collection = existing
    else:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
    for obj in objects:
        collection_link_only(obj, collection)
    return collection
