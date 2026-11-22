"""Rebuild the connected desk joints from the graph; run in Blender background."""
import bpy,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'source'))
from pipe_engine import build,profile_from_measurements
from blender_components import rebuild,model_errors
from blender_equipment import rebuild_equipment,REPLACED
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
a=build(profile_from_measurements(ROOT/'source/Measurements-v8.json'),shared_desk=True);assert not a.validate()['geometry_errors'];a.save(ROOT/'source/assembly.json')
# Under-bed boxes are resized below; everything else outside the graph must stay exactly where it was.
def underbed(o):return o.name.startswith(('Crate slat','Crate end slat')) and any(c.name.startswith('05 ') for c in o.users_collection)
# Scene items that sit on the frame (lights, light covers, clothes, crates, speaker pads) follow their shelf or rail.
# Each remembers the level it was last placed for, so the script can be rerun. First-run values are the sliding-T V18 heights.
B=a.boards;RAIL=sorted({q.origin[2] for id,q in a.parts.items() if id.startswith('Rack.clean0') and id.endswith('.tube') and abs(q.axis[1])>.9})
NOW={'shelf0':B['Desk.shelf0']['bottom'],'shelf1':B['Desk.shelf1']['bottom'],'top':B['Rack.top0']['bottom'],'tray':B['Speaker0.platform']['bottom'],'shoe':B['Rack.coat_shoes']['bottom'],
 'rail_upper':RAIL[-1],'rail_lower':RAIL[0],'wear':a.parts['Wear.rail'].origin[2],**{f'fold{k}':B[f'Rack.fold{k}']['bottom'] for k in range(4)}}
NOW_X={'rail_lower':a.parts[f'Rack.clean0.{RAIL[0]:g}.tube'].origin[0],'wear':a.parts['Wear.rail'].origin[0]}
WAS={'shelf0':1540,'shelf1':1880,'top':2190,'tray':1100,'shoe':200,'rail_upper':1950,'rail_lower':950,'wear':1250,'fold0':700,'fold1':1100,'fold2':1500,'fold3':1850};WAS_X={'rail_lower':3085,'wear':2925}
LENGTH={id:B[id]['bounds'][3]-B[id]['bounds'][2] for id in ('Desk.shelf1','Desk.shelf2','Rack.top0','Rack.top1','Rack.top2')};LENGTH_WAS={'Desk.shelf1':1554,'Desk.shelf2':1554,'Rack.top0':1004,'Rack.top1':606,'Rack.top2':606}
def box_of(o):
 pts=[o.matrix_world@Vector(c) for c in o.bound_box] if o.type in ('MESH','CURVE') else [o.matrix_world.translation.copy()]
 return [(min(q[i] for q in pts)*1000,max(q[i] for q in pts)*1000) for i in range(3)]
def seat_key(o):
 col=next((c.name[:2] for c in o.users_collection),'');n=o.name;low=n.lower();(x0,x1),(y0,y1),(z0,z1)=box_of(o)
 if x1<2900 or y1<1200:return None
 if col in ('14','15'):
  if n.startswith('Desk.shelf1') or 'TRADFRI 603.426.56 - accessible' in n:return 'shelf1'
  if n.startswith(('Desk.shelf2','Rack.top','V9 TRADFRI')):return 'top'
  if 'MITTLED' in n or 'Light clip screw' in n or 'VAGDAL' in n:return 'shelf0'
 if col=='18' and n.startswith('KNAGGLIG Top'):return 'top'
 if col=='04' and 'thin isolation pad' in n:return 'tray'
 if col=='07':
  if 'pullover' in low:return 'fold'+str(max(k for k in range(4) if WAS[f'fold{k}']+28<=z0+6))
  if 'wear' in low:return 'wear'
  if any(w in low for w in ('shoe','sole','boot')):return 'shoe'
  yc=(y0+y1)/2;zc=(z0+z1)/2
  if 3940<yc<4560:return 'wear'
  return 'rail_upper' if yc>4560 or zc>1000 else 'rail_lower'
 return None
from mathutils import Vector
seated=[]
for o in bpy.context.scene.objects:
 if o.parent or any(c.name.startswith('13 ') for c in o.users_collection) or o.get('service_equipment'):continue
 if 'seat_key' not in o:
  key=seat_key(o)
  if not key:continue
  o['seat_key']=key;o['seat_z']=WAS[key]
  if key in WAS_X:o['seat_x']=WAS_X[key]
  board=next((id for id in LENGTH if o.name.startswith(id)),None)
  if board and any(w in o.name for w in ('light lip','glare return','end cheek')):o['seat_board']=board;o['seat_len']=LENGTH_WAS[board]
 seated.append(o.name)
fixed={o.name:tuple(v for row in o.matrix_world for v in row) for o in bpy.context.scene.objects if o.name not in REPLACED and o.name not in seated and not o.get('service_equipment') and not underbed(o) and not any(c.name.startswith('13 ') for c in o.users_collection)}
for name in seated:
 o=bpy.data.objects[name];key=o['seat_key'];o.location.z+=(NOW[key]-o['seat_z'])/1000;o['seat_z']=NOW[key]
 if key in NOW_X:o.location.x+=(NOW_X[key]-o['seat_x'])/1000;o['seat_x']=NOW_X[key]
 if 'seat_board' in o:
  # Light covers follow their board's length: lips and glare returns stretch, end cheeks move in with the board ends.
  board=o['seat_board'];new=LENGTH[board];old=o['seat_len'];centre=(B[board]['bounds'][2]+B[board]['bounds'][3])/2000
  if 'end cheek' in o.name:o.location.y=centre+(o.location.y-centre)*new/old
  else:o.scale.y*=new/old;o.location.y=centre+(o.location.y-centre)*new/old
  o['seat_len']=new
rebuild(a);rebuild_equipment(ROOT);assert not model_errors(a),model_errors(a)
assert all(tuple(v for row in bpy.data.objects[name].matrix_world for v in row)==matrix for name,matrix in fixed.items())
# Under-bed boxes slide out beneath the 250 mm side beam: three 40 mm slat rows, top 230 mm incl. casters.
ROWS=((.100,.095),(.165,.1525),(.230,.210))
for o in bpy.data.objects:
 if not underbed(o):continue
 old,new=min(ROWS,key=lambda r:min(abs(o.location.z-r[0]),abs(o.location.z-r[1])))
 zs=[v.co.z for v in o.data.vertices];o.location.z=new;o.scale.z=.040/(max(zs)-min(zs))
for o in bpy.data.objects:
 if o.type=='LIGHT' and 'ceiling' in o.name.lower():o.data.energy=0
for t in bpy.data.texts:
 if t.name.startswith('Assembly'):t.clear();t.write((ROOT/'source/assembly.json').read_text())
bpy.context.scene['desk_joint_revision']='All-threaded frame: fixed Ts, desk-height crosses, boards on capped arms, rounded entrance corner, ear-aimed speakers'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
print('JOINTS_REBUILT',len(a.parts),flush=True)
