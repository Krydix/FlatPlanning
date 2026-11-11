"""Bring the existing kitchen corner in line with the occupant's photos (2026-11-11).
Run with Blender in background mode; it rewrites source/flat-v18.blend (V18 only, the portal is frozen).

- Kitchen run, from the left (bed) wall: wide end cabinet, built-in oven with a drawer below
  and the hob above, a slim 45 cm integrated dishwasher, then the sink cabinet at the door end.
  Each upper door lines up with the unit below it. Widths are read from the photos and scaled
  to the assumed 2,410 mm run, so they move if the run is measured.
- Five existing KNAGGLIG crates lie on their long side on the upper cabinets (310 mm tall,
  under a 320 mm gap), bottoms to the room.
- The room door is a frameless clear glass leaf in a white frame, with a clear transom above.
- Two IKEA DALFRED bar stools (seat Ø300, 63–74 cm) stand at the bar under the pendants,
  pulled out as far as the daybed allows. Their tripod spread is read from product photos.
"""
import bpy,bmesh,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent.parent
FILE=ROOT/'source/flat-v18.blend'
bpy.ops.wm.open_mainfile(filepath=str(FILE))
M=bpy.data.materials
def coll(name):
 c=bpy.data.collections.get(name)
 if not c:c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
 return c
KITCHEN=next(c for c in bpy.data.collections if c.name.startswith('02 '));DOORS=next(c for c in bpy.data.collections if c.name.startswith('12 '))
def drop(*prefixes,collection=None):
 for o in list(bpy.data.objects):
  if o.name.startswith(prefixes) and (collection is None or collection in o.users_collection):bpy.data.objects.remove(o,do_unlink=True)
def box(name,lo,hi,mat,c,bevel=2,segments=1):
 lo=Vector(lo);hi=Vector(hi);me=bpy.data.meshes.new(name);bm=bmesh.new();bmesh.ops.create_cube(bm,size=1);bmesh.ops.scale(bm,vec=(hi-lo)/1000,verts=bm.verts);bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);c.objects.link(o);o.location=(lo+hi)/2000;me.materials.append(mat if isinstance(mat,bpy.types.Material) else M[mat])
 if bevel:mod=o.modifiers.new('Bevel','BEVEL');mod.width=bevel/1000;mod.segments=segments;mod.limit_method='ANGLE'
 return o
def cylinder(name,a,b,r,mat,c,verts=24):
 a=Vector(a)/1000;b=Vector(b)/1000;me=bpy.data.meshes.new(name);bm=bmesh.new()
 bmesh.ops.create_cone(bm,cap_ends=True,segments=verts,radius1=r/1000,radius2=r/1000,depth=(b-a).length);bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);c.objects.link(o);me.materials.append(M[mat] if isinstance(mat,str) else mat)
 o.matrix_world=Matrix.Translation((a+b)/2)@(b-a).to_track_quat('Z','Y').to_matrix().to_4x4()
 for p in me.polygons:p.use_smooth=True
 return o
