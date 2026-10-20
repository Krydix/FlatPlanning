"""Export the locked model as static, UV-baked glTF. Run with Blender 5.2.
Lighting is baked from the practical night setup; the ceiling fixture stays OFF.
"""
import bpy,sys,json,math,struct,time
from types import SimpleNamespace
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'source/flat-v18.blend';OUT=ROOT/'public/models';OUT.mkdir(parents=True,exist_ok=True);LIGHTMAPS=ROOT/'source/lightmaps';LIGHTMAPS.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.context.scene;scene.frame_set(1)
SAMPLES=128
scene.render.engine='CYCLES';scene.cycles.device='GPU';scene.cycles.samples=SAMPLES
scene.cycles.seed=0;scene.cycles.max_bounces=12;scene.cycles.diffuse_bounces=6
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='METAL'
scene.cycles.use_denoising=True;scene.render.bake.margin=12;scene.render.bake.use_pass_direct=True;scene.render.bake.use_pass_indirect=True;scene.render.bake.use_pass_color=True;scene.render.bake.use_pass_emit=True;scene.render.bake.use_pass_glossy=False;scene.render.bake.use_pass_transmission=False
for o in bpy.data.objects:
 if o.type=='LIGHT' and 'ceiling' in o.name.lower():o.data.energy=0
light_records=[{'name':o.name,'type':o.data.type,'watts':o.data.energy,'color':list(o.data.color)} for o in scene.objects if o.type=='LIGHT' and not o.hide_render]
# Keep only scene-linked, render-visible objects; alternate bed and cutaway duplicates stay excluded.
allowed=set()
def visit(c,hidden=False):
 hidden=hidden or c.hide_render
 if not hidden:
  for o in c.objects:
   if not o.hide_render:allowed.add(o.original.name)
 for child in c.children:visit(child,hidden)
visit(scene.collection)
def category(o,inst):
 n=o.name;cols=[c.name for c in o.users_collection]
 if inst.is_instance and inst.parent and 'KNAGGLIG' in inst.parent.original.name:return 'crates'
 if any(c.startswith('01 ') for c in cols):
  if 'floor' in n.lower() or 'parquet' in n.lower():return 'floor'
  if any(k in n.lower() for k in ('exterior','partition','wall','pier')):return 'shell'
  return 'trim'
 if any(c.startswith('02 ') for c in cols):return 'kitchen'
 if any(c.startswith('04 ') for c in cols):return 'chair' if n.startswith('Chair') else 'equipment'
 if any(c.startswith('05 ') for c in cols):return 'bed'
 if any(c.startswith('07 ') for c in cols):return 'curtains' if 'curtain' in n.lower() else 'clothes'
 if any(c.startswith('08 ') for c in cols):return 'hall'
 if any(c.startswith('09 ') for c in cols):return 'ceiling'
 if any(c.startswith('10 ') for c in cols):return 'exterior'
 if any(c.startswith('12 ') for c in cols):return 'glass' if 'glass' in n.lower() else 'doors'
 if any(c.startswith('13 ') for c in cols):return 'wood' if o.parent and o.parent.get('catalog_kind')=='wood' else 'pipes'
 if any(c.startswith(('14 ','15 ')) for c in cols):return 'lighting'
 return 'misc'
# Export the graph geometry separately for the assembly viewer, preserving clean component IDs.
assembly=bpy.data.collections['13 V8 - component assembly']
bpy.ops.object.select_all(action='DESELECT')
for o in assembly.objects:
 for key in list(o.keys()):
  if key not in ('part_id','catalog_kind','catalog_sku'):del o[key]
 o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'assembly.glb'),export_format='GLB',use_selection=True,export_extras=True,export_cameras=False,export_lights=False,export_animations=False)
