"""Derive source/flat-portal.blend from the V18 scene; run in Blender background.
Only the frame, the desk module's loose contents, the wardrobe contents, the crates and a few
lights change. The architecture, kitchen, bar and bed stay exactly as they are in V18.
"""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'source'))
from pipe_engine import build,profile_from_measurements
from blender_components import rebuild,model_errors
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
a=build(profile_from_measurements(ROOT/'source/Measurements-v8.json'),portal=True);assert not a.validate()['geometry_errors'],a.validate()['geometry_errors'][:5]
a.save(ROOT/'source/assembly-portal.json');P=a.portal;DESK=P['desk_offset']/1000;LEVELS=json.loads((ROOT/'source/portal-layout.json').read_text())['levels'];t=.028
def collection(prefix):return next(c for c in bpy.data.collections if c.name.startswith(prefix))
FIXED=('01 ','02 ','05 ','08 ','09 ','12 ')
fixed={o.name:tuple(v for row in o.matrix_world for v in row) for o in bpy.context.scene.objects if any(c.name.startswith(FIXED) for c in o.users_collection)}
rebuild(a);assert not model_errors(a),model_errors(a)[:5]
def bounds(o):
 pts=[o.matrix_world@Vector(c) for c in o.bound_box];return Vector(tuple(min(p[i] for p in pts) for i in range(3))),Vector(tuple(max(p[i] for p in pts) for i in range(3)))
def centre(o):
 lo,hi=bounds(o);return (lo+hi)/2
def move(o,dx=0,dy=0,dz=0):
 if not (o.parent and o.parent.users_collection==o.users_collection):o.matrix_world=Matrix.Translation((dx,dy,dz))@o.matrix_world
def remove(o):bpy.data.objects.remove(o,do_unlink=True)
def turn(o,pivot,target,angle=math.pi/2):
 o.matrix_world=Matrix.Translation(target)@Matrix.Rotation(angle,4,'Z')@Matrix.Translation(-Vector(pivot))@o.matrix_world
# Divider boards run across the room, so they take the grain-turned oak.
across=bpy.data.materials.get('Oak across the room')
if across:
 for o in bpy.data.objects:
  if o.name.startswith('Portal.') and ' / ' in o.name and o.data and hasattr(o.data,'materials') and o.parent and o.parent.get('catalog_kind')=='wood':o.data.materials[0]=across
# The desk module is a rigid block in the graph, so its contents follow by the same offset.
for o in list(collection('04 ').objects):
 move(o,dy=DESK)
 # Parked further into the 472 mm knee depth: the chair now stands in the aisle beside the bed.
 if o.name.startswith('Chair'):move(o,dx=.150)
for o in list(collection('14 ').objects):move(o,dy=DESK)
bpy.context.view_layer.update()
strip=[o for o in collection('15 ').objects if o.name.startswith('Rack.top0') and 'cable' not in o.name]
# Wardrobe contents follow the graph: V18's first 606 mm top board started at y 3,948.
RACK=(a.boards['Rack.top0']['bounds'][2]-3948)/1000;BAY=(a.columns['RF0']['y']+a.columns['RF1']['y'])/2000
for o in list(collection('15 ').objects):
 n=o.name
 if n.startswith(('Desk.','V9 TRADFRI','V9 FORNIMMA')):move(o,dy=DESK)
 elif n.startswith('Rack.') and 'cable' in n:remove(o)
 elif n.startswith(('Rack.top1','Rack.top2')):move(o,dy=RACK)
bpy.context.view_layer.update()
# The 960 mm bar and its oak cover turn 90 degrees and light the lintel, cover flush with the kitchen-side edge.
lintel=P['lintel']/1000;front=(P['rows'][0]-45)/1000;pivot=(3.055,3.410,2.190);target=(P['cx']/1000,front,lintel)
for o in strip:turn(o,pivot,target)
bpy.context.view_layer.update()
# Two further 460 mm bars under the highest full shelves. Same housing, diffuser and light as the wardrobe bars.
top=len(LEVELS)-1;board=a.boards[f'Portal.shelfL{top}']['bounds'];right=a.boards[f'Portal.shelfR{top}']['bounds'];z5=LEVELS[top]/1000
for side,xc in (('L',(board[0]+board[1])/2000),('R',(right[0]+right[1])/2000)):
 for o in [o for o in collection('15 ').objects if o.name.startswith('Rack.top2 ÖVERSIDAN')]:
  c=o.copy();c.name=f'Portal.shelf{side}{top} '+o.name.split(' ',1)[1]
  if o.data:c.data=o.data.copy()
  collection('15 ').objects.link(c);turn(c,(3.055,4.883+RACK,2.190),(xc,front,z5))
bpy.context.view_layer.update()
# Clothes follow their bays. Seven short garments fit the 602 mm bay; coats rise with their rail.
piles=[]
for o in list(collection('07 ').objects):
 n=o.name;lo,hi=bounds(o);c=(lo+hi)/2
 if 'curtain' in n.lower():continue
 if 'folded pullover' in n:piles.append(o);continue
 if 'wear-again' in n or 'over wear rail' in n:remove(o);continue
 if c.y<3.95:
  if c.y>3.56:remove(o)
  else:move(o,dy=BAY-3.296)
 else:move(o,dy=RACK,dz=0 if hi.z<.40 else .080)
bpy.context.view_layer.update()
# Eight folded stacks, three pullovers each, stand across the tower bays between the bores.
# They sit slightly forward: the desk's tower pipes cross the rear row at 485 and 689 mm.
xs=P['xs'];ymid=P['ymid']/1000-.020;piles.sort(key=lambda o:(bounds(o)[0].z,bounds(o)[0].y));stacks=[piles[i:i+3] for i in range(0,len(piles),3)]
stacks.sort(key=lambda s:(bounds(s[0])[0].z,bounds(s[0])[0].y))
places=[((xs[0]+xs[1])/2000,LEVELS[k]/1000+t) for k in (1,2,3,4)]+[((xs[2]+xs[3])/2000,LEVELS[k]/1000+t) for k in (1,2,3,4)]
for stack,(x,z) in zip(stacks,places):
 base=min(bounds(o)[0].z for o in stack)
 for o in stack:
  lo,hi=bounds(o);c=(lo+hi)/2;turn(o,(c.x,c.y,base),(x,ymid,z+.005))
bpy.context.view_layer.update()
# KNAGGLIG: the collection asset has its long side along Y and its origin at the base centre.
for o,(x,y,z) in zip(collection('18 ').objects,P['crates']):
 o.location=(x/1000,y/1000,z/1000);o.rotation_euler=(0,0,math.pi/2)
assert all(tuple(v for row in bpy.data.objects[n].matrix_world for v in row)==m for n,m in fixed.items()),'A fixed object moved'
for o in bpy.data.objects:
 if o.type=='LIGHT' and 'ceiling' in o.name.lower():o.data.energy=0
# Kitchen-side view through the door, matching the reference image's framing.
cam=bpy.data.objects['01 Entrance perspective'];cam.location=(2.36,.42,1.42);cam.rotation_euler=(math.radians(93),0,0);cam.data.lens=16
for text in bpy.data.texts:
 if text.name.startswith('Assembly'):text.clear();text.write((ROOT/'source/assembly-portal.json').read_text())
bpy.context.scene['desk_joint_revision']='Portal divider variant derived from V18'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/flat-portal.blend'))
print('PORTAL_BUILT',len(a.parts),flush=True)
