"""Blender 5: actual KiCad GLBs + licensed left/right hand meshes.
Run from the repo: blender -b --python hardware/render/scene.py
The DevKit, IMU, harness, straps, and sensor surfaces are illustrative proxies.
"""
import bpy, math, pathlib, json, hashlib
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
R=pathlib.Path(__file__).resolve().parents[1];OUT=R/'render';AS=OUT/'assets'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
 if c.name!='Collection':bpy.data.collections.remove(c)
def mat(name,color,metal=0,rough=.45):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=(*color,1);s.inputs['Metallic'].default_value=metal;s.inputs['Roughness'].default_value=rough;return m
skin=mat('Hand / warm neutral skin',(.49,.285,.18),rough=.48);ss=skin.node_tree.nodes.get('Principled BSDF');ss.inputs['Subsurface Weight'].default_value=.12
black=mat('Strap / woven charcoal',(.014,.021,.027),rough=.85);foam=mat('Mount / soft elastomer',(.035,.047,.052),rough=.85)
teal=mat('PCB / teal solder mask',(.009,.14,.12),rough=.4);devmat=mat('DevKit PCB / graphite',(.012,.024,.025),rough=.55)
gold=mat('Sensor / amber polyester',(.58,.32,.045),metal=.25,rough=.34);carbon=mat('Sensor / carbon resistive track',(.045,.038,.025),rough=.72)
copper=mat('Contact / plated gold',(.72,.49,.17),metal=.8,rough=.25);metal=mat('Shield / brushed metal',(.56,.61,.64),metal=.85,rough=.3)
white=mat('Markings / warm white',(.79,.85,.84),rough=.65);red=mat('ENABLE / vermilion',(.8,.075,.035),rough=.4)
wirem=[mat('Harness / '+n,c,rough=.55) for n,c in [('signal',(.05,.52,.53)),('power',(.65,.12,.06)),('ground',(.018,.025,.03)),('clock',(.75,.5,.05))]]
def cube(name,loc,dim,m,bevel=.0006):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if m:o.data.materials.append(m)
 if bevel:mod=o.modifiers.new('Soft edges','BEVEL');mod.width=bevel;mod.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
def curve(name,points,radius,m):
 c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=12;c.bevel_depth=radius;c.bevel_resolution=3;s=c.splines.new('BEZIER');s.bezier_points.add(len(points)-1)
 for bp,pt in zip(s.bezier_points,points):bp.co=pt;bp.handle_left_type='AUTO';bp.handle_right_type='AUTO'
 o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);o.data.materials.append(m);return o
def cylinder(name,loc,r,depth,m):
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=r,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(m);be=o.modifiers.new('Edge bevel','BEVEL');be.width=.0003;be.segments=2;return o
def text(s,loc,size,m,name=None):
 c=bpy.data.curves.new(name or s,'FONT');c.body=s;c.size=size;c.align_x='CENTER';c.space_character=1.12;c.extrude=0;c.resolution_u=8;o=bpy.data.objects.new(name or s,c);bpy.context.collection.objects.link(o);o.location=loc;o.data.materials.append(m);return o
def strap(name,y,rx,rz,centre=-.001,width=.01):
 verts=[];faces=[];steps=80
 for j in range(steps):
  a=2*math.pi*j/steps
  for yy in [-width/2,width/2]:verts.append((rx*math.cos(a),y+yy,centre+rz*math.sin(a)))
 for j in range(steps):k=2*j;n=2*((j+1)%steps);faces.append((k,n,n+1,k+1))
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(black);mod=o.modifiers.new('Webbing thickness','SOLIDIFY');mod.thickness=.001;return o

