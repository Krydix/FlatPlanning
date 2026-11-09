"""Build the balcony and the daytime sky and sun; run in Blender background. Running it again rebuilds them.
The balcony comes from the assumed block in source/room-measurements.json. The sky is a CC0 Poly Haven
HDRI (Quadrangle Sunny, Savva Zakharov) used for baking; the viewer shows a compressed copy on a dome.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Euler
ROOT=Path(__file__).resolve().parent.parent;B=json.loads((ROOT/'source/room-measurements.json').read_text())['balcony']
DAY={'sky':5.5,'sun':7.0,'practical':.12}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
NAME='19 Balcony - assumed from photo'
co=bpy.data.collections.get(NAME)
if co:
 for o in list(co.objects):bpy.data.objects.remove(o,do_unlink=True)
else:
 co=bpy.data.collections.new(NAME);bpy.context.scene.collection.children.link(co)
def material(name,color,rough=.7,metal=0):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
DECK=material('Balcony composite decking',(.19,.18,.19));STEEL=material('Balcony grey steel',(.11,.125,.14),.5,.6);SLAB=material('Balcony concrete slab',(.42,.42,.40),.85)
def solid(name,boxes,mat):
 # One mesh per material keeps the bar count from becoming hundreds of objects.
 bm=bmesh.new()
 for x0,x1,y0,y1,z0,z1 in boxes:
  r=bmesh.ops.create_cube(bm,size=1)['verts']
  for v in r:v.co=Vector(((x0 if v.co.x<0 else x1)/1000,(y0 if v.co.y<0 else y1)/1000,(z0 if v.co.z<0 else z1)/1000))
 me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);co.objects.link(o);me.materials.append(mat);return o
x0,x1=B['x'];y1=B['outer_y'];door=5370;rail=B['railing_top_z'];pitch=B['bar_pitch'];low=B['slab_bottom_z'];wall=5700;off=26
solid('Balcony slab',[(x0,x1,door,y1,low,-30)],SLAB)
solid('Balcony decking',[(x0,x1,door,y1,-30,0)],DECK)
# Railing on all three open sides, fixed to the slab edge: the bars run the full height down past the deck.
front=[(x-6,x+6,y1+off-20,y1+off+20,low,rail) for x in range(x0-off,x1+off+1,pitch)]
left=[(x0-off-20,x0-off+20,y-6,y+6,low,rail) for y in range(wall+40,y1+off,pitch)]
right=[(x1+off-20,x1+off+20,y-6,y+6,low,rail) for y in range(wall+40,y1+off,pitch)]
top=[(x0-off-25,x1+off+25,y1+off-25,y1+off+25,rail,rail+10),(x0-off-25,x0-off+25,wall,y1+off,rail,rail+10),(x1+off-25,x1+off+25,wall,y1+off,rail,rail+10)]
solid('Balcony railing',front+left+right+top,STEEL)
# Daylight: the HDRI lights the scene, the sun lamp gives the low autumn patch through the door.
world=bpy.context.scene.world;world.use_nodes=True;n=world.node_tree.nodes;l=world.node_tree.links;n.clear()
out=n.new('ShaderNodeOutputWorld');bg=n.new('ShaderNodeBackground');env=n.new('ShaderNodeTexEnvironment');tc=n.new('ShaderNodeTexCoord');mp=n.new('ShaderNodeMapping')
env.image=bpy.data.images.load(str(ROOT/'source/textures/quadrangle_sunny_2k.hdr'),check_existing=True);mp.inputs['Rotation'].default_value=(0,0,math.radians(B.get('sky_rotation',-90)))
bg.inputs['Strength'].default_value=DAY['sky'];l.new(tc.outputs['Generated'],mp.inputs['Vector']);l.new(mp.outputs['Vector'],env.inputs['Vector']);l.new(env.outputs['Color'],bg.inputs['Color']);l.new(bg.outputs['Background'],out.inputs['Surface'])
sun=bpy.data.objects.get('Afternoon sun')
if not sun:
 sun=bpy.data.objects.new('Afternoon sun',bpy.data.lights.new('Afternoon sun','SUN'));next(c for c in bpy.data.collections if c.name.startswith('10 ')).objects.link(sun)
sun.data.energy=DAY['sun'];sun.data.angle=math.radians(1.2);sun.data.color=(1,.96,.9)
# Sun in front of the door, high enough to clear the lintel, slanting in from the left.
sun.rotation_euler=Euler((math.radians(58),0,math.radians(205)),'XYZ');sun.location=(1.4,9,6)
for o in bpy.data.objects:
 if o.name=='Neutral exterior backdrop':o.hide_render=True;o.hide_viewport=True
 # Fixtures stay on but sit well under daylight. The night value is kept so a rerun cannot compound.
 if o.type=='LIGHT' and o.data.type=='AREA' and o.data.energy>0 and 'Afternoon' not in o.name:
  o.data['night_watts']=o.data.get('night_watts',o.data.energy);o.data.energy=o.data['night_watts']*DAY['practical']
# Cycles samples the door opening directly, which keeps a sky-lit interior from going noisy.
portal=bpy.data.objects.get('Balcony door light portal')
if not portal:
 portal=bpy.data.objects.new('Balcony door light portal',bpy.data.lights.new('Balcony door light portal','AREA'));next(c for c in bpy.data.collections if c.name.startswith('10 ')).objects.link(portal)
portal.data.shape='RECTANGLE';portal.data.size=2.32;portal.data.size_y=2.2;portal.data.cycles.is_portal=True;portal.location=(1.42,5.28,1.1);portal.rotation_euler=(math.radians(90),0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
print('EXTERIOR_BUILT',len(co.objects),flush=True)
