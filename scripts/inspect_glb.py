import trimesh
import sys

filepath = sys.argv[1] if len(sys.argv) > 1 else "dist/streetfighter.glb"
scene = trimesh.load(filepath)
print(f"Type: {type(scene).__name__}")

if hasattr(scene, "geometry"):
    print(f"Geometries count: {len(scene.geometry)}")
    for i, (name, geom) in enumerate(scene.geometry.items()):
        if i >= 5:
            break
        verts = getattr(geom, "vertices", None)
        faces = getattr(geom, "faces", None)
        print(f"  {name}:")
        if verts is not None:
            print(f"    vertices: {verts.shape}")
        else:
            print(f"    vertices: None")
        if faces is not None:
            print(f"    faces: {faces.shape}")
        else:
            print(f"    faces: None")
elif hasattr(scene, "n_points"):
    print(f"Single mesh: {scene.n_points} points, {scene.n_cells} cells")
