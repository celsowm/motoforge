import bpy
bpy.ops.mesh.primitive_cube_add(size=2)
bpy.ops.export_scene.gltf(filepath='C:/dist/test_cube.glb', export_format='GLB', export_apply=True)
print('Exported test cube')