def ribbon(name,points,width,m,thick=.00048):
 vs=[];fs=[]
 for i,pt in enumerate(points):
  tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)]);d=Vector((-tangent.y,tangent.x,0)).normalized()*width/2
  vs.extend([Vector(pt)+d,Vector(pt)-d])
 for i in range(len(points)-1):fs.append((2*i,2*i+1,2*i+3,2*i+2))
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(m);so=o.modifiers.new('Film thickness','SOLIDIFY');so.thickness=thick;return o
manifest={'scene_units':'meters','carrier_origin':'KiCad GLB origin (x, -PCB_y, z); translate (-0.033,0.088,0.025)','hand_asset_revision':'f4992299601614adbfefd398dc8e281556bb7444','components':'DevKit and IMU approximate envelopes; PCB geometry imported without scaling','hands':[]}
for side,ox,angle in [('left',-.095,math.radians(-7)),('right',.095,math.radians(7))]:
 start=set(bpy.data.objects)
 with bpy.data.libraries.load(str(AS/(side+'-baked.blend')),link=False) as (src,dst):dst.objects=[n for n in src.objects if 'actual hand mesh' in n]
 obj=dst.objects[0];bpy.context.collection.objects.link(obj);new=obj.data;verts=[v.co.copy() for v in new.vertices]
 obj.data.materials.clear();obj.data.materials.append(skin)
 for poly in obj.data.polygons:poly.use_smooth=True
 sub=obj.modifiers.new('Hand surface smoothing','SUBSURF');sub.levels=2;sub.render_levels=2
 bonep={n:Vector(v) for n,v in json.loads((AS/(side+'-bones.json')).read_text()).items()}
 bvh=BVHTree.FromPolygons(verts,[list(f.vertices) for f in new.polygons])
 def surface(v,zoff=.001):
  hit=bvh.ray_cast(Vector((v.x,v.y,.2)),Vector((0,0,-1)),.4)[0]
  return Vector((v.x,v.y,hit.z+zoff if hit else v.z+.01))
 created={obj}
 # Add a short forearm extension behind the source mesh's cut wrist.
 bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,location=(0,-.032,-.001));o=bpy.context.object;o.name=side+' / illustrative wrist extension';o.scale=(.027,.055,.016);o.data.materials.append(skin)
 for f in o.data.polygons:f.use_smooth=True
 strap(side+' / wrist webbing',-.018,.031,.018,width=.014)
 strap(side+' / palm webbing',.048,.042,.020,width=.013)
 # Four localized cushions retain ventilation and avoid inventing a fitted enclosure.
 for x in [-.026,.026]:
  for y in [.021,.074]:cube(side+' / illustrative cushion',(x,y,.0205),(.012,.015,.006),foam,.002)
 pre=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(R/'build'/side/'carrier.glb'));pcbobjects=set(bpy.data.objects)-pre
 for o in pcbobjects:
  if o.parent is None:o.location+=Vector((-.033,.088,.025))
  o.name=side+' / KiCad / '+o.name
  if o.type=='MESH' and 'soldermask' in o.name.lower():o.data.materials.clear();o.data.materials.append(teal)
 # Approximate genuine DevKitC-1 dimensions, following Espressif mechanical drawing.
 cube(side+' / DevKit PCB proxy',(0,.04390,.0362),(.0254,.06274,.0016),devmat,.0005)
 cube(side+' / WROOM substrate proxy',(0,.0688,.0375),(.018,.0255,.001),devmat,.0003)
 cube(side+' / WROOM shield proxy',(0,.065,.0396),(.0178,.0175,.0032),metal,.0007)
 text('ESP32-S3',(0,.0655,.04125),.0021,devmat)
 # Visible meander proxy above the carrier's antenna notch.
 for dx in [-.006,-.003,0,.003,.006]:curve(side+' / antenna illustration',[(dx,.077,.03805),(dx,.080,.03805)],.00022,copper)
 curve(side+' / antenna bus illustration',[(-.006,.077,.03805),(.006,.077,.03805)],.00022,copper)
 for x in [-.01143,.01143]:
  for i in range(22):cube(side+' / DevKit header',(x,.074-i*.00254,.0353),(.0025,.0022,.0015),black,.0001)
 for x in [-.0052,.0052]:
  cube(side+' / Micro USB shell',(x,.0145,.0388),(.0075,.0055,.0028),metal,.0004);cube(side+' / USB opening',(x,.01172,.0387),(.0058,.0003,.0015),black,.0001)
 cube(side+' / USB UART chip',(0,.034,.038),(.0048,.0048,.001),black,.0002)
 for x in [-.005,.005]:cube(side+' / boot reset proxy',(x,.025,.0384),(.0032,.004,.0017),black,.0003)
 # Motion breakout is rigidly mounted to the separate wrist strap.
 cube(side+' / IMU support',(0,-.018,.020),(.030,.023,.003),foam,.002)
 cube(side+' / Adafruit 5543 envelope proxy',(0,-.018,.023),(.0254,.01778,.0016),teal,.0006)
 for x in [-.006,.005]:cube(side+' / IMU sensor proxy',(x,-.018,.0245),(.003,.003,.0013),black,.0002)
 text('9DOF',(0,-.012,.024),.0019,white)
 for x in [-.010,.010]:
  for y in [-.024,-.012]:cylinder(side+' / IMU screw',(x,y,.025),.0017,.0017,metal)
 for j in range(4):
  dx=(j-1.5)*.0012;curve(side+' / IMU four-wire harness',[(.024+dx,.034,.035),(.039+dx,.016,.029),(.038+dx,-.013,.026),(.011,-.021+dx,.026)],.00055,wirem[j])
 # Five sensors on real finger surfaces, with a dorsal ray cast to place the films.
 fingers=['thumb','index-finger','middle-finger','ring-finger','pinky-finger'];connector={'thumb':(.024,.066),'index-finger':(.024,.053),'middle-finger':(-.026,.066),'ring-finger':(-.026,.053),'pinky-finger':(-.026,.040)}
 sensor_lengths={}
 for fi,finger in enumerate(fingers):
  names=[finger+'-'+n for n in (['metacarpal','phalanx-proximal','phalanx-distal','tip'] if finger=='thumb' else ['metacarpal','phalanx-proximal','phalanx-intermediate','phalanx-distal','tip'])]
  path=[bonep[n] for n in names];prox=path[1];base=prox+(path[0]-prox).normalized()*.025;path=[base]+path[1:]
  points=[]
  for a,b in zip(path,path[1:]):
   for i in range(6):points.append(surface(a.lerp(b,i/6),.0015))
  points.append(surface(path[-1],.0015))
  # Preserve the selected sensor's full 77.57 mm visual length along the surface.
  clipped=[points[0]];length=0.;target=.07757
  for aa,bb in zip(points,points[1:]):
   seg=(bb-aa).length
   if length+seg>=target:
    clipped.append(aa.lerp(bb,(target-length)/seg));break
   clipped.append(bb);length+=seg
  points=clipped
  ribbon(side+' / '+finger+' / flex polyester',points,.00641,gold)
  carbonpts=[p+Vector((0,0,.0003)) for p in points[2:-2]];ribbon(side+' / '+finger+' / resistive strip',carbonpts,.0037,carbon,.0001)
  sensor_lengths[finger]=sum((b-a).length for a,b in zip(points,points[1:]))*1000
  # Two small retention tabs stand for sewn finger pockets.
  for k in [len(points)//3,2*len(points)//3]:
   p=points[k];cube(side+' / '+finger+' / retention tab',(p.x,p.y,p.z+.0006),(.010,.003,.001),black,.0004)
  bx,by=connector[finger];sgn=1 if bx>0 else -1
  for j in range(2):
   pp=points[0]+Vector(((j-.5)*.002,0,.0005));cylinder(side+' / '+finger+' / contact',pp,.0008,.0003,copper)
   curve(side+' / '+finger+' / sensor lead',[(bx+(j-.5)*.0015,by,.036),(sgn*.040,by+.008,.038),(sgn*.043,max(by+.02,pp.y-.015),.027),pp],.00055,wirem[j])
 # External ENABLE thumb control; no right-hand button fitted.
 if side=='left':
  cube('LEFT / ENABLE switch mount',(.041,.072,.022),(.013,.016,.007),foam,.002)
  cylinder('LEFT / ENABLE switch',(.041,.072,.028),.0045,.003,red)
  for j in range(2):curve('LEFT / ENABLE external leads',[(-.026+j*.002,.025,.035),(-.039,.008,.029),(.038,.004,.025),(.041+j*.002,.063,.026)],.00055,wirem[2-j])
 # USB supply remains explicit, with cable exiting toward the wrist.
 cube(side+' / USB power plug',(-.0052,.007,.039),(.008,.010,.004),black,.001)
 curve(side+' / USB power cable',[(-.0052,.003,.039),(-.017,-.022,.032),(-.032,-.055,.015),(-.032,-.077,.008)],.00165,black)
 for x,y in [(-.027,.081),(.027,.081),(-.027,.015),(.027,.015)]:cylinder(side+' / carrier mounting screw',(x,y,.027),.0023,.002,metal)
 # Apply one rigid product transform, preserving native PCB component placement.
 allside=(set(bpy.data.objects)-start)|{obj};root=bpy.data.objects.new(side.upper()+' ASSEMBLY',None);bpy.context.collection.objects.link(root)
 for o in allside:
  if o.parent is None:o.parent=root
 root.location.x=ox;root.rotation_euler.z=angle
 manifest['hands'].append({'side':side,'asset_sha256':hashlib.sha256((AS/(side+'.glb')).read_bytes()).hexdigest(),'board_sha256':hashlib.sha256((R/side/(side+'-hand.kicad_pcb')).read_bytes()).hexdigest(),'sensor_visual_path_lengths_mm':sensor_lengths,'sensor_geometry':'illustrative routing; width 6.41 mm, not a cut-length template'})
# The third board belongs to the hub firmware: no flex or motion sensor on it.
pre=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(R/'build'/'hub'/'carrier.glb'))
for o in set(bpy.data.objects)-pre:
 if o.parent is None:o.location+=Vector((-.027,.044,.019))
 o.name='HUB / KiCad / '+o.name
 if o.type=='MESH' and 'soldermask' in o.name.lower():o.data.materials.clear();o.data.materials.append(teal)
