"""Under-desk equipment envelopes and separate adjustable-holder concepts."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector

def rebuild_equipment(root):
 cfg=json.loads((root/'source/equipment-layout.json').read_text())
 co=bpy.data.collections['04 Equipment - measured envelopes pending']
 # Remove the old tabletop interface and previous generated equipment only.
 for o in list(co.objects):
  if o.name=='Audio interface' or o.get('service_equipment'):bpy.data.objects.remove(o,do_unlink=True)
 def mat(name,color,metal=0):
  m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
  n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=.45;return m
 black=mat('Service equipment matte black',(.025,.029,.035));silver=mat('Mac mini aluminium',(.43,.46,.50),.7);red=mat('Focusrite red shell',(.40,.013,.022),.5)
 def link(o):
  for c in list(o.users_collection):c.objects.unlink(o)
  co.objects.link(o);o['service_equipment']=True;return o
 def box(name,centre,size,material,bevel=1):
  bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(centre)/1000);o=link(bpy.context.object);o.name=name;o.dimensions=Vector(size)/1000;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material)
  if bevel:
   m=o.modifiers.new('Rounded enclosure','BEVEL');m.width=bevel/1000;m.segments=3
  return o
 def tube(name,p,q,r,material=black):
  p=Vector(p)/1000;q=Vector(q)/1000;v=q-p;bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=r/1000,depth=v.length,location=(p+q)/2);o=link(bpy.context.object);o.name=name;o.rotation_euler=v.to_track_quat('Z','Y').to_euler();o.data.materials.append(material);return o
 for d in cfg['devices']:
  id=d['id'];size=d['size'];loc=d['location']
  # Holder dimensions are a conservative clearance; the visible device is smaller.
  if id.startswith('Mac'):size=[197,197,33];loc=[3290,1575,537.5]
  if id.startswith('Focusrite'):size=[140,200,55];loc=[2783,1585,657.5]
  if id.startswith('OWC'):size=[90,230,28];loc=[2758,2660,668]
  o=box(id,loc,size,silver if id.startswith('Mac') else red if id.startswith('Focusrite') else black,5 if id.startswith('Mac') else 2);o['space_status']=d['status']
  x,y,z=loc;dx,dy,dz=size
  if id.startswith(('Focusrite','OWC')):
   box(id+' front panel',(x-dx/2-.5,y,z),(2,dy-4,dz-4),black)
   if id.startswith('Focusrite'):
    for yy in (y-70,y-25):tube('Focusrite input',(x-dx/2-3,yy,z),(x-dx/2-6,yy,z),9)
    for yy in (y+20,y+65):tube('Focusrite accessible knob',(x-dx/2-2,yy,z),(x-dx/2-8,yy,z),7)
   else:
    for yy in (y-75,y-40,y+10,y+70):box('OWC accessible port',(x-dx/2-2,yy,z),(3,12,5),silver,0)
  if id.startswith('Mac'):
   tube('Mac mini native base envelope',(x,y,518),(x,y,521),78)
   box('Mac mini rear ports along shelf',(x,y+99,z),(140,2,16),black)
  if id.startswith('Router'):
   for yy in (y-90,y+90):tube('Router illustrative antenna',(x+40,yy,z+20),(x+40,yy,680),3)
  if id.startswith('Power brick'):
   box('Individual removable brick strap',(x,y,z+dz/2+1),(dx+4,10,2),black,0)
 for holder in cfg['mounts']:
  x0,x1,y0,y1=holder['bounds'];z=holder['base_z'];top=holder['upper_z']
  # Two U saddles, at different depths, leave both port faces unobstructed.
  for x in (x0+28,x1-28):
   box(holder['id']+' base',(x,(y0+y1)/2,z+1.5),(18,y1-y0,3),black,0)
   for y,sign in ((y0,1),(y1,-1)):
    box(holder['id']+' side',(x,y+sign*1.5,(z+top)/2),(18,3,top-z),black,0)
    box(holder['id']+' fixing lip',(x,y+sign*10,top-1.5),(18,20,3),black,0)
    tube('Holder short screw to verify',(x,y+sign*11,top-3),(x,y+sign*11,top+12),1.5)
 # Cable paths hug the underside; their final bend radii are illustrative.
 for i,y in enumerate((1585,2660)):
  points=[(2853 if i==0 else 2803,y,657 if i==0 else 668),(2950,y,680),(3100,y,685),(3290+30*i,y,685),(3290+30*i,1740,538),(3290+30*i,1675,538)]
  for j,(p,q) in enumerate(zip(points,points[1:])):tube('Service loop / clipped cable',p,q,2)
 return cfg