# Kitchen run: x from the left wall, y from the partition (0) to the worktop front (735).
RUN=2410;UNITS=[('end',760),('oven',600),('dishwasher',450),('sink',600)]
scale=RUN/sum(w for _,w in UNITS);edges=[0]
for _,w in UNITS:edges.append(round(edges[-1]+w*scale))
X={k:(edges[i],edges[i+1]) for i,(k,_) in enumerate(UNITS)}
drop('Kitchen white front','Black oven front','Oven control','Oven handle','Fixed black hob','Hob ring','Sink steel rim','Sink bowl','Fixed upper white cabinet','Kitchen tap','Kitchen faucet','Oven drawer front','Dishwasher integrated front','Kitchen plinth')
FRONT='Fixed white worktop';WHITE='Rental white matte'
box('Kitchen plinth',(0,630,0),(RUN,670,130),WHITE,KITCHEN)
for k in ('end','sink'):box('Kitchen white front',(X[k][0]+2,693,70),(X[k][1]-2,711,850),FRONT,KITCHEN)
box('Dishwasher integrated front',(X['dishwasher'][0]+2,693,70),(X['dishwasher'][1]-2,711,850),FRONT,KITCHEN)
a,b=X['oven'];mid=(a+b)/2
box('Oven drawer front',(a+2,693,70),(b-2,711,248),FRONT,KITCHEN)
box('Black oven front',(a+2,700,255),(b-2,724,762),'Oven glass',KITCHEN)
box('Oven controls',(a+2,700,766),(b-2,726,850),'DOLLE PIPE black powdercoat',KITCHEN)
cylinder('Oven control knob',(mid,726,808),(mid,748,808),24,'Brushed steel',KITCHEN)
box('Oven handle',(a+60,744,718),(b-60,760,734),'Brushed steel',KITCHEN,bevel=4,segments=2)
box('Fixed black hob',(mid-290,190,902),(mid+290,590,914),'Oven glass',KITCHEN)
for dx in (-130,130):cylinder('Hob ring',(mid+dx,390,914),(mid+dx,390,916),80,'DOLLE PIPE black powdercoat',KITCHEN,verts=32)
# Anthracite single-bowl sink, a little toward the dishwasher, with a slim steel tap behind it.
a,b=X['sink'];sc=(a+b)/2-40
box('Sink steel rim',(sc-225,215,900),(sc+225,615,910),'Sink interior',KITCHEN,bevel=6,segments=2)
box('Sink bowl dark interior',(sc-200,240,909),(sc+200,590,911),'Sink interior',KITCHEN,bevel=0)
tx=sc-60;cylinder('Kitchen tap',(tx,110,900),(tx,110,1200),15,'Brushed steel',KITCHEN);cylinder('Kitchen tap spout',(tx,110,1185),(tx,290,1185),11,'Brushed steel',KITCHEN);cylinder('Kitchen tap spout',(tx,290,1185),(tx,290,1135),11,'Brushed steel',KITCHEN)
# Upper doors line up with the units below.
for k,_ in UNITS:a,b=X[k];box('Fixed upper white cabinet',(a+(17 if a==0 else 3),0,1530),(b-3,360,2310),FRONT,KITCHEN)
# Five KNAGGLIG crates on their long side: 460 along the run, 310 tall, 250 deep, bottom to the room.
drop('KNAGGLIG existing kitchen top');asset=bpy.data.collections['ASSET KNAGGLIG 70292359 460x310x250 mm'];tops=coll('20 Existing KNAGGLIG on the kitchen')
span=RUN-17;gap=(span-5*460)/6;turn=Matrix(((0,1,0,0),(0,0,-1,0),(-1,0,0,0),(0,0,0,1)))  # local length→x, width→z, open top→wall
for i in range(5):
 e=bpy.data.objects.new(f'KNAGGLIG existing kitchen top {i+1}',None);e.instance_type='COLLECTION';e.instance_collection=asset;tops.objects.link(e);e['existing']=True
 e.matrix_world=Matrix.Translation(Vector((17+gap+230+i*(460+gap),355,2310+155))/1000)@turn
# Room door: white frame, frameless 8 mm clear leaf on two patch hinges, clear transom above.
drop('Main room','Room door frame',collection=DOORS)
# Only a 30 mm strip of wall stays above the transom frame.
wall=bpy.data.objects['Room door transom'];bm=bmesh.new();bmesh.ops.create_cube(bm,size=1);bmesh.ops.scale(bm,vec=(.9,.1,.03),verts=bm.verts);bm.to_mesh(wall.data);bm.free();wall.location=(2.9,-.05,2.615);wall.rotation_euler=(0,0,0);wall.scale=(1,1,1)
L,R,TOP=2450,3350,2600
for x0,x1 in ((L,L+40),(R-40,R)):box('Room door frame jamb',(x0,-105,0),(x1,5,TOP),WHITE,DOORS)
box('Room door frame head',(L,-105,2105),(R,5,2160),WHITE,DOORS);box('Room door frame head',(L,-105,2560),(R,5,TOP),WHITE,DOORS)
glass=M['Balcony glazing']
box('Main room clear glass leaf closed',(L+44,-54,10),(R-44,-46,2102),glass,DOORS,bevel=1)
box('Main room transom glass',(L+40,-54,2160),(R-40,-46,2560),glass,DOORS,bevel=1)
for z in (250,1750):box('Main room door hinge patch',(R-100,-64,z),(R-44,-36,z+150),'Brushed steel',DOORS,bevel=3)
box('Main room door lock patch',(L+44,-64,960),(L+120,-36,1080),'Brushed steel',DOORS,bevel=3)
for y in (-64,-36):
 s=-1 if y<-50 else 1;cylinder('Main room door handle',(L+82,y,1020),(L+82,y+s*45,1020),9,'Brushed steel',DOORS);cylinder('Main room door handle',(L+82,y+s*45,1020),(L+200,y+s*45,1020),9,'Brushed steel',DOORS)
