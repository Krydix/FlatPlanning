"""Room clearance and clash report from the locked Blender model; run in Blender background.
Writes public/data/clearances.json. Distances are model distances in mm: they are only as true
as source/room-measurements.json and the equipment envelopes, and each check records its basis.
"""
import bpy,sys,json,math,os
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT/'source'))
from pipe_engine import room_geometry,EAR_MM
# FLAT_VARIANT=portal checks source/flat-portal.blend; the default keeps V18's own report.
PORTAL=os.environ.get('FLAT_VARIANT')=='portal';SCENE,GRAPH,REPORT=('flat-portal.blend','assembly-portal.json','clearances-portal.json') if PORTAL else ('flat-v18.blend','assembly.json','clearances.json')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source'/SCENE));scene=bpy.context.scene;scene.frame_set(1)
ROOM=json.loads((ROOT/'source/room-measurements.json').read_text());GEO=room_geometry();TARGET=ROOM['clearance_targets']
EQUIPMENT=json.loads((ROOT/'source/equipment-layout.json').read_text());ASSEMBLY=json.loads((ROOT/'source'/GRAPH).read_text());DESK=ASSEMBLY['boards']['Desk.top']['bounds']
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
report('entry-passage','Entrance passage, kitchen corner to '+('divider' if PORTAL else 'desk'),best[0],TARGET['entry_passage_min'],status,f'Nearest: {best[1]}. At floor level the nearest is {floor[1]} at {floor[0]:.0f} mm. Comfortable two-way passage is about {TARGET["entry_passage_comfortable"]} mm.','assumed' if not GEO['wall_measured'] else 'measured',points=[(kx,ky,best[2].z),tuple(best[2])])
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
kz=EQUIPMENT['knee_zone'];x0,x1,y0,y1=kz['bounds'];y0+=DESK[2]-1305;y1+=DESK[2]-1305;top=kz['clear_height'];intruders=sorted({part(o) for o in OBJECTS if not o.name.startswith('Chair') and any(x0+1<v.x<x1-1 and y0+1<v.y<y1-1 and 60<v.z<top-1 for v in world(o)[0])})
report('knee-zone','Central knee zone',y1-y0,700,'clash' if intruders else 'ok',('Intrudes: '+', '.join(intruders)) if intruders else f'{y1-y0:.0f} mm wide, {x1-x0:.0f} mm deep, {top} mm clear. Check against your own knee width with the chair arms.','envelopes')
# 5. Speaker aim: tweeter axis versus the seated ear reference.
for side,suffix in (('L',''),('R','.001')):
 body=bpy.data.objects.get('KRK monitor speaker reservation'+suffix);tw=bpy.data.objects.get('KRK tweeter'+suffix)
 if not body or not tw:continue
 axis=(body.matrix_world.to_3x3()@Vector((1,0,0))).normalized();t=tw.matrix_world.translation*1000;tray=body.get('speaker_tray')
 ear=Vector((EAR_MM[0],(DESK[2]+DESK[3])/2,EAR_MM[1]));to_ear=(ear-t).normalized();error=math.degrees(axis.angle(to_ear))
 report('speaker-aim-'+side,f'Speaker {side} tweeter aim error',error,8,'ok' if error<=8 else 'tight',f'Tweeter at {t.z:.0f} mm, {(ear-t).length:.0f} mm from the ear reference; pad tilt {body.get("speaker_tilt_degrees",0)}°, capped at 10° for a stable wedge pad; under about 8° keeps the ear inside the tweeter on-axis window. Seated ear reference x {EAR_MM[0]}, z {EAR_MM[1]} mm.','envelopes','deg')
