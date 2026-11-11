"""Replace the V18 bed with an IKEA GLAMBERGET daybed (pull-out, 2 x ÅGOTNES 80 x 200).
Run with Blender in background mode; it rewrites source/flat-v18.blend. Rebuild the portal
variant afterwards, because it is derived from this file.

IKEA lists 211 cm long, 35 cm high, 87 cm closed and 163 cm extended. Board sizes, the pull-out
stroke and the lift are read from product photos, not from assembly instructions. The model's
extended width is a little over IKEA's 163 cm because its front rail sits between the mattresses.

The bed is built in the daybed pose. Parts carry `bed_part` so the bake can split them:
  fixed     frame, slats, upper mattress and throw (one atlas)
  pullout   lower frame, mattress and drawer fronts; baked extended
  legs      fold-down legs; they follow the pull-out sideways but stay on the floor
  cushion   five back cushions, each its own node so the viewer can drop them in one by one
The scene stores the motion as `bed_extend_m` = (sideways stroke, lift) in metres.
"""
import bpy,bmesh,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent.parent
FILE=ROOT/'source/flat-v18.blend'
bpy.ops.wm.open_mainfile(filepath=str(FILE))
# Origin: x along the room from the left wall, y toward the balcony, z up (all mm, converted below).
X0,Y0=30,2620          # clear of the 27 mm skirting; same near edge as the old bed
LENGTH,DEPTH=2110,870
STROKE,LIFT=825,170    # pull-out travel and how far it rises to meet the fixed mattress
old=next(c for c in bpy.data.collections if c.name.startswith('05 '))
for o in list(old.all_objects):bpy.data.objects.remove(o,do_unlink=True)
old.name='05 Bed - GLAMBERGET daybed'
for m in list(bpy.data.meshes):
 if not m.users:bpy.data.meshes.remove(m)
def material(name,color,checker=None,rough=.85):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear()
 out=nt.nodes.new('ShaderNodeOutputMaterial');bsdf=nt.nodes.new('ShaderNodeBsdfPrincipled');bsdf.inputs['Roughness'].default_value=rough;nt.links.new(bsdf.outputs[0],out.inputs[0])
 if 'Sheen Weight' in bsdf.inputs:bsdf.inputs['Sheen Weight'].default_value=.3
 if checker:
  # A small woven check, like the black-and-white cushions in the IKEA photos.
  co=nt.nodes.new('ShaderNodeTexCoord');tex=nt.nodes.new('ShaderNodeTexChecker');tex.inputs['Scale'].default_value=checker[2]
  tex.inputs['Color1'].default_value=(*checker[0],1);tex.inputs['Color2'].default_value=(*checker[1],1);nt.links.new(co.outputs['Object'],tex.inputs['Vector']);nt.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
 else:bsdf.inputs['Base Color'].default_value=(*color,1)
 return m
PINE=bpy.data.materials['KNAGGLIG untreated pale pine']
MATTRESS=material('ÅGOTNES mattress cover',(.42,.47,.53))
OAT=material('Daybed cushion oat linen',(.62,.57,.48))
CHECK=material('Daybed cushion woven check',None,checker=((.035,.035,.035),(.72,.70,.66),32))
PETROL=bpy.data.materials['Petrol textile'];THROW=bpy.data.materials['Bed throw rust'];DARK=material('GLAMBERGET handle recess',(.03,.025,.02))
def add(name,lo,hi,mat,part,bevel=3,segments=1):
 """Box from local mm corners; local x runs out from the wall, y along it."""
 lo=Vector(lo);hi=Vector(hi);size=(hi-lo)/1000;mid=(Vector((X0,Y0,0))+(lo+hi)/2)/1000
 me=bpy.data.meshes.new(name);bm=bmesh.new();bmesh.ops.create_cube(bm,size=1);bmesh.ops.scale(bm,vec=size,verts=bm.verts);bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);old.objects.link(o);o.location=mid;me.materials.append(mat);o['bed_part']=part
 if bevel:mod=o.modifiers.new('Bevel','BEVEL');mod.width=bevel/1000;mod.segments=segments;mod.limit_method='ANGLE'
 return o
