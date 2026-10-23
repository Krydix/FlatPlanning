"""Room clearance and clash report from the locked Blender model; run in Blender background.
Writes public/data/clearances.json. Distances are model distances in mm: they are only as true
as source/room-measurements.json and the equipment envelopes, and each check records its basis.
"""
import bpy,sys,json,math
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT/'source'))
from pipe_engine import room_geometry,EAR_MM
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'));scene=bpy.context.scene;scene.frame_set(1)
ROOM=json.loads((ROOT/'source/room-measurements.json').read_text());GEO=room_geometry();TARGET=ROOM['clearance_targets']
EQUIPMENT=json.loads((ROOT/'source/equipment-layout.json').read_text())
dg=bpy.context.evaluated_depsgraph_get()
def collections(o):return [c.name for c in o.users_collection]
def rendered(o):
 if o.type!='MESH' or o.hide_render:return False
 return not any(c.startswith(('06 ','11 ','ASSET')) for c in collections(o))
OBJECTS=[o for o in scene.objects if rendered(o)]
cache={}
def world(o):
 # Evaluated (bevelled/booleaned) geometry in millimetres.
 if o.name not in cache:
  e=o.evaluated_get(dg);me=e.to_mesh();m=o.matrix_world
  cache[o.name]=([(m@v.co)*1000 for v in me.vertices],[tuple(p.vertices) for p in me.polygons]);e.to_mesh_clear()
 return cache[o.name]
def bounds(objs):
 pts=[v for o in objs for v in world(o)[0]];return [min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]
def tree(objs,inset=.5):
 # A small inset keeps resting contact (keyboard on desk, pad on tray) from counting as a clash.
 verts=[];polys=[]
 for o in objs:
  vs,ps=world(o);lo=[min(v[i] for v in vs) for i in range(3)];hi=[max(v[i] for v in vs) for i in range(3)];c=[(lo[i]+hi[i])/2 for i in range(3)]
  k=[max(0,(hi[i]-lo[i])-2*inset)/(hi[i]-lo[i]) if hi[i]-lo[i]>1e-6 else 1 for i in range(3)]
  base=len(verts);verts+=[Vector(tuple(c[i]+(v[i]-c[i])*k[i] for i in range(3))) for v in vs];polys+=[tuple(base+j for j in p) for p in ps]
 return BVHTree.FromPolygons(verts,polys) if polys else None
def boxes_overlap(a,b,pad=0):return all(a[0][i]-pad<=b[1][i] and b[0][i]-pad<=a[1][i] for i in range(3))
checks=[]
def report(id,label,value,target,status,detail,basis,unit='mm',points=None):
 checks.append({'id':id,'label':label,'value':round(value,1) if value is not None else None,'target':target,'unit':unit,'status':status,'detail':detail,'basis':basis,**({'points':[[round(c,1) for c in p] for p in points]} if points else {})})
def named(*prefixes,collection=None):return [o for o in OBJECTS if o.name.startswith(prefixes) and (collection is None or any(c.startswith(collection) for c in collections(o)))]
assembly=[o for o in OBJECTS if any(c.startswith('13 ') for c in collections(o))]
def part(o):
 p=o.parent
 while p and not p.get('part_id'):p=p.parent
 return p.get('part_id') if p else o.name
# 1. Architecture agrees with the room file.
right=named('Right exterior')[0];wall=bounds([right])[0][0];ceiling=bounds(named('Ceiling slab','Ceiling - assumed',collection='09 '))[0][2]
for id,label,model,value,measured in (('wall','Right wall plane vs room file',wall,GEO['wall_x'],GEO['wall_measured']),('ceiling','Ceiling plane vs room file',ceiling,GEO['ceiling'],GEO['ceiling_measured'])):
 delta=abs(model-value);report('architecture-'+id,label,delta,5,'clash' if delta>5 else 'ok',f'Model {model:.0f} mm, room file {value:.0f} mm'+('' if measured else ' (assumed)'),'measured' if measured else 'assumed')