for o in list(bpy.data.objects):
 if o.name.startswith('left / ') and any(k in o.name for k in ['DevKit','WROOM','antenna illustration','antenna bus illustration','Micro USB','USB opening','USB UART','boot reset']):
  z=o.copy();z.data=o.data.copy();z.parent=None;z.name=o.name.replace('left /','HUB /');z.location+=Vector((-.007,-.044,-.006));bpy.context.collection.objects.link(z)
cube('HUB / USB data plug',(-.0122,-.037,.033),(.008,.010,.004),black,.001)
curve('HUB / USB data cable to laptop',[(-.0122,-.041,.033),(-.008,-.064,.025),(.007,-.084,.002),(.007,-.116,-.018)],.00165,black)
text('HUB / USB TO HOST',(0,-.051,.001),.0032,white)
manifest['hub']={'board_sha256':hashlib.sha256((R/'hub'/'hub.kicad_pcb').read_bytes()).hexdigest(),'transform_m':[-.027,.044,.019]}

# Clean product studio. Hand meshes and assemblies remain individually editable.
floor=mat('Studio / porcelain',(.72,.75,.73),rough=.8);cube('Studio surface',(0,.07,-.085),(.8,.8,.005),floor,.002)
ink=mat('Typography / charcoal',(.025,.05,.055),rough=.8)
text('PALMPILOT',(0,.245,-.022),.018,ink)
text('T W O   H A N D S   /   O N E   F L I G H T',(0,.228,-.022),.0044,ink)
text('L  /  THROTTLE + YAW',(-.108,-.092,-.022),.0042,ink)
text('R  /  PITCH + ROLL',(.108,-.092,-.022),.0042,ink)
text('REV A     /     USB-POWERED CARRIERS     /     WEARABLE FIT CONCEPT',(0,-.106,-.022),.0028,ink)
def area(name,loc,power,size,color):
 d=bpy.data.lights.new(name,'AREA');o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;d.energy=power;d.shape='DISK';d.size=size;d.color=color;o.rotation_euler=(Vector((0,.08,0))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key softbox',(-.22,-.05,.45),22,.35,(1,.87,.74));area('Fill softbox',(.27,.16,.3),17,.25,(.72,.87,1));area('Rim softbox',(-.1,.35,.32),25,.22,(1,1,1))
world=bpy.context.scene.world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.7,.77,.82,1);world.node_tree.nodes['Background'].inputs[1].default_value=.35
bpy.ops.object.camera_add(location=(0,-.265,.59));cam=bpy.context.object;cam.name='Hero / both hands';cam.rotation_euler=(Vector((0,.075,.003))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.425;bpy.context.scene.camera=cam
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True;sc.render.resolution_x=1700;sc.render.resolution_y=1700;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False;sc.view_settings.view_transform='AgX';sc.view_settings.exposure=-3;sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
(OUT/'assembly-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'palmpilot-two-hands.blend'))
sc.render.filepath=str(OUT/'two-hands.png');bpy.ops.render.render(write_still=True)
# Detail camera keeps the other assembly in the saved project but frames the left hand.
cam.location=(-.24,-.08,.32);cam.rotation_euler=(Vector((-.10,.075,.02))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.255;sc.render.resolution_x=1800;sc.render.resolution_y=1600;sc.render.filepath=str(OUT/'left-hand-detail.png');bpy.ops.render.render(write_still=True)
