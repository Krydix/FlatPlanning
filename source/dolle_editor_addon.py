bl_info={'name':'DOLLE PIPE Connected Editor','author':'Weserstrasse design study','version':(0,18,0),'blender':(4,2,0),'location':'3D View > Sidebar > DOLLE PIPE','category':'Object','description':'Catalog-only pipe graph, compatible sockets and checked rail-height edits. Preview dimensions, not supplier CAD.'}
import bpy,json,sys,copy
from pathlib import Path
from . import pipe_engine as engine
sys.modules.setdefault('pipe_engine',engine)
from . import blender_components as drawing

def read():
 t=bpy.data.texts.get('Assembly-v8.json')
 if not t:raise engine.DesignError('No assembly graph in this file')
 d=json.loads(t.as_string());a=engine.Assembly(d['profile']);a.parts={p['id']:engine.Part(**p) for p in d['parts']};a.ports={p['id']:engine.Port(**p) for p in d['ports']}
 for k in ('edges','mounts','clamps','boards','lights','columns','notes'):setattr(a,k,d['connections' if k=='edges' else k])
 return a

def selected(context):
 o=context.object
 while o and not o.get('part_id'):o=o.parent
 return o.get('part_id') if o else None

def write(a):
 errors=drawing.model_errors(read())
 if errors:raise engine.DesignError('Geometry changed outside graph. Rebuild from graph before editing.')
 drawing.rebuild(a)
 path=Path(bpy.app.tempdir)/'dolle-connected-editor.json';a.save(path);bpy.data.texts['Assembly-v8.json'].clear();bpy.data.texts['Assembly-v8.json'].write(path.read_text());path.unlink(missing_ok=True)

def unique(a,base):
 i=1
 while base+str(i) in a.parts:i+=1
 return base+str(i)

def free_ports(self,context):
 try:
  a=read();id=selected(context);return [(p.id,p.id.split('.')[-1]+' / '+p.kind,'') for p in a.ports.values() if p.owner==id and not p.used] or [('NONE','No free port','Remove an end cover or select another part')]
 except:return [('NONE','No graph','')]

class DOLLE_Settings(bpy.types.PropertyGroup):
 socket:bpy.props.EnumProperty(name='Free port',items=free_ports)
 stock:bpy.props.EnumProperty(name='Uncut pipe',items=[(str(n),str(n)+' mm','') for n in engine.STOCK],default='250')
 connector:bpy.props.EnumProperty(name='Fitting',items=[('extension','Female–female extension 96445',''),('elbow','Female–female elbow 96353','')])
 height:bpy.props.FloatProperty(name='Height from floor (mm)',default=950,min=50,max=2400,precision=1)
 branch:bpy.props.EnumProperty(name='Branch direction',items=[('X','Toward wall (+X)',''),('-X','Toward room (-X)',''),('Y','Along room (+Y)',''),('-Y','Along room (-Y)','')],default='-X')
 seed_x:bpy.props.FloatProperty(name='New foot X (mm)',default=-1000)
 seed_y:bpy.props.FloatProperty(name='New foot Y (mm)',default=1000)

class DOLLE_Validate(bpy.types.Operator):
 bl_idname='dolle.validate';bl_label='Check connections and geometry'
 def execute(self,context):
  try:
   a=read();r=a.validate();err=r['geometry_errors']+drawing.model_errors(a);self.report({'WARNING'} if err else {'INFO'},'; '.join(err[:3]) if err else f'{len(a.parts)} components: connections pass. Dimensions still need calibration.');return {'FINISHED'}
  except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
class DOLLE_Rail(bpy.types.Operator):
 bl_idname='dolle.rail_height';bl_label='Set selected rail height';bl_options={'REGISTER','UNDO'}
 def execute(self,context):
  try:
   a=read();id=selected(context);a.move_rail(id,context.scene.dolle_settings.height);write(a);self.report({'INFO'},'Rail and both tees moved together; checks passed. Clothes are illustration and stay in place.');return {'FINISHED'}
  except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
class DOLLE_Uncap(bpy.types.Operator):
 bl_idname='dolle.uncap';bl_label='Remove selected end cover';bl_options={'REGISTER','UNDO'}
 def execute(self,context):
  try:
   a=read();id=selected(context)
   if a.parts[id].kind!='cap':raise engine.DesignError('Select an end cover')
   for p in a.ports.values():
    if p.used==id:p.used=None
   del a.parts[id];a.edges=[e for e in a.edges if e[1]!=id];write(a);return {'FINISHED'}
  except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
class DOLLE_Pipe(bpy.types.Operator):
 bl_idname='dolle.attach_pipe';bl_label='Attach stock pipe to free socket';bl_options={'REGISTER','UNDO'}
 def execute(self,context):
  try:
   a=read();s=context.scene.dolle_settings;id=unique(a,'Added.pipe');a.from_port(id,int(s.stock),s.socket);write(a);return {'FINISHED'}
  except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
class DOLLE_Fitting(bpy.types.Operator):
 bl_idname='dolle.attach_fitting';bl_label='Attach fitting to free pipe end';bl_options={'REGISTER','UNDO'}
 def execute(self,context):
  try:
   a=read();s=context.scene.dolle_settings;p=a.ports[s.socket]
   if p.kind!='male' or p.used:raise engine.DesignError('Select a free male tube end')
   id=unique(a,'Added.'+s.connector);n=p.n
   if s.connector=='extension':
    gap=a.v('extension_gap');a.part(id,'extension',engine.add(p.p,engine.mul(n,gap/2)),n,gap=gap);a.port(id+'.in',id,'female',p.p,engine.mul(n,-1));a.port(id+'.out',id,'female',engine.add(p.p,engine.mul(n,gap)),n)
   else:
    off=a.v('elbow_stop');centre=engine.add(p.p,engine.mul(n,off));d=(1,0,0) if abs(n[0])<.5 else (0,1,0);a.part(id,'elbow',centre,engine.mul(n,-1),d);a.port(id+'.in',id,'female',p.p,engine.mul(n,-1));a.port(id+'.out',id,'female',engine.add(centre,engine.mul(d,off)),d)
   a.connect(s.socket,id+'.in');write(a);return {'FINISHED'}
  except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