# 2. Entrance pinch: kitchen worktop corner to anything new between 100 and 1,800 mm height.
kitchen=bounds(named('Kitchen worktop'));kx,ky=kitchen[1][0],kitchen[1][1];best=(1e9,None,None)
for o in assembly+named('Chair',collection='04 '):
 for v in world(o)[0]:
  if 100<=v.z<=1800 and v.x>kx-1 and v.y>ky-1:
   d=math.hypot(max(0,v.x-kx),max(0,v.y-ky))
   if d<best[0]:best=(d,part(o),v.copy())
floor=min((math.hypot(max(0,v.x-kx),max(0,v.y-ky)),part(o)) for o in assembly for v in world(o)[0] if v.z<100 and v.x>kx-1 and v.y>ky-1)
status='clash' if best[0]<TARGET['entry_passage_min'] else 'tight' if best[0]<TARGET['entry_passage_comfortable'] else 'ok'
report('entry-passage','Entrance passage, kitchen corner to desk',best[0],TARGET['entry_passage_min'],status,f'Nearest: {best[1]}. At floor level the nearest is {floor[1]} at {floor[0]:.0f} mm. Comfortable two-way passage is about {TARGET["entry_passage_comfortable"]} mm.','assumed' if not GEO['wall_measured'] else 'measured',points=[(kx,ky,best[2].z),tuple(best[2])])
# 3. Equipment must not intersect each other or the frame (resting contact allowed).
groups=defaultdict(list)
for o in OBJECTS:
 cols=collections(o)
 if any(c.startswith('04 ') for c in cols):
  n=o.name
  key=('Chair' if n.startswith('Chair') else 'Computer keyboard' if n.startswith('Computer keyboard') else 'MIDI controller' if n.startswith(('Komplete','MIDI')) else
   'Monitor' if n.startswith(('Single 28','Dark monitor','Monitor arm')) else ('Speaker R' if n.endswith('.001') else 'Speaker L') if n.startswith(('KRK','Angled isolation')) else
   'Mac mini' if n.startswith('Mac') else 'Router' if n.startswith('Router') else 'Focusrite' if n.startswith('Focusrite') else 'OWC dock' if n.startswith(('OWC','owc')) and 'holder' not in n.lower() else
   'Power bricks' if n.startswith(('Power brick','Individual removable')) else None)
  if key:groups[key].append(o)
trees={k:tree(v) for k,v in groups.items()};boxes={k:bounds(v) for k,v in groups.items()};clashes=[]
names=sorted(groups)
for i,a in enumerate(names):
 for b in names[i+1:]:
  if boxes_overlap(boxes[a],boxes[b]) and trees[a].overlap(trees[b]):clashes.append(f'{a} / {b}')
frame=defaultdict(list)
for o in assembly:frame[part(o)].append(o)
for a in names:
 if a=='Chair':continue
 for pid,objs in frame.items():
  bb=bounds(objs)
  if boxes_overlap(boxes[a],bb) and trees[a].overlap(tree(objs)):clashes.append(f'{a} / {pid}')
