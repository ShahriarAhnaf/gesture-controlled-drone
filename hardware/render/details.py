"""Render RIGHT and HUB close-ups from the saved, revision-bound assembly."""
import pathlib
import bpy
from mathutils import Vector
R=pathlib.Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(R/'render/palmpilot-two-hands.blend'))
scene=bpy.context.scene
camera=scene.camera
scene.render.resolution_x=1700
scene.render.resolution_y=1500
for name,location,target,scale in [
 ('right-hand-detail',(.12,-.03,.28),(.10,.056,.025),.13),
 ('hub-detail',(.065,-.10,.17),(0,.008,.021),.09),
]:
 camera.location=location
 camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
 camera.data.ortho_scale=scale
 scene.render.filepath=str(R/'render'/(name+'.png'))
 bpy.ops.render.render(write_still=True)