# DALFRED bar stools under the two pendants. Seat Ø300 at 740 (max), birch lacquered black,
# steel spindle and footrest ring, tripod legs spread to r 235. One leg points at the bar.
BLACK=M.get('DALFRED black lacquer') or M.new('DALFRED black lacquer');BLACK.use_nodes=True;p=BLACK.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(.025,.025,.027,1);p.inputs['Roughness'].default_value=.45
drop('DALFRED')
BAR_EDGE=2280;BED_NEAR=2620;RING_R,LEG_R=150,235
cy=BED_NEAR-RING_R-12  # the footrest ring is the first thing to reach the daybed's end board
for i,cx in enumerate((350,950)):
 n=f'DALFRED bar stool {i+1}'
 seat=cylinder(n+' seat',(cx,cy,700),(cx,cy,740),150,BLACK,KITCHEN,verts=40);mod=seat.modifiers.new('Bevel','BEVEL');mod.width=.008;mod.segments=3
 cylinder(n+' spindle',(cx,cy,540),(cx,cy,700),13,'Brushed steel',KITCHEN);cylinder(n+' hub',(cx,cy,470),(cx,cy,560),32,BLACK,KITCHEN)
 for k in range(3):
  a=math.radians(-90+120*k);d=Vector((math.cos(a),math.sin(a),0));top=Vector((cx,cy,520))+d*28;foot=Vector((cx,cy,0))+d*LEG_R;cylinder(n+' leg',top,foot,14,BLACK,KITCHEN,verts=16)
 # The footrest is a round steel tube: a curve with a bevel.
 cu=bpy.data.curves.new(n+' footrest','CURVE');cu.dimensions='3D';cu.bevel_depth=.008;cu.bevel_resolution=3;sp=cu.splines.new('POLY');sp.points.add(47)
 for j,pt in enumerate(sp.points):t=j/48*math.tau;pt.co=(RING_R/1000*math.cos(t),RING_R/1000*math.sin(t),0,1)
 sp.use_cyclic_u=True;o=bpy.data.objects.new(n+' footrest',cu);KITCHEN.objects.link(o);o.location=(cx/1000,cy/1000,.23);cu.materials.append(M['DOLLE PIPE black powdercoat'])
 # Keep it as a mesh, so the clearance checks see it like every other part.
 bpy.context.view_layer.update();me=bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()));me.name=n+' footrest'
 loc=o.location.copy();bpy.data.objects.remove(o,do_unlink=True);bpy.data.curves.remove(cu);o=bpy.data.objects.new(n+' footrest',me);KITCHEN.objects.link(o);o.location=loc
for o in KITCHEN.objects:
 if o.name.startswith('DALFRED'):o['stool']=int(o.name.split()[3])
bpy.context.scene['bar_stools_mm']={'bar_edge_y':BAR_EDGE,'seat_centre_y':cy,'ring_r':RING_R,'leg_r':LEG_R}
bpy.context.view_layer.update()
print('KITCHEN_UNITS',X,'STOOL_Y',cy,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(FILE))
print('KITCHEN_SAVED',flush=True)