report('equipment-clashes','Desk equipment intersections',len(clashes),0,'clash' if clashes else 'ok','; '.join(clashes) or 'No equipment envelope intersects another device, the desk or the frame.','envelopes','count')
kb=boxes['Computer keyboard'];midi=bounds([o for o in groups['MIDI controller'] if o.name.startswith('Komplete')])
report('keyboard-midi','Computer keyboard to MIDI controller',midi[0][0]-kb[1][0],10,'ok' if midi[0][0]-kb[1][0]>=10 else 'clash','Front-to-back gap on the desktop','envelopes')
# 4. Knee zone stays open (the chair is the occupant).
kz=EQUIPMENT['knee_zone'];x0,x1,y0,y1=kz['bounds'];top=kz['clear_height'];intruders=sorted({part(o) for o in OBJECTS if not o.name.startswith('Chair') and any(x0+1<v.x<x1-1 and y0+1<v.y<y1-1 and 60<v.z<top-1 for v in world(o)[0])})
report('knee-zone','Central knee zone',y1-y0,700,'clash' if intruders else 'ok',('Intrudes: '+', '.join(intruders)) if intruders else f'{y1-y0:.0f} mm wide, {x1-x0:.0f} mm deep, {top} mm clear. Check against your own knee width with the chair arms.','envelopes')
# 5. Speaker aim: tweeter axis versus the seated ear reference.
for side,suffix in (('L',''),('R','.001')):
 body=bpy.data.objects.get('KRK monitor speaker reservation'+suffix);tw=bpy.data.objects.get('KRK tweeter'+suffix)
 if not body or not tw:continue
 axis=(body.matrix_world.to_3x3()@Vector((1,0,0))).normalized();t=tw.matrix_world.translation*1000;tray=body.get('speaker_tray')
 ear=Vector((EAR_MM[0],(2920+1305)/2,EAR_MM[1]));to_ear=(ear-t).normalized();error=math.degrees(axis.angle(to_ear))
 report('speaker-aim-'+side,f'Speaker {side} tweeter aim error',error,8,'ok' if error<=8 else 'tight',f'Tweeter at {t.z:.0f} mm, {(ear-t).length:.0f} mm from the ear reference; pad tilt {body.get("speaker_tilt_degrees",0)}°, capped at 10° for a stable wedge pad; under about 8° keeps the ear inside the tweeter on-axis window. Seated ear reference x {EAR_MM[0]}, z {EAR_MM[1]} mm.','envelopes','deg')
# 6. Storage below the ceiling.
storage=[o for o in OBJECTS if any(c.startswith(('13 ','15 ','18 ','07 ')) for c in collections(o)) or 'KNAGGLIG' in o.name]
instances=[(i.object.original,i.matrix_world.copy()) for i in dg.object_instances if i.is_instance and i.parent and 'KNAGGLIG' in i.parent.original.name]
tops=[max(((m@Vector(c))*1000).to_tuple()[::-1] for c in o.bound_box)[::-1]+('KNAGGLIG crate',) for o,m in instances]
tops=[(t[2],t[3],t[:3]) for t in tops]+[(v.z,part(o),tuple(v)) for o in storage for v in [max(world(o)[0],key=lambda v:v.z)]]
high=max(tops);gap=GEO['ceiling']-high[0];top_board=max(b['bottom']+b['thickness'] for k,b in json.loads((ROOT/'source/assembly.json').read_text())['boards'].items() if k.startswith('Rack.top'))
report('ceiling-storage','Highest storage to ceiling',gap,TARGET['storage_ceiling_gap_min'],'clash' if gap<0 else 'tight' if gap<TARGET['storage_ceiling_gap_min'] or not GEO['ceiling_measured'] else 'ok',f'{high[1]} reaches {high[0]:.0f} mm; ceiling {GEO["ceiling"]:.0f} mm'+(' measured' if GEO['ceiling_measured'] else ' ASSUMED — measure before buying the top crates')+f'. Above the {top_board:.0f} mm top boards there is {GEO["ceiling"]-top_board:.0f} mm; a 310 × 250 mm crate needs {math.hypot(310,250):.0f} mm to tilt in, otherwise it must slide in flat.','measured' if GEO['ceiling_measured'] else 'assumed',points=[high[2],(high[2][0],high[2][1],GEO['ceiling'])])
# 7. Under-bed boxes slide out under the side beam.
beams=named('Bed side beam',collection='05 ');beam_low=min(bounds([b])[0][2] for b in beams);boxes_top=max(bounds(named('Crate slat','Crate end slat',collection='05 '))[1][2],0)
bed_frame=named('Bed side beam','Bed loadbearing leg','Bed longitudinal support',collection='05 ');crates=named('Crate',collection='05 ')
blocked=tree(crates).overlap(tree(bed_frame))
report('under-bed','Under-bed boxes below the side beam',beam_low-boxes_top,TARGET['under_bed_beam_gap_min'],'clash' if blocked or beam_low-boxes_top<0 else 'tight' if beam_low-boxes_top<TARGET['under_bed_beam_gap_min'] else 'ok',f'Box top {boxes_top:.0f} mm incl. casters; beam underside {beam_low:.0f} mm. Boxes must stay at or below this height overall.','envelopes')
# 8. Door sweeps (directions assumed unless surveyed).
obstacles=[o for o in OBJECTS if not any(c.startswith(('01 ','09 ','10 ','12 ')) for c in collections(o)) and 'curtain' not in o.name.lower()]
def segment(px,py,ax,ay,bx,by):
 dx,dy=bx-ax,by-ay;t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)));return math.hypot(px-ax-t*dx,py-ay-t*dy)
