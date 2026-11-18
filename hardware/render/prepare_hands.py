"""Bake each licensed skinned hand in an isolated scene before assembly imports."""
import bpy,pathlib,json
from mathutils import Vector,Matrix
D=pathlib.Path(__file__).resolve().parent/'assets'
for side in ['left','right']:
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 bpy.ops.import_scene.gltf(filepath=str(D/(side+'.glb')));bpy.context.view_layer.update()
 arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH');bones={b.name:arm.matrix_world@b.head for b in arm.pose.bones};wrist=bones['wrist'];fw=(bones['middle-finger-phalanx-proximal']-wrist).normalized();ac=bones['index-finger-phalanx-proximal']-bones['pinky-finger-phalanx-proximal']
 if side=='right':ac=-ac
 ac=(ac-fw*ac.dot(fw)).normalized();up=ac.cross(fw).normalized();basis=Matrix([ac,fw,up]);canon=lambda v:basis@(v-wrist)
 ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());data=bpy.data.meshes.new_from_object(ev);vs=[canon(mesh.matrix_world@v.co) for v in data.vertices]
 assert max(v.y for v in vs)<.25 and max(abs(v.z) for v in vs)<.1,side
 for v,c in zip(data.vertices,vs):v.co=c
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 o=bpy.data.objects.new(side.upper()+' / actual hand mesh',data);bpy.context.collection.objects.link(o)
 (D/(side+'-bones.json')).write_text(json.dumps({n:list(canon(v)) for n,v in bones.items()},indent=2)+'\n')
 bpy.ops.wm.save_as_mainfile(filepath=str(D/(side+'-baked.blend')))
 print(side,'baked bounds',[(min(v[i] for v in vs),max(v[i] for v in vs)) for i in range(3)],flush=True)
