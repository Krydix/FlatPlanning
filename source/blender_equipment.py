"""Under-desk equipment envelopes and separate adjustable-holder concepts."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
# Hand-placed objects from earlier versions that are now generated from equipment-layout.json.
REPLACED={'Audio interface','Computer keyboard','KRK monitor speaker reservation','KRK monitor speaker reservation.001','KRK tweeter','KRK tweeter.001','KRK yellow cone','KRK yellow cone.001','KRK dust cap','KRK dust cap.001'}

def rebuild_equipment(root):
 cfg=json.loads((root/'source/equipment-layout.json').read_text())
 co=bpy.data.collections['04 Equipment - measured envelopes pending']
 # Remove the old tabletop interface and previous generated equipment only.
 for o in list(co.objects):
  if o.name in REPLACED or o.get('service_equipment'):bpy.data.objects.remove(o,do_unlink=True)
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
 rubber=bpy.data.materials.get('Rubber and dark equipment') or black;cone=bpy.data.materials.get('KRK yellow cone') or mat('KRK yellow cone',(.9,.75,.05))
 powder=bpy.data.materials.get('DOLLE PIPE black powdercoat') or black
 for item in cfg['desk_items']:
  if item.get('static'):continue
  if 'pole' in item:
   # Desk-clamp VESA arm on the rear edge: top plate, spine, lower jaw, pole and a short link to the panel.
   x,y=item['pole'];r=item['pole_radius'];cx,cy=item['clamp'];top=732
   box('Monitor arm clamp plate',(x,y,top+4),(cx,cy,8),powder,1);box('Monitor arm clamp spine',(3410,y,(650+top+8)/2),(10,cy,top+8-650),powder,1);box('Monitor arm clamp jaw',(x+5,y,659),(cx-10,cy,18),powder,1)
   tube('Monitor arm pole',(x,y,top+8),(x,y,item['pole_top']),r,powder)
   monitor=next(d for d in cfg['desk_items'] if d['id'].startswith('Single'));back=monitor['location'][0]+monitor['size'][0]/2;z=monitor['location'][2]
   box('Monitor arm VESA link',((back+x-r)/2,y,z),(x-r-back,40,30),powder,1);box('Monitor arm VESA plate',(back+2.5,y,z),(5,item['vesa'],item['vesa']),powder,0)
   continue
  box(item['id'],item['location'],item['size'],powder,3)['space_status']=item['status']
 # Studio monitors stand on their trays, aimed at the seated ear reference and tilted by angled pads.
 sp=cfg['speakers'];depth,width,height=sp['size'];graph=json.loads((root/'source/assembly.json').read_text());parts={p['id']:p for p in graph['parts']}
 # Rear-outer-most mirrored position the tray, frame, wall and monitor allow (speaker_placement.py).
 from speaker_placement import speaker_layout
 layout=speaker_layout(root)
 for i,tray in enumerate(sp['trays']):
  b=graph['boards'][tray];(cx,cy),yaw=layout[i]['centre'],layout[i]['yaw'];base=b['bottom']+b['thickness']+sp['pad'];tx,ty,tz=parts[tray]['data']['speaker_target_mm']
  front=Vector((cx,cy,base))+Vector((math.cos(yaw),math.sin(yaw),0))*depth/2
  tilt=min(math.radians(sp['max_tilt_degrees']),max(0,math.atan2(base+sp['tweeter_above_base']-tz,(Vector((tx,ty,0))-front.xy.to_3d()).length)))
  # Local +X faces the listener; rotate about the front-bottom edge so the pad lifts the rear.
  frame=Matrix.Translation(Vector((cx,cy,base))/1000)@Matrix.Rotation(yaw,4,'Z')@Matrix.Translation((depth/2000,0,0))@Matrix.Rotation(tilt,4,'Y')@Matrix.Translation((-depth/2000,0,0))
  suffix='' if i==0 else '.001'
  def place(o):
   o.matrix_world=frame@o.matrix_basis;o['speaker_tilt_degrees']=round(math.degrees(tilt),2);o['speaker_tray']=tray;o['tray_offset_mm']=list(layout[i]['tray_offset']);return o
  o=box('KRK monitor speaker reservation'+suffix,(0,0,height/2),(depth,width,height),rubber,4);place(o);o['space_status']=sp['status']
  for name,z,radius,material,dz in (('KRK yellow cone',sp['woofer_above_base'],65,cone,2.5),('KRK dust cap',sp['woofer_above_base'],25,powder,4),('KRK tweeter',sp['tweeter_above_base'],26,powder,3.5)):
   place(tube(name+suffix,(depth/2,0,z),(depth/2+dz,0,z),radius,material))
  rise=depth*math.sin(tilt);verts=[(v[0]/1000,v[1]/1000,v[2]/1000) for v in ((-depth/2,-width/2,0),(depth/2,-width/2,0),(depth/2,width/2,0),(-depth/2,width/2,0),(-depth/2,-width/2,sp['pad']+rise),(depth/2,-width/2,sp['pad']),(depth/2,width/2,sp['pad']),(-depth/2,width/2,sp['pad']+rise))]
  me=bpy.data.meshes.new('Angled isolation pad');me.from_pydata(verts,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);me.update()
  pad=link(bpy.data.objects.new('Angled isolation pad'+suffix,me));pad.data.materials.append(rubber)
  pad.matrix_world=Matrix.Translation(Vector((cx,cy,base-sp['pad']))/1000)@Matrix.Rotation(yaw,4,'Z');pad['speaker_tilt_degrees']=round(math.degrees(tilt),2)
 # Cable paths hug the underside; their final bend radii are illustrative.
 for i,y in enumerate((1585,2660)):
  points=[(2853 if i==0 else 2803,y,657 if i==0 else 668),(2950,y,680),(3100,y,685),(3290+30*i,y,685),(3290+30*i,1740,538),(3290+30*i,1675,538)]
  for j,(p,q) in enumerate(zip(points,points[1:])):tube('Service loop / clipped cable',p,q,2)
 return cfg