def sweep_gap(leaf):
 hx,hy=leaf['hinge'];cx,cy=leaf['closed_toward'];ox,oy=leaf['open_toward'];w=math.hypot(cx-hx,cy-hy);a0=math.atan2(cy-hy,cx-hx);span=math.radians(leaf.get('max_angle',90))
 sign=1 if (cx-hx)*(oy-hy)-(cy-hy)*(ox-hx)>0 else -1;tip=lambda t:(hx+w*math.cos(a0+sign*t),hy+w*math.sin(a0+sign*t));best=(1e9,None)
 for o in obstacles:
  for v in world(o)[0]:
   if v.z>2100 or math.hypot(v.x-hx,v.y-hy)>w+400:continue
   r=math.hypot(v.x-hx,v.y-hy);ang=(math.atan2(v.y-hy,v.x-hx)-a0)*sign%math.tau
   d=(-1 if r<=w else r-w) if ang<=span else min(segment(v.x,v.y,hx,hy,*tip(0)),segment(v.x,v.y,hx,hy,*tip(span)))
   if d<best[0]:best=(d,part(o))
 return best
for leaf in ROOM['doors']['leaves']:
 gap,who=sweep_gap(leaf)
 report('door-'+leaf['id'].lower().replace(' ','-'),leaf['id']+' sweep',max(gap,0) if gap<1e8 else None,TARGET['door_sweep_gap_min'],'clash' if gap<0 else 'tight' if gap<TARGET['door_sweep_gap_min'] else 'ok',f'Swing {leaf["swing"]} to {leaf.get("max_angle",90)}°; nearest {who}' if gap<1e8 else f'Swing {leaf["swing"]}; nothing within reach','assumed' if leaf['status']!='measured' else 'measured')
# 9. Aisle between the bed and the wardrobe clothes.
bed=bounds(named('1400 x 2000 mattress',collection='05 '));aisle,who,at=min((v.x-bed[1][0],part(o),tuple(v)) for o in OBJECTS if any(c.startswith(('04 ','07 ','13 ')) for c in collections(o)) and 'curtain' not in o.name.lower() for v in world(o)[0] if bed[0][1]<v.y<bed[1][1] and v.z<1900 and v.x>bed[1][0])
report('bed-aisle','Bed to desk and wardrobe aisle',aisle,TARGET['aisle_min'],'ok' if aisle>=TARGET['aisle_min'] else 'tight',f'Narrowest point beside the bed: {who}. Garments in front of the wardrobe are included.','envelopes',points=[(bed[1][0],at[1],at[2]),at])
basis={'wall':'measured' if GEO['wall_measured'] else 'assumed','ceiling':'measured' if GEO['ceiling_measured'] else 'assumed','services':ROOM['services']['status'],'doors':ROOM['doors']['status']}
tilts={o.get('speaker_tilt_degrees') for o in OBJECTS if o.name.startswith('KRK monitor speaker reservation')}
out={'generated_by':'scripts/check-clearances.py','basis':basis,'ear_reference_mm':list(EAR_MM),'speaker_tilt_degrees':max(tilts),'checks':checks}
(ROOT/'public/data/clearances.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
for c in checks:print('CLEARANCE',c['status'].upper().ljust(6),c['label'],c['value'],c['unit'],'|',c['detail'],flush=True)