# 6. Storage below the ceiling.
# Ceiling ties reach the slab by design; they are fixings, not storage.
storage=[o for o in OBJECTS if (any(c.startswith(('13 ','15 ','18 ','07 ')) for c in collections(o)) or 'KNAGGLIG' in o.name) and not part(o).startswith('Portal.tie')]
instances=[(i.object.original,i.matrix_world.copy()) for i in dg.object_instances if i.is_instance and i.parent and 'KNAGGLIG' in i.parent.original.name]
tops=[max(((m@Vector(c))*1000).to_tuple()[::-1] for c in o.bound_box)[::-1]+('KNAGGLIG crate',) for o,m in instances]
tops=[(t[2],t[3],t[:3]) for t in tops]+[(v.z,part(o),tuple(v)) for o in storage for v in [max(world(o)[0],key=lambda v:v.z)]]
high=max(tops);gap=GEO['ceiling']-high[0];top_board=max(b['bottom']+b['thickness'] for k,b in ASSEMBLY['boards'].items() if k.startswith('Portal.lintel1' if PORTAL else 'Rack.top'))
report('ceiling-storage','Highest storage to ceiling',gap,TARGET['storage_ceiling_gap_min'],'clash' if gap<0 else 'tight' if gap<TARGET['storage_ceiling_gap_min'] or not GEO['ceiling_measured'] else 'ok',f'{high[1]} reaches {high[0]:.0f} mm; ceiling {GEO["ceiling"]:.0f} mm'+(' measured' if GEO['ceiling_measured'] else ' ASSUMED — measure before buying the top crates')+f'. Above the {top_board:.0f} mm top boards there is {GEO["ceiling"]-top_board:.0f} mm; a 310 × 250 mm crate needs {math.hypot(310,250):.0f} mm to tilt in, otherwise it must slide in flat.','measured' if GEO['ceiling_measured'] else 'assumed',points=[high[2],(high[2][0],high[2][1],GEO['ceiling'])])
# 7. The daybed's pull-out slides out under the front rail and the fixed slats.
bed_parts=lambda kind:[o for o in OBJECTS if o.get('bed_part')==kind]
STROKE,LIFT=(v*1000 for v in scene.get('bed_extend_m',(0,0)))
pullout=bed_parts('pullout');fixed_bed=[o for o in bed_parts('fixed') if not o.name.startswith(('ÅGOTNES','Folded'))]
pull_top=bounds(pullout)[1][2];over=[o for o in fixed_bed if bounds([o])[0][0]>bounds(pullout)[0][0] and bounds([o])[0][2]>pull_top-5];over_low=min(bounds([o])[0][2] for o in over)
blocked=tree(pullout).overlap(tree(fixed_bed))
report('under-bed','Pull-out below the front rail and slats',over_low-pull_top,TARGET['under_bed_beam_gap_min'],'clash' if blocked or over_low<pull_top else 'tight' if over_low-pull_top<TARGET['under_bed_beam_gap_min'] else 'ok',f'Closed pull-out top {pull_top:.0f} mm; lowest rail or slat above it {over_low:.0f} mm. Board sizes are read from IKEA photos.','envelopes')
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
 # A leaf the layout deliberately lets stop against furniture reports how far it still opens.
 if gap<0 and leaf.get('accepted_stop'):
  lo,hi=0.,float(leaf.get('max_angle',90))
  for _ in range(14):
   mid=(lo+hi)/2;lo,hi=(mid,hi) if sweep_gap({**leaf,'max_angle':mid})[0]>=0 else (lo,mid)
  report('door-'+leaf['id'].lower().replace(' ','-'),leaf['id']+' sweep',round(lo),leaf.get('max_angle',90),'tight',f'Opens to about {lo:.0f}° of {leaf.get("max_angle",90)}°, then stops against {who}. Accepted: {leaf["accepted_stop"]}','assumed' if leaf['status']!='measured' else 'measured',unit='deg');continue
 report('door-'+leaf['id'].lower().replace(' ','-'),leaf['id']+' sweep',max(gap,0) if gap<1e8 else None,TARGET['door_sweep_gap_min'],'clash' if gap<0 else 'tight' if gap<TARGET['door_sweep_gap_min'] else 'ok',f'Swing {leaf["swing"]} to {leaf.get("max_angle",90)}°; nearest {who}' if gap<1e8 else f'Swing {leaf["swing"]}; nothing within reach','assumed' if leaf['status']!='measured' else 'measured')