print('ASSEMBLY_EXPORTED',flush=True)
# Convert evaluated geometry, including the six collection-instance crates.
dg=bpy.context.evaluated_depsgraph_get();co=bpy.data.collections.new('WEB baked geometry');scene.collection.children.link(co);groups=defaultdict(list)
instances=[(v.object.original,v.matrix_world.copy(),bool(v.is_instance),v.parent.original if v.parent else None) for v in dg.object_instances]
for index,(orig,matrix,is_instance,parent) in enumerate(instances):
 inst=SimpleNamespace(is_instance=is_instance,parent=parent)
 if orig.type not in ('MESH','CURVE','SURFACE','FONT'):continue
 if inst.is_instance:
  if not inst.parent or inst.parent.original.name not in allowed:continue
 elif orig.name not in allowed:continue
 key=category(orig,inst)
 if key=='misc':continue
 try:me=bpy.data.meshes.new_from_object(orig.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
 except Exception:continue
 if not me.polygons:bpy.data.meshes.remove(me);continue
 # Preserve per-object generated texture coordinates through joining.
 mins=[min(v.co[i] for v in me.vertices) for i in range(3)];maxs=[max(v.co[i] for v in me.vertices) for i in range(3)]
 generated=me.attributes.new('orig_generated','FLOAT_VECTOR','POINT');objectcoords=me.attributes.new('orig_object','FLOAT_VECTOR','POINT')
 for v,g,a in zip(me.vertices,generated.data,objectcoords.data):
  g.vector=tuple((v.co[i]-mins[i])/(maxs[i]-mins[i]) if maxs[i]-mins[i]>1e-8 else .5 for i in range(3));a.vector=v.co
 o=bpy.data.objects.new('WEB_'+key+'_'+str(index),me);co.objects.link(o);o.matrix_world=matrix;groups[key].append(o)
for o in list(scene.objects):
 if o.type in ('MESH','CURVE','SURFACE','FONT') and o.name not in {v.name for values in groups.values() for v in values}:o.hide_render=True
print('GROUP_COUNTS',json.dumps({k:len(v) for k,v in groups.items()}),flush=True)
# Join within categories: small draw-call count with independent shell/ceiling visibility.
merged=[]
for key,objects in groups.items():
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name='flat_'+key;o['category']=key;merged.append(o)
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008,area_weight=.5,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
print('UV_READY',len(merged),flush=True)
# Give each atlas material independent nodes while preserving the procedural albedo.
records=[];prepared=[]
for o in merged:
 key=o['category'];size=4096 if key in ('floor','shell','wood') else 2048
 if key in ('trim','pipes','exterior','ceiling','glass'):size=1024
 image=bpy.data.images.new('baked_'+key,width=size,height=size,alpha=False);image.colorspace_settings.name='sRGB'
 copies={}
 for slot in o.material_slots:
  old=slot.material
  if not old:continue
  if old.name in copies:slot.material=copies[old.name];continue
  m=old.copy();m.name='BAKE '+key+' '+old.name;m.use_nodes=True;copies[old.name]=m;slot.material=m;nodes=m.node_tree.nodes;links=m.node_tree.links
  gen=nodes.new('ShaderNodeAttribute');gen.attribute_name='orig_generated';obj=nodes.new('ShaderNodeAttribute');obj.attribute_name='orig_object'
  for link in list(links):
   if link.from_node.bl_idname=='ShaderNodeTexCoord' and link.from_socket.name in ('Generated','Object'):
    if link.from_socket.name=='Object' and link.from_node.object:continue
    links.new(gen.outputs['Vector'] if link.from_socket.name=='Generated' else obj.outputs['Vector'],link.to_socket)
  for node in list(nodes):
   if node.bl_idname.startswith('ShaderNodeTex') and node.bl_idname not in ('ShaderNodeTexImage','ShaderNodeTexEnvironment','ShaderNodeTexCoord') and 'Vector' in node.inputs and not node.inputs['Vector'].is_linked:links.new(gen.outputs['Vector'],node.inputs['Vector'])
   if node.bl_idname=='ShaderNodeBsdfPrincipled':
    node.inputs['Metallic'].default_value=0;node.inputs['Roughness'].default_value=.8
    if 'Transmission Weight' in node.inputs:node.inputs['Transmission Weight'].default_value=0
  target=nodes.new('ShaderNodeTexImage');target.image=image;nodes.active=target;target.select=True
 prepared.append((o,image,key,size))
# Prepare all shaders before tracing any atlas; replace them only after every bake.
for o,image,key,size in prepared:
 # Bake with all other geometry present so occlusion and practical lighting are retained.
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 started=time.time();print('BAKE_START',key,size,flush=True)
 bpy.ops.object.bake(type='COMBINED',use_clear=True)
 image.filepath_raw=str(LIGHTMAPS/('baked-'+key+'.jpg'));image.file_format='JPEG';scene.render.image_settings.quality=94;image.save()
 records.append({'category':key,'atlas':size,'bake_seconds':round(time.time()-started,1),'vertices':len(o.data.vertices),'polygons':len(o.data.polygons)})
 print('BAKE_DONE',key,records[-1]['bake_seconds'],flush=True)
for o,image,key,size in prepared:
 # Replace the original shader with a single texture; mark it UNLIT in the glTF JSON below.
 m=bpy.data.materials.new('BAKED '+key);m.use_nodes=True;nodes=m.node_tree.nodes;shader=nodes.get('Principled BSDF');shader.inputs['Metallic'].default_value=0;shader.inputs['Roughness'].default_value=1
 tex=nodes.new('ShaderNodeTexImage');tex.image=image;m.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);o.data.materials.clear();o.data.materials.append(m)
 for face in o.data.polygons:face.material_index=0
# Avoid re-lighting already baked textures at runtime.
bpy.ops.object.select_all(action='DESELECT')
for o in merged:o.select_set(True)
file=OUT/'flat-baked.glb';bpy.ops.export_scene.gltf(filepath=str(file),export_format='GLB',use_selection=True,export_extras=True,export_cameras=False,export_lights=False,export_animations=False,export_image_format='JPEG',export_jpeg_quality=94)
data=file.read_bytes();length,kind=struct.unpack_from('<II',data,12);gltf=json.loads(data[20:20+length]);binary=data[20+length:]
used=set(gltf.get('extensionsUsed',[]));used.add('KHR_materials_unlit');gltf['extensionsUsed']=sorted(used)
for m in gltf.get('materials',[]):m.setdefault('extensions',{})['KHR_materials_unlit']={}
gltf.setdefault('asset',{})['extras']={'design':'V18 locked','lighting':'Baked practical lights; main ceiling light OFF','bake':f'Cycles combined diffuse/indirect/emission, {SAMPLES} samples, per-category UV atlases up to 4096px','geometry':'Approved model; connector profiles and structural load capacities remain unverified'}
encoded=json.dumps(gltf,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
file.write_bytes(struct.pack('<III',0x46546c67,2,12+8+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+binary)
manifest={'design':'V18','ceiling_light_on':False,'baked':True,'render_engine':'Cycles','samples':SAMPLES,'max_bounces':scene.cycles.max_bounces,'diffuse_bounces':scene.cycles.diffuse_bounces,'bake_type':'COMBINED','passes':['DIFFUSE','DIRECT','INDIRECT','EMIT','COLOR'],'view_independent':True,'max_atlas_size':4096,'baked_lights':light_records,'atlases':records,'model_bytes':file.stat().st_size,'mesh_count':len(merged),'lights_exported':False}
(ROOT/'public/data/bake-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('BAKE_COMPLETE',json.dumps(manifest),flush=True)
