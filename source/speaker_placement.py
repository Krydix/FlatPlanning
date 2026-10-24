"""Speaker position on a rotated tray: as far toward the wall and outward as the geometry allows.
Millimetres, plan view; no Blender dependency so the rule is unit-testable.
The speaker always faces the listening target; only its footprint centre moves.
"""
import math
from pipe_engine import point_in_board

def _rect(c,yaw,depth,width):
 f=(math.cos(yaw),math.sin(yaw));l=(-f[1],f[0])
 return [(c[0]+f[0]*a*depth/2+l[0]*b*width/2,c[1]+f[1]*a*depth/2+l[1]*b*width/2) for a,b in ((1,1),(1,-1),(-1,-1),(-1,1))]
def _seg(p,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];L=dx*dx+dy*dy;t=0 if L==0 else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/L));return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
def _inside(p,poly):
 s=[(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]) for a,b in zip(poly,poly[1:]+poly[:1])];return all(v>=0 for v in s) or all(v<=0 for v in s)
def _cross(a,b,c,d):
 o=lambda p,q,r:(q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0]);return o(a,b,c)*o(a,b,d)<0 and o(c,d,a)*o(c,d,b)<0
def clearance(poly,a,b):
 """Plan distance from a convex footprint to segment a-b (a point when a == b); negative if they overlap."""
 if _inside(a,poly) or _inside(b,poly) or any(_cross(a,b,p,q) for p,q in zip(poly,poly[1:]+poly[:1])):return -1
 return min([_seg(p,a,b) for p in poly]+[_seg(e,p,q) for e in (a,b) for p,q in zip(poly,poly[1:]+poly[:1])])

def obstacles(parts,z0,z1):
 """Frame parts whose height overlaps [z0, z1], as plan segments with an envelope radius."""
 out=[]
 for p in parts:
  k=p['kind'];o=p['origin'];ax=p['axis']
  if k.startswith('tube_'):
   L=p['data']['length'];e=[o[i]+ax[i]*L for i in range(3)]
   if max(o[2],e[2])+12.5<z0 or min(o[2],e[2])-12.5>z1:continue
   out.append((p['id'],tuple(o[:2]),tuple(e[:2]),12.5))
  elif k in ('slide_tee','cross','elbow','extension','cap','flange'):
   half=35
   if o[2]+half<z0 or o[2]-half>z1:continue
   out.append((p['id'],tuple(o[:2]),tuple(o[:2]),35 if k=='flange' else 17))
 return out

def candidates(tray,target,size,parts,wall_x,keepouts=(),height=330,base=1128,margin=5,gap=15,wall_gap=20,step=5,middle_y=None):
 """Every valid footprint on the tray, keyed by its (along, across) tray-frame offset."""
 depth,width=size[:2];x0,x1,y0,y1=tray['bounds'];cx,cy=(x0+x1)/2,(y0+y1)/2;th=math.radians(tray.get('rotation_degrees',0))
 middle_y=target[1] if middle_y is None else middle_y;out_sign=1 if cy>middle_y else -1
 # Tilting lifts the rear edge by up to depth*sin(10°); check obstacles over the full raised height.
 obs=obstacles(parts,base,base+height+depth*math.sin(math.radians(10)))
 found={};half=(x1-x0)/2
 for i in range(int(-half),int(half)+1,step):
  for j in range(int(-half),int(half)+1,step):
   c=(cx+i*math.cos(th)-j*math.sin(th),cy+i*math.sin(th)+j*math.cos(th));yaw=math.atan2(target[1]-c[1],target[0]-c[0]);poly=_rect(c,yaw,depth,width)
   if not all(point_in_board(x,y,tray,-margin) for x,y in poly):continue
   if max(x for x,_ in poly)>wall_x-wall_gap:continue
   near=min([(clearance(poly,a,b)-r,id) for id,a,b,r in obs]+[(min(clearance(poly,(k[0],k[2]),(k[1],k[2])),clearance(poly,(k[0],k[3]),(k[1],k[3])),clearance(poly,(k[0],k[2]),(k[0],k[3])),clearance(poly,(k[1],k[2]),(k[1],k[3]))),'keep-out') for k in keepouts],default=(1e9,None))
   if near[0]<gap:continue
   # Rear = toward the wall behind the desk (+x); outward = away from the desk centre line.
   score=(c[0]-cx)+out_sign*(c[1]-cy)
   found[(i,j)]={'score':score,'centre':(round(c[0],1),round(c[1],1)),'yaw':yaw,'footprint':poly,'nearest':(round(near[0],1),near[1]),'wall_gap':round(wall_x-max(x for x,_ in poly),1),'tray_offset':(i,j)}
 return found
def place_pair(trays,targets,size,parts,wall_x,middle_y,**options):
 """Mirror-symmetric rear-outer placement on two mirrored trays, so both speakers sit at equal distances."""
 a=candidates(trays[0],targets[0],size,parts,wall_x,middle_y=middle_y,**options);b=candidates(trays[1],targets[1],size,parts,wall_x,middle_y=middle_y,**options)
 pairs=[(a[k]['score']+b[(k[0],-k[1])]['score'],k) for k in a if (k[0],-k[1]) in b]
 if not pairs:raise ValueError('No mirrored speaker position fits both trays')
 k=max(pairs)[1];return a[k],b[(k[0],-k[1])]
def speaker_layout(root):
 """Placement for the configured trays from the saved graph and equipment file (root = repository)."""
 import json
 from pathlib import Path
 from pipe_engine import WALL_X
 root=Path(root);graph=json.loads((root/'source/assembly.json').read_text());cfg=json.loads((root/'source/equipment-layout.json').read_text());sp=cfg['speakers']
 parts={p['id']:p for p in graph['parts']};trays=[graph['boards'][t] for t in sp['trays']];targets=[parts[t]['data']['speaker_target_mm'] for t in sp['trays']]
 # Static desk items that reach the speaker height band are keep-out boxes (the monitor).
 base=trays[0]['bottom']+trays[0]['thickness']+sp['pad'];keep=[]
 for d in cfg['desk_items']:
  if 'size' in d and d['location'][2]+d['size'][2]/2>base:(x,y,_),(dx,dy,_)=d['location'],d['size'];keep.append((x-dx/2,x+dx/2,y-dy/2,y+dy/2))
 desk=graph['boards']['Desk.top']['bounds'];middle=(desk[2]+desk[3])/2
 return place_pair(trays,targets,sp['size'],graph['parts'],WALL_X,middle,keepouts=keep,height=sp['size'][2],base=base,**sp.get('placement',{}))