# 9. Aisle between the bed and the wardrobe clothes, with the daybed pulled out to a double.
lo,hi=bounds(bed_parts('fixed')+pullout);bed=([lo[0],lo[1],lo[2]],[bounds(pullout)[1][0]+STROKE,hi[1],hi[2]+LIFT]);aisle,who,at=min((v.x-bed[1][0],part(o),tuple(v)) for o in OBJECTS if any(c.startswith(('04 ','07 ','13 ')) for c in collections(o)) and 'curtain' not in o.name.lower() for v in world(o)[0] if bed[0][1]<v.y<bed[1][1] and v.z<1900 and v.x>bed[1][0])
report('bed-aisle','Extended bed to desk and wardrobe aisle',aisle,TARGET['aisle_min'],'ok' if aisle>=TARGET['aisle_min'] else 'tight',f'Narrowest point beside the pulled-out bed: {who}. Garments in front of the wardrobe are included.','envelopes',points=[(bed[1][0],at[1],at[2]),at])
# 10. Portal divider: fixed furniture agrees with the layout file, the door stays open, the crates really fit.
if PORTAL:
 L=json.loads((ROOT/'source/portal-layout.json').read_text());F=L['fixed'];P=ASSEMBLY['portal'];C=L['crate']['size'];xs=P['xs'];yf,yb=P['rows'];cx=P['cx'];cz=P['centre_z'];sh=P['semi_height'];hw=P['half_width']
 frame_parts=[o for o in OBJECTS if any(c.startswith(('13 ','15 ','18 ')) for c in collections(o)) and yf-60<bounds([o])[1][1] and bounds([o])[0][1]<yb+60]
 bar=bounds(named('FIXED bar worktop','OPTIONAL removable oak bar end skin'));bed=([*bounds(bed_parts('fixed'))[0]],[bounds(pullout)[1][0]+STROKE,0,0])
 for id,label,model,value in (('bar-end','Bar end vs portal layout',bar[1][0],F['bar_end_x']),('bar-back','Bar back vs portal layout',bar[1][1],F['bar_back_y']),('bed-near','Bed near side vs portal layout',bed[0][1],F['bed_near_y']),('bed-right','Extended bed front vs portal layout',bed[1][0],F['bed_right_x'])):
  delta=abs(model-value);report('portal-fixed-'+id,label,delta,5,'clash' if delta>5 else 'ok',f'Model {model:.0f} mm, layout file {value:.0f} mm','assumed')
 left=min(v.x for o in assembly if part(o).startswith(('PF0','PB0','Portal')) for v in world(o)[0]);gap=left-F['bar_end_x']
 report('portal-bar-gap','Divider to bar end',gap,10,'clash' if gap<0 else 'tight' if gap<10 else 'ok','Lowest boards and foot flanges beside the bar end, including the optional oak skin.','assumed')
 # Nothing may enter the ellipse the shelves describe, at any depth through the divider.
 outside=lambda v:((v.x-cx)/hw)**2+((v.z-cz)/sh)**2;board_y=ASSEMBLY['boards']['Portal.lintel0']['bounds'][2:]
 # The desk's near return stands on the rear post line by design, so it is measured separately below.
 desk_end=('DF0','Desk.low0','Desk.shared0','Desk.top')
 intruders=sorted({part(o) for o in OBJECTS if not any(c.startswith(('01 ','05 ','02 ','09 ','10 ','12 ','04 ','07 ')) for c in collections(o)) and not part(o).startswith(desk_end) for v in world(o)[0] if board_y[0]<=v.y<=board_y[1]-.5 and 0<v.z and outside(v)<.98})
 report('portal-outline','Parts inside the portal opening',len(intruders),0,'clash' if intruders else 'ok','; '.join(intruders) or f'Clear ellipse {2*hw:.0f} mm wide and {P["head"]:.0f} mm high, centred on x {cx:.0f}, apart from the desk return checked below. Oak light cover included.','envelopes','count')
 uprights=[(a,b,math.dist(A,B)) for i,(a,A) in enumerate(sorted((k,(v['x'],v['y'])) for k,v in ASSEMBLY['columns'].items())) for b,B in sorted((k,(v['x'],v['y'])) for k,v in ASSEMBLY['columns'].items())[i+1:]];near=min(uprights,key=lambda u:u[2])
 report('portal-doubled-posts','Closest two uprights',near[2],200,'ok' if near[2]>=200 else 'clash',f'{near[0]} and {near[1]}. Below 200 mm two posts would be doing one job.','envelopes')
 floor_width=2*hw*math.sqrt(max(0,1-(cz/sh)**2));report('portal-floor-width','Portal width at the floor',floor_width,800,'ok' if floor_width>=800 else 'tight','Width of the ellipse at floor level; it widens with height.','envelopes')
 shoulder=2*hw*math.sqrt(max(0,1-((1500-cz)/sh)**2));report('portal-shoulder','Portal width at 1,500 mm height',shoulder,700,'ok' if shoulder>=700 else 'tight','Shoulder height of a tall adult walking through.','envelopes')
 # Bounds, not vertices: a long cover has no vertex near the centre line.
 spans=[bounds([o]) for o in OBJECTS if any(c.startswith(('13 ','15 ')) for c in collections(o))];hd=min(lo[2] for lo,hi in spans if lo[0]<cx+250 and hi[0]>cx-250 and lo[1]<board_y[1] and hi[1]>board_y[0] and lo[2]>1500)
 # Behind the opening the walkway is bounded by the door's kitchen-side edge and the desk's front corner.
 desk_x=ASSEMBLY['boards']['Desk.top']['bounds'][0];exit_width=desk_x-(cx-2*hw*math.sqrt(max(0,1-(cz/sh)**2))/2)
 report('portal-exit','Walkway through the door past the desk corner',exit_width,600,'clash' if exit_width<600 else 'tight' if exit_width<TARGET['entry_passage_comfortable'] else 'ok',f'Left edge of the opening at the floor to the desktop edge at x {desk_x:.0f}. The near desk leg and its low brace stand on the rear post line, in the right-hand part of the opening.','envelopes')
 report('portal-head','Portal head height at the centre',hd,1950,'ok' if hd>=1950 else 'tight',f'Lowest part within 250 mm of the centre line: the oak light cover or lintel rail. Ceiling {GEO["ceiling"]:.0f} mm.','measured' if GEO['ceiling_measured'] else 'assumed')
 groups_=defaultdict(list)
 for i in dg.object_instances:
  if i.is_instance and i.parent and 'KNAGGLIG' in i.parent.original.name:groups_[i.parent.original.name].append((i.object.original,i.matrix_world.copy()))
 boxes_=[]
 for key,items in groups_.items():
  pts=[(m@Vector(c))*1000 for o,m in items for c in o.bound_box];boxes_.append(([min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]))
 boards=ASSEMBLY['boards'];hit=[];side=[];depth=[]
 for lo,hi in boxes_:
  size=[hi[i]-lo[i] for i in range(3)]
  if abs(size[0]-C[0])>12 or abs(size[1]-C[1])>12 or abs(size[2]-C[2])>12:hit.append(f'wrong crate envelope {size}')
  depth.append(min(lo[1]-boards['Portal.lintel0']['bounds'][2],boards['Portal.lintel0']['bounds'][3]-hi[1]))
  side.append(min(lo[0]-xs[1],xs[2]-hi[0])-12.5)
  for o in OBJECTS:
   if any(c.startswith(('13 ','15 ')) for c in collections(o)) and not (part(o).startswith('Portal.lintel')):
    b=bounds([o])
    if all(lo[i]+1<b[1][i] and b[0][i]<hi[i]-1 for i in range(3)):hit.append(part(o))
 hit=sorted(set(hit));report('portal-crate-count','KNAGGLIG crates on the lintel boards',len(boxes_),6,'ok' if len(boxes_)==6 else 'clash',f'{len(boxes_)} crates of {C[0]} x {C[1]} x {C[2]} mm, long side across the room.','envelopes','count')
 report('portal-crate-clash','Parts intersecting a crate',len(hit),0,'clash' if hit else 'ok','; '.join(hit) or 'No frame, hanger or light part intersects any crate envelope.','envelopes','count')
 report('portal-crate-side','Crate to inner post',min(side),5,'clash' if min(side)<0 else 'tight' if min(side)<5 else 'ok','Tightest end of the three-crate row between the inner posts.','envelopes')
 report('portal-crate-depth','Crate inside board depth',min(depth),20,'clash' if min(depth)<0 else 'ok',f'Boards are {boards["Portal.lintel0"]["bounds"][3]-boards["Portal.lintel0"]["bounds"][2]:.0f} mm deep; crates are {C[1]} mm deep.','envelopes')
