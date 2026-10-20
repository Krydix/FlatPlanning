"""Blender adapter for pipe_engine. Meshes are visual envelopes, not supplier CAD."""
import bpy,math,json,hashlib
from mathutils import Vector,Matrix
from pathlib import Path
MANAGED='13 V8 - component assembly'
def material(name,color,metal=0):
 m=bpy.data.materials.get(name)
 if m:return m
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.5;return m
def geometry_digest(o):
 if o.type=='MESH':value=([(round(v.co.x,7),round(v.co.y,7),round(v.co.z,7)) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])
 elif o.type=='CURVE':value=[tuple(round(x,7) for x in p.co) for sp in o.data.splines for p in sp.points]
 else:value=[]
 mods=[(m.type,getattr(m,'width',None),getattr(m,'segments',None)) for m in o.modifiers]
 return hashlib.sha256(repr((value,mods)).encode()).hexdigest()
def rebuild(a,collection=MANAGED):
 old=bpy.data.collections.get(collection)
 if old:
  for o in list(old.objects):bpy.data.objects.remove(o,do_unlink=True)
 else:
  old=bpy.data.collections.new(collection);bpy.context.scene.collection.children.link(old)
 co=old;black=material('DOLLE PIPE black powdercoat',(.018,.022,.025),.65);wood=bpy.data.materials.get('Oak for proposed furniture') or material('Oak',(.43,.24,.10));silver=material('Brushed steel',(.35,.4,.42),.8)
 cache={}
 def link(o):
  for c in list(o.users_collection):c.objects.unlink(o)
  co.objects.link(o);return o
 def cylinder(name,p,q,r,mat=black):
  p,q=Vector(p)/1000,Vector(q)/1000;v=q-p;bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=r/1000,depth=v.length,location=(p+q)/2);o=link(bpy.context.object);o.name=name;o.rotation_euler=v.to_track_quat('Z','Y').to_euler();o.data.materials.append(mat);return o
 def box(name,p,dim,mat=wood):
  bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(p)/1000);o=link(bpy.context.object);o.name=name;o.dimensions=Vector(dim)/1000;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);return o
 def boolean(o,c,operation='DIFFERENCE'):
  bpy.context.view_layer.objects.active=o;m=o.modifiers.new('Catalog body / bore','BOOLEAN');m.operation=operation;m.solver='EXACT';m.object=c;bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(c,do_unlink=True)
 def annulus(name,p,q,r,inner,mat=black):
  o=cylinder(name,p,q,r,mat);d=(Vector(q)-Vector(p)).normalized();c=cylinder('Bore',Vector(p)-d,Vector(q)+d,inner,mat);boolean(o,c);return o
 def group(root,objs):
  for o in objs:
   o.parent=root;o.matrix_parent_inverse=root.matrix_world.inverted();o['graph_child']=True
   o.lock_location=(True,True,True);o.lock_rotation=(True,True,True);o.lock_scale=(True,True,True)
  root['expected_matrix']=json.dumps([v for row in root.matrix_world for v in row]);root['mesh_digests']=json.dumps({o.name:geometry_digest(o) for o in objs});root['child_fingerprint']=json.dumps({o.name:([v for row in o.matrix_local for v in row],list(o.dimensions)) for o in objs})
  root.lock_location=(True,True,True);root.lock_rotation=(True,True,True);root.lock_scale=(True,True,True)
 # Use templates at origin, then transform all local geometry into assembly coordinates.
 for id,p in a.parts.items():
  root=bpy.data.objects.new(id,None);co.objects.link(root);root.location=Vector(p.origin)/1000;root['part_id']=id;root['catalog_kind']=p.kind;root['catalog_sku']=__import__('pipe_engine').CATALOG.get(p.kind,{}).get('sku','custom timber');root.empty_display_size=.025
  if p.kind in cache:
   if p.kind.startswith('tube_') or p.kind in ('flange','extension','cap'):rot=Vector(p.axis).to_track_quat('Z','Y').to_matrix()
   elif p.kind=='slide_tee':
    xx,zz=Vector(p.direction),Vector(p.axis);rot=Matrix((xx,zz.cross(xx),zz)).transposed()
   elif p.kind in ('end_holder','middle_holder'):rot=Matrix.Rotation(math.atan2(p.direction[1],p.direction[0])-math.pi/2,3,'Z')
   elif p.kind=='elbow':
    xx,yy=Vector(p.axis),Vector(p.direction);rot=Matrix((xx,yy,xx.cross(yy))).transposed()
   else:rot=Matrix.Identity(3)
   objs=[]
   for i,(data,matrix) in enumerate(cache[p.kind]):
    o=bpy.data.objects.new(id+' / body '+str(i+1),data);co.objects.link(o);o.matrix_world=Matrix.Translation(Vector(p.origin)/1000) @ rot.to_4x4() @ matrix;objs.append(o)
   bpy.context.view_layer.update();group(root,objs);continue
  objs=[];O=Vector((0,0,0));Z=Vector((0,0,1));X=Vector((1,0,0));Y=Vector((0,1,0));rot=Matrix.Identity(3)
  def c(n,v,w,r,ma=black):
   o=cylinder(id+' / '+n,v,w,r,ma);objs.append(o);return o
  def b(n,v,dim,ma=wood):
   o=box(id+' / '+n,v,dim,ma);objs.append(o);return o
  if p.kind.startswith('tube_'):
   L=p.data['length'];o=annulus(id+' / uncut tube',(0,0,0),(0,0,L),12.5,11);objs.append(o);rot=Vector(p.axis).to_track_quat('Z','Y').to_matrix()
  elif p.kind=='flange':
   o=c('Ø70 mounting disc',(0,0,0),(0,0,8),35);hub=cylinder('hub',(0,0,4),(0,0,a.v('flange_stop')+a.v('flange_engagement')),17);boolean(o,hub,'UNION');bore=cylinder('female socket',(0,0,a.v('flange_stop')),(0,0,40),12.6);boolean(o,bore)
   for angle in (0,math.tau/3,2*math.tau/3):
    v=(25*math.cos(angle),25*math.sin(angle));drill=cylinder('Mounting hole',(*v,-1),(*v,9),3);boolean(o,drill)
   rot=Vector(p.axis).to_track_quat('Z','Y').to_matrix()
  elif p.kind=='extension':
   rot=Vector(p.axis).to_track_quat('Z','Y').to_matrix()
   gap=a.v('extension_gap');end=gap/2+a.v('extension_engagement');o=annulus(id+' / female extension',(0,0,-end),(0,0,end),17,12.6);objs.append(o);stop=annulus(id+' / internal seating shoulder',(0,0,-gap/2),(0,0,gap/2),12.6,10.5);objs.append(stop)
  elif p.kind=='slide_tee':
   h=a.v('tee_half_height');r=a.v('tee_outer_radius');mouth=a.v('tee_stop')+a.v('tee_engagement');o=c('Sliding sleeve',(0,0,-h),(0,0,h),r);branch=cylinder('branch',(0,0,0),(mouth,0,0),17);boolean(o,branch,'UNION');bore=cylinder('through bore',(0,0,-h-1),(0,0,h+1),12.6);boolean(o,bore);bore=cylinder('female branch',(10,0,0),(mouth+1,0,0),12.6);boolean(o,bore)
   for zz in (-22,22):c('Set screw',(0,-17,zz),(0,-20,zz),3,silver)
   xx,zz=Vector(p.direction),Vector(p.axis);yy=zz.cross(xx);rot=Matrix((xx,yy,zz)).transposed()
  elif p.kind in ('end_holder','middle_holder'):
   h=a.v('holder_height');o=annulus(id+' / split collar',(0,0,-h/2),(0,0,h/2),18,12.6);objs.append(o)
   # Profile outline derived from overall listing envelope; holes/plate thickness need measuring.
   if p.kind=='end_holder':b('Shelf wing',(0,36.5, h/2-1.5),(85,73,3),black)
   else:b('Two shelf wings',(0,0,h/2-1.5),(65,90,3),black)
   # The open bore continues through the plate around the upright.
   wing=objs[-1];bore=cylinder('clearance',(0,0,-12),(0,0,12),12.6);boolean(wing,bore)
   c('Clamp screw',(17,0,0),(22,0,0),3,silver)
   # Default wing is +Y.
   rot=Matrix.Rotation(math.atan2(p.direction[1],p.direction[0])-math.pi/2,3,'Z')
  elif p.kind=='cap':
   c('End cover - fit pending',(0,0,0),(0,0,4),14);rot=Vector(p.axis).to_track_quat('Z','Y').to_matrix()
  elif p.kind=='elbow':
   e=a.v('elbow_stop')+a.v('elbow_engagement');o=c('90 degree body',(0,0,0),(e,0,0),17);branch=cylinder('second leg',(0,0,0),(0,e,0),17);boolean(o,branch,'UNION')
   for q in ((e+1,0,0),(0,e+1,0)):
    bore=cylinder('socket',(0,0,0),q,12.6);boolean(o,bore)
   # local X maps to p.axis; local Y to p.direction, local Z to cross.
   xx,yy=Vector(p.axis),Vector(p.direction);rot=Matrix((xx,yy,xx.cross(yy))).transposed()
  elif p.kind=='hook':
   # A U-shaped strap below a horizontal X-axis tube; two screw tabs meet wood underside.
   data=bpy.data.curves.new('Hook strap','CURVE');data.dimensions='3D';data.bevel_depth=.0015;data.bevel_resolution=2;sp=data.splines.new('POLY');pts=[(0,-25,12.5),(0,-14,12.5)]+[(0,14*math.cos(t),14*math.sin(t)) for t in [math.pi+i*math.pi/16 for i in range(17)]]+[(0,14,12.5),(0,25,12.5)];sp.points.add(len(pts)-1)
   for pt,v in zip(sp.points,pts):pt.co=(*[x/1000 for x in v],1)
   o=bpy.data.objects.new(id+' / hook strap',data);co.objects.link(o);o.data.materials.append(black);objs.append(o)
  elif p.kind=='saddle':
   # Axis X; one-sided tab follows +Y before mapping into the assembly.
   r=14;top=a.v('saddle_rise')-1.5;offset=a.v('saddle_tab_offset')
   points=[(0,-r,2)]+[(0,r*math.cos(t),r*math.sin(t)) for t in [math.pi+i*math.pi/20 for i in range(21)]]+[(0,r,top),(0,offset+8,top)]
   # Flat strap, 14 mm wide; open hook wraps beneath the horizontal pipe.
   angles=[math.pi+i*math.pi/24 for i in range(25)];verts=[]
   for xx in (-7,7):
    for rad in (12.5,15.5):
     for ang in angles:verts.append((xx/1000,rad*math.cos(ang)/1000,rad*math.sin(ang)/1000))
   n=len(angles);faces=[]
   for k in range(n-1):
    faces.extend([(k,k+1,n+k+1,n+k),(2*n+k,3*n+k,3*n+k+1,2*n+k+1),(k,2*n+k,2*n+k+1,k+1),(n+k,n+k+1,3*n+k+1,3*n+k)])
   faces.extend([(0,n,3*n,2*n),(n-1,2*n-1,4*n-1,3*n-1)])
   me=bpy.data.meshes.new('Flat saddle hook');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(id+' / curved saddle',me);co.objects.link(o);o.data.materials.append(black);objs.append(o)
   b('Vertical side',(0,r,top/2),(14,3,top),black)
   b('Screw tab',(0,(r+offset+8)/2,top),(14,offset+8-r,3),black)
   c('Wood screw',(0,offset,top-2),(0,offset,top+14),1.75,silver)
   yy=Vector(p.direction);zz=Vector((0,0,1));xx=yy.cross(zz);rot=Matrix((xx,yy,zz)).transposed()
  elif p.kind=='wood':
   rot=Matrix.Rotation(math.radians(p.data.get('rotation_degrees',0)),3,'Z')
   origin=Vector(p.origin);x0,x1,y0,y1=p.data['bounds'];bt=p.data['bottom'];th=p.data['thickness'];o=b('Oak cut board',(0,0,0),(x1-x0,y1-y0,th));origin=Vector(p.origin)
   for x,y,diam in p.data['holes']:
    pos=Vector((x,y,bt-th))-origin;q=Vector((x,y,bt+th*2))-origin;hole=cylinder('Post bore',pos,q,diam/2);boolean(o,hole)
   rc=p.data.get('recess')
   if rc:
    centre=Vector((rc['centre'][0],rc['centre'][1],bt+rc['depth']/2-.1))-origin;cut=box('OPEN UNDERSIDE POCKET',centre,(rc['width'],rc['length'],rc['depth']+.2));boolean(o,cut)
    # Widen both ends for the connector and clip/removal access (preview allowances).
    for sign in (-1,1):
     centre=Vector((rc['centre'][0],rc['centre'][1]+sign*(rc['length']/2-25),bt+rc['depth']/2-.1))-origin;cut=box('End access',centre,(50,50,rc['depth']+.2));boolean(o,cut)
   for rc in p.data.get('support_reliefs',[]):
    x0,x1,y0,y1,z0,z1=rc['bounds'];pos=Vector(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))-origin
    cut=box('Tee underside clearance',pos,(x1-x0,y1-y0,z1-z0));boolean(o,cut)
   bevel=o.modifiers.new('Soft timber edges','BEVEL');bevel.width=.0015;bevel.segments=2
  if p.kind not in ('wood','saddle'):cache[p.kind]=[(o.data,o.matrix_world.copy()) for o in objs]
  for o in objs:
   o.matrix_world=Matrix.Translation(Vector(p.origin)/1000) @ rot.to_4x4() @ o.matrix_world
  bpy.context.view_layer.update();group(root,objs)
 return co

def model_errors(a):
 errors=[]
 for id in a.parts:
  root=bpy.data.objects.get(id)
  if not root:errors.append(id+': component missing');continue
  expected=json.loads(root['expected_matrix']);actual=[v for row in root.matrix_world for v in row]
  if any(abs(x-y)>1e-6 for x,y in zip(expected,actual)):errors.append(id+': transform differs from graph')
  digests=json.loads(root.get('mesh_digests','{}'))
  saved=json.loads(root['child_fingerprint'])
  for name,(matrix,dims) in saved.items():
   o=bpy.data.objects.get(name)
   if not o:errors.append(name+': geometry missing');continue
   if digests.get(name)!=geometry_digest(o):errors.append(name+': mesh edited outside graph')
   values=[v for row in o.matrix_local for v in row]
   if any(abs(x-y)>1e-6 for x,y in zip(matrix,values)) or any(abs(x-y)>1e-6 for x,y in zip(dims,o.dimensions)):errors.append(name+': geometry transform changed')
 return errors