def cushion(name,centre,size,tilt,mat,index):
 """Rounded, slightly puffed box leaning back toward the wall by `tilt` degrees."""
 w,h,t=(v/1000 for v in size);me=bpy.data.meshes.new(name);bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
 bmesh.ops.subdivide_edges(bm,edges=bm.edges[:],cuts=6,use_grid_fill=True)
 for v in bm.verts:
  x,y,z=v.co.x*2,v.co.y*2,v.co.z*2  # -1..1 across thickness, width, height
  puff=1-.55*max(abs(y),abs(z))**4    # full in the middle, pinched at the seams
  v.co=Vector((x*t/2*puff,y*w/2,z*h/2))
 bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);old.objects.link(o);me.materials.append(mat);o['bed_part']='cushion';o['cushion_index']=index
 o.location=(Vector((X0,Y0,0))+Vector(centre))/1000;o.rotation_euler=(0,math.radians(-tilt),0)
 mod=o.modifiers.new('Subdivision','SUBSURF');mod.levels=mod.render_levels=2
 for p in me.polygons:p.use_smooth=True
 return o
# Fixed unit: corner posts, end and back boards, front rail, cleats, slats, mattress.
for x in (0,800):
 for y in (0,LENGTH-55):add('GLAMBERGET post',(x,y,0),(x+70,y+55,345),PINE,'fixed',bevel=5)
for y in (5,LENGTH-45):
 add('GLAMBERGET end board',(70,y,40),(800,y+40,185),PINE,'fixed');add('GLAMBERGET end board',(70,y,195),(800,y+40,340),PINE,'fixed')
add('GLAMBERGET back board',(5,55,40),(35,LENGTH-55,185),PINE,'fixed');add('GLAMBERGET back board',(0,55,195),(35,LENGTH-55,340),PINE,'fixed')
add('GLAMBERGET front rail',(835,55,235),(870,LENGTH-55,345),PINE,'fixed',bevel=4)
add('GLAMBERGET slat cleat',(35,55,250),(55,LENGTH-55,270),PINE,'fixed',bevel=1);add('GLAMBERGET slat cleat',(815,55,250),(835,LENGTH-55,270),PINE,'fixed',bevel=1)
for i in range(19):
 y=70+i*(LENGTH-200)/18;add('GLAMBERGET slat',(35,y,270),(835,y+60,288),PINE,'fixed',bevel=1)
add('ÅGOTNES mattress',(37,57,290),(833,LENGTH-57,390),MATTRESS,'fixed',bevel=22,segments=4)
add('Folded rust throw',(60,1600,388),(815,1990,418),THROW,'fixed',bevel=10,segments=3)
# Pull-out, closed: it sits under the slats and below the front rail.
for y in (65,LENGTH-90):add('GLAMBERGET pull-out side',(50,y,30),(835,y+25,120),PINE,'pullout')
add('GLAMBERGET pull-out back',(50,90,30),(75,LENGTH-90,120),PINE,'pullout')
for i in range(15):
 y=100+i*(LENGTH-260)/14;add('GLAMBERGET pull-out slat',(75,y,100),(835,y+60,118),PINE,'pullout',bevel=1)
add('ÅGOTNES mattress pull-out',(45,75,120),(825,LENGTH-75,220),MATTRESS,'pullout',bevel=22,segments=4)
half=(LENGTH-130)/2
for k,(a,b) in enumerate(((65,65+half-5),(65+half+5,LENGTH-65))):
 add('GLAMBERGET drawer front',(835,a,15),(867,b,212),PINE,'pullout',bevel=4)
 c=(a+b)/2;add('GLAMBERGET drawer grip',(864,c-70,150),(868,c+70,178),DARK,'pullout',bevel=6,segments=3)
# Fold-down legs, drawn standing: when raised the pull-out rests on them.
for x in (60,790):
 for y in (110,LENGTH-160):add('GLAMBERGET pull-out leg',(x,y,0),(x+45,y+50,LIFT+30),PINE,'legs',bevel=3)
# Daybed cushions: three large ones against the wall, two smaller in front, like the IKEA set.
top=390;back=[(410,OAT),(1055,CHECK),(1700,OAT)]
for i,(y,mat) in enumerate(back):cushion('Daybed back cushion',(112,y,top+268),(650,560,190),12,mat,i)
for i,(y,mat) in enumerate(((720,CHECK),(1420,PETROL))):cushion('Daybed accent cushion',(285,y,top+205),(450,430,150),19,mat,3+i)
bpy.context.scene['bed_extend_m']=[STROKE/1000,LIFT/1000]
bpy.context.view_layer.update()
print('BED_PARTS',{p:sum(1 for o in old.objects if o.get('bed_part')==p) for p in ('fixed','pullout','legs','cushion')},flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(FILE))
print('BED_SAVED',flush=True)