# 11. Floors: rays cast downward from the room air must never leave the flat through the floor line.
for o in scene.objects:
 cols=collections(o)
 if any(c.startswith(('06 ','11 ')) for c in cols) and not any(c.startswith('01 ') for c in cols):o.hide_viewport=True
bpy.context.view_layer.update();rays=bpy.context.evaluated_depsgraph_get();down=[Vector((math.cos(a)*c,math.sin(a)*c,-math.sqrt(1-c*c))).normalized() for a in [i*math.tau/16 for i in range(16)] for c in (.5,.9,.985)];gaps=[];cast=0
for x0,x1,y0,y1 in ((0,3450,0,5300),(2200,3450,-3200,-100),(0,2100,-3050,-300),(2450,3350,-100,0),(2100,2200,-1620,-850)):
 for x in range(x0+25,x1,75):
  for y in range(y0+25,y1,75):
   o=Vector((x,y,40))/1000
   if scene.ray_cast(rays,o,Vector((0,0,1)),distance=.0005)[0]:continue
   for d in down:
    cast+=1;hit=scene.ray_cast(rays,o,d,distance=9)[0];foot=o+d*((o.z+.01)/-d.z)
    if not hit and 0<=foot.x<=GEO['wall_x']/1000 and -3.2<=foot.y<=5.3:gaps.append((round(foot.x*1000),round(foot.y*1000)))