class DOLLE_Clamp(bpy.types.Operator):
 bl_idname='dolle.add_clamp';bl_label='Fit sliding tee on selected upright';bl_options={'REGISTER','UNDO'}
 def execute(self,context):
  try:
   a=read();s=context.scene.dolle_settings;id=selected(context);p=a.parts[id]
   if not p.kind.startswith('tube_') or tuple(p.axis)!=(0,0,1):raise engine.DesignError('Select a vertical Ø25 tube')
   col=unique(a,'Editor.column');a.columns[col]={'x':p.origin[0],'y':p.origin[1],'tubes':[id]};d={'X':(1,0,0),'-X':(-1,0,0),'Y':(0,1,0),'-Y':(0,-1,0)}[s.branch];a.clamp(unique(a,'Added.tee'),col,s.height,d);write(a);return {'FINISHED'}
  except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
class DOLLE_Seed(bpy.types.Operator):
 bl_idname='dolle.new_foot';bl_label='Start a new floor flange';bl_options={'REGISTER','UNDO'}
 def execute(self,context):
  try:
   a=read();s=context.scene.dolle_settings;a.flange(unique(a,'Added.foot'),(s.seed_x,s.seed_y,0),(0,0,1),'floor');write(a);return {'FINISHED'}
  except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
class DOLLE_Rebuild(bpy.types.Operator):
 bl_idname='dolle.rebuild';bl_label='Restore geometry from graph';bl_options={'REGISTER','UNDO'}
 def execute(self,context):
  try:drawing.rebuild(read());return {'FINISHED'}
  except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
class DOLLE_Export(bpy.types.Operator):
 bl_idname='dolle.export';bl_label='Update review BOM / checks'
 def execute(self,context):
  try:
   a=read();r=a.validate();r['blender_transform_errors']=drawing.model_errors(a);t=bpy.data.texts.get('CURRENT REVIEW BOM.json') or bpy.data.texts.new('CURRENT REVIEW BOM.json');t.clear();t.write(json.dumps({'status':'PLANNING ONLY','parts':dict(a.bom()),'validation':r},indent=2));self.report({'INFO'},'Updated CURRENT REVIEW BOM.json inside this file.');return {'FINISHED'}
  except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
class DOLLE_Fabrication(bpy.types.Operator):
 bl_idname='dolle.fabrication';bl_label='Check fabrication readiness'
 def execute(self,context):
  r=read().validate(fabrication=True);self.report({'ERROR'},'Not ready: '+ '; '.join(r['geometry_errors'][:3]));return {'CANCELLED'}
class DOLLE_Calibrate(bpy.types.Operator):
 bl_idname='dolle.calibrate';bl_label='Rebuild planned rack from measurements';bl_description='Replaces this assembly with the planned rack using Measurements-v8.json alongside the blend file; save custom edits first';bl_options={'REGISTER','UNDO'}
 def execute(self,context):
  try:
   path=Path(bpy.path.abspath('//Measurements-v8.json'))
   if not path.exists():raise engine.DesignError('Keep Measurements-v8.json beside the saved Blender file')
   a=engine.build(engine.profile_from_measurements(path),shared_desk=True);write(a);self.report({'INFO'},'Frame regenerated from measured/preview profile; unresolved items remain labelled.');return {'FINISHED'}
  except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
class DOLLE_Panel(bpy.types.Panel):
 bl_label='DOLLE PIPE / V8';bl_idname='VIEW3D_PT_dolle';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='DOLLE PIPE'
 def draw(self,context):
  l=self.layout;s=context.scene.dolle_settings;l.label(text='Preview fittings / measure before making',icon='INFO');l.operator('dolle.validate');l.operator('dolle.rebuild');l.separator();l.label(text='Adjust a rail with both sliding tees');l.prop(s,'height');l.operator('dolle.rail_height');l.separator();l.label(text='Connect catalog parts');l.prop(s,'socket');l.prop(s,'stock');l.operator('dolle.attach_pipe');l.prop(s,'connector');l.operator('dolle.attach_fitting');l.operator('dolle.uncap');l.prop(s,'branch');l.operator('dolle.add_clamp');l.separator();l.prop(s,'seed_x');l.prop(s,'seed_y');l.operator('dolle.new_foot');l.separator();l.operator('dolle.calibrate');l.operator('dolle.export');l.operator('dolle.fabrication')
CLASSES=[DOLLE_Settings,DOLLE_Validate,DOLLE_Rail,DOLLE_Uncap,DOLLE_Pipe,DOLLE_Fitting,DOLLE_Clamp,DOLLE_Seed,DOLLE_Rebuild,DOLLE_Export,DOLLE_Fabrication,DOLLE_Calibrate,DOLLE_Panel]
def register():
 for c in CLASSES:
  old=getattr(bpy.types,c.__name__,None)
  if old:
   try:bpy.utils.unregister_class(old)
   except:pass
  bpy.utils.register_class(c)
 bpy.types.Scene.dolle_settings=bpy.props.PointerProperty(type=DOLLE_Settings)
def unregister():
 if hasattr(bpy.types.Scene,'dolle_settings'):del bpy.types.Scene.dolle_settings
 for c in reversed(CLASSES):
  try:bpy.utils.unregister_class(c)
  except:pass