report('floor-gaps','Rays escaping through the floor',len(gaps),0,'clash' if gaps else 'ok',f'{cast} rays cast down from the room air.'+(f' First escapes at {gaps[:4]}.' if gaps else ' None leave the flat through the floor line.'),'envelopes','count')
# Balcony leaves: how far each opens with the daybed closed and pulled out. The viewer opens
# them this far and closes the left leaf down before the bed extends.
def free_angle(leaf):
 top=float(leaf.get('max_angle',90))
 if sweep_gap(leaf)[0]>=0:return top
 lo,hi=0.,top
 for _ in range(14):
  mid=(lo+hi)/2;lo,hi=(mid,hi) if sweep_gap({**leaf,'max_angle':mid})[0]>=0 else (lo,mid)
 return lo
# The sweep test looks at vertices, and a long mattress edge can cross the leaf between its
# corners. Bed parts are sampled every 25 mm along their edges for this test only.
def dense(o):
 vs,ps=world(o);pts=list(vs)
 for poly in ps:
  for a,b in zip(poly,poly[1:]+poly[:1]):
   n=int((vs[b]-vs[a]).length//25)
   pts+=[vs[a].lerp(vs[b],k/(n+1)) for k in range(1,n+1)]
 return pts,ps
saved={o.name:cache[o.name] if o.name in cache else world(o) for o in bed_parts('fixed')+bed_parts('pullout')+bed_parts('legs')}
for o in bed_parts('fixed')+bed_parts('pullout')+bed_parts('legs'):cache[o.name]=dense(o)
def bed_extended(on):
 for o in bed_parts('pullout')+bed_parts('legs'):
  shift=Vector((STROKE,0,LIFT if o.get('bed_part')=='pullout' else 0))*(1 if on else -1);vs,ps=world(o);cache[o.name]=([v+shift for v in vs],ps)
balcony=[]
for leaf in ROOM['doors']['leaves']:
 if not leaf['id'].startswith('Balcony'):continue
 daybed=free_angle(leaf);bed_extended(True);extended=free_angle(leaf);bed_extended(False)
 balcony.append({'id':leaf['id'],'side':'left' if 'left' in leaf['id'].lower() else 'right','hinge_mm':leaf['hinge'],'closed_toward_mm':leaf['closed_toward'],'open_toward_mm':leaf['open_toward'],'max_angle':leaf.get('max_angle',90),'angle_daybed':round(daybed,1),'angle_bed_extended':round(extended,1),'basis':'assumed' if leaf['status']!='measured' else 'measured'})
print('BALCONY',json.dumps(balcony),flush=True)
cache.update(saved)
basis={'wall':'measured' if GEO['wall_measured'] else 'assumed','ceiling':'measured' if GEO['ceiling_measured'] else 'assumed','services':ROOM['services']['status'],'doors':ROOM['doors']['status']}
tilts={o.get('speaker_tilt_degrees') for o in OBJECTS if o.name.startswith('KRK monitor speaker reservation')}
out={'generated_by':'scripts/check-clearances.py','basis':basis,'ear_reference_mm':list(EAR_MM),'speaker_tilt_degrees':max(tilts),'balcony':balcony,'checks':checks}
(ROOT/'public/data'/REPORT).write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
for c in checks:print('CLEARANCE',c['status'].upper().ljust(6),c['label'],c['value'],c['unit'],'|',c['detail'],flush=True)
