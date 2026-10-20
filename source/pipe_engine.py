"""DOLLE PIPE design graph. Millimetres throughout; no Blender dependency.
Socket coordinates are seating stops, NOT outer fitting faces. A preview profile
is intentionally NOT a measured profile. This is a geometric design tool, not a
structural certification or a manufacturer's digital twin.
"""
from dataclasses import dataclass, field, asdict
from collections import Counter, defaultdict
import math, json, copy
from pathlib import Path
FAMILY='DOLLE-current-25-metric-unconfirmed-pitch'
STOCK={40:('96193','https://www.obi.de/p/4964102/dolle-rohr-tube-fuer-pipe-regalsystem-25-mm-x-40-mm-schwarz-matt'),200:('96247','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-200-mm-20-mm-3-4-schwarz-matt-0763202832/'),250:('96254','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-250-mm-20-mm-3-4-schwarz-matt-0763202837/'),602:('96599','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-602-mm-20-mm-3-4-schwarz-matt-0763202834/'),802:('96605','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-802-mm-20-mm-3-4-schwarz-matt-0763202835/'),1000:('96292','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-1000-mm-20-mm-3-4-schwarz-matt-0763202825/'),1200:('verify supplier','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-1200-mm-20-mm-3-4-schwarz-matt-0763202841/'),1500:('96339','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-1500-mm-20-mm-3-4-schwarz-matt-0763202820/')}
PROFILE={
 'saddle_rise':{'value':15,'status':'preview','measure':'Horizontal tube axis to wood underside at the saddle tab'},
 'saddle_tab_offset':{'value':32,'status':'preview','measure':'Tube axis to shelf screw hole, perpendicular to tube'},
 'saddle_half_width':{'value':7,'status':'preview','measure':'Half the strap width along the horizontal tube'},
 'flange_stop':{'value':15,'status':'preview','measure':'Mounting face to fully seated tube end'},
 'tee_stop':{'value':20,'status':'preview','measure':'Upright axis to fully seated branch tube end'},
 'tee_half_height':{'value':35,'status':'published envelope','measure':'Half of measured sleeve height: 70 mm overall means enter 35'},
 'tee_outer_radius':{'value':17,'status':'published envelope','measure':'Half of measured sleeve outside diameter: 34 mm overall means enter 17'},
 'tee_engagement':{'value':10,'status':'preview','measure':'Sliding-tee branch: mouth to tube-end seating stop'},
 'flange_engagement':{'value':10,'status':'preview','measure':'Flange socket: mouth to tube-end seating stop'},
 'extension_engagement':{'value':10,'status':'preview','measure':'Extension socket: mouth to tube-end seating stop; check both ends'},
 'elbow_engagement':{'value':10,'status':'preview','measure':'Elbow socket: mouth to tube-end seating stop; check both ends'},
 'extension_gap':{'value':12,'status':'preview','measure':'Gap between two tube ends seated in extension 96445'},
 'elbow_stop':{'value':20,'status':'preview','measure':'Elbow axis intersection to seated tube end, both ports'},
 'holder_wing':{'value':32,'status':'preview','measure':'Post axis to wood screw centre on split end holder'},
 'middle_holder_wing':{'value':32,'status':'preview','measure':'MIDDLE holder: post axis to wood screw centre, check each side'},
 'holder_height':{'value':19,'status':'published envelope','measure':'End holder overall height, not plate thickness'},
 'holder_plate':{'value':3,'status':'preview','measure':'Wood support plate thickness'},
 'clip_height':{'value':3,'status':'preview','measure':'MITTLED fitted clip stand-off from wood to housing'},
 'cap_fit':{'value':1,'status':'preview','measure':'Verify 96476 stopper installation on current externally threaded tube'},
}
CATALOG={
 'saddle':{'sku':'toom 7450897; DOLLE EAN unconfirmed','name':'DOLLE PIPE one-sided saddle shelf holder, 2 per Toom pack','source':'https://toom.de/p/regalbodenhalter-fuer-regalsystem-pipe-schwarz-2-stueck/7450897'},
 'flange':{'sku':'96483','name':'DOLLE plate / flange Ø70','source':'https://www.globus-baumarkt.de/p/dolle-plattenscheibe-fuer-pipe-regalsystem-oe-70-mm-20-mm-3-4-schwarz-matt-0763202822/'},
 'slide_tee':{'sku':'96544','name':'DOLLE sliding T, one female branch, Ø25 sleeve','source':'https://www.globus-baumarkt.de/p/dolle-t-verbinder-fuer-pipe-regalsystem-20-mm-3-4-verschiebbar-schwarz-matt-0763202823/'},
 'extension':{'sku':'96445','name':'DOLLE Extension, TWO FEMALE THREADS','source':'https://www.obi.de/p/4978219/dolle-doppelmuffe-extension-fuer-pipe-regalsystem-20-mm-3-4-schwarz-matt'},
 'elbow':{'sku':'96353','name':'DOLLE 90 degree elbow, two female threads','source':'https://www.obi.de/p/4974440/dolle-90-eckverbinder-fuer-pipe-regalsystem-2-innengewinden-20-mm-3-4-schwarz'},
 'end_holder':{'sku':'supplier item 115610071; DOLLE no. pending','name':'DOLLE PIPE split end shelf holder, one assembled holder','source':'https://www.sonderpreis-baumarkt.de/renovieren-und-wohnen/inneneinrichtung/wohneinrichtung/regale/regalbodenhalter-endstueck-pipe-%C3%B8-25-mm-schwarz-2er-set-115610071.html'},
 'middle_holder':{'sku':'supplier item 115610070; DOLLE no. pending','name':'DOLLE PIPE split middle shelf holder, one assembled holder','source':'https://www.sonderpreis-baumarkt.de/renovieren-und-wohnen/inneneinrichtung/wohneinrichtung/regale/regalbodenhalter-mittelstueck-pipe-%C3%B8-25-mm-schwarz-115610070.html'},
 'hook':{'sku':'96490','name':'DOLLE shelf hook, 4 hooks + 8 screws per set','source':'https://www.globus-baumarkt.de/p/dolle-regalbodenhalter-set-fuer-pipe-regalsystem-haken-schrauben-schwarz-matt-0763202817/'},
 'cap':{'sku':'96476','name':'DOLLE end stopper, fit to verify, 2 per pack','source':'https://www.globus-baumarkt.de/p/dolle-abdeckstopfen-fuer-pipe-regalsystem-20-mm-3-4-schwarz-matt-2-stueck-0763202816/'},
}
for L,(sku,url) in STOCK.items(): CATALOG['tube_'+str(L)]={'sku':sku,'name':f'DOLLE tube Ø25 × {L} mm','source':url}
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def mul(a,s):return tuple(x*s for x in a)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def norm(a):return math.sqrt(dot(a,a))
def unit(a):return mul(a,1/norm(a))
def close(a,b,tol=.001):return norm(sub(a,b))<tol
def board_corners(board):
 x0,x1,y0,y1=board['bounds'];cx=(x0+x1)/2;cy=(y0+y1)/2;theta=math.radians(board.get('rotation_degrees',0));c=math.cos(theta);s=math.sin(theta)
 return [(cx+c*(x-cx)-s*(y-cy),cy+s*(x-cx)+c*(y-cy)) for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
def point_in_board(x,y,board,margin=0):
 x0,x1,y0,y1=board['bounds'];cx=(x0+x1)/2;cy=(y0+y1)/2;theta=-math.radians(board.get('rotation_degrees',0));c=math.cos(theta);s=math.sin(theta);dx=x-cx;dy=y-cy
 return x0-margin<=cx+c*dx-s*dy<=x1+margin and y0-margin<=cy+s*dx+c*dy<=y1+margin
class DesignError(ValueError):pass
@dataclass
class Port:
 id:str; owner:str; kind:str; p:tuple; n:tuple; family:str=FAMILY; used:str|None=None
@dataclass
class Part:
 id:str; kind:str; origin:tuple; axis:tuple=(0,0,1); direction:tuple=(1,0,0); data:dict=field(default_factory=dict)
class Assembly:
 def __init__(self,profile=None):
  self.profile=copy.deepcopy(profile or PROFILE);self.parts={};self.ports={};self.edges=[];self.mounts={};self.clamps=[];self.boards={};self.lights=[];self.columns={};self.notes=[]
 def v(self,k):return self.profile[k]['value']
 def part(self,id,kind,p,axis=(0,0,1),direction=(1,0,0),**data):
  if id in self.parts:raise DesignError('Duplicate ID '+id)
  if kind not in CATALOG and kind not in ('wood','light'):raise DesignError('Not in component catalog: '+kind)
  self.parts[id]=Part(id,kind,tuple(p),tuple(axis),tuple(direction),data);return id
 def port(self,id,owner,kind,p,n,family=FAMILY):
  if id in self.ports:raise DesignError('Duplicate port')
  self.ports[id]=Port(id,owner,kind,tuple(p),tuple(n),family);return id
 def connect(self,a,b):
  pa,pb=self.ports[a],self.ports[b]
  if pa.used or pb.used:raise DesignError('Port already occupied')
  if {pa.kind,pb.kind}!={'male','female'}:raise DesignError('Only male/female thread mates allowed')
  if pa.family!=pb.family:raise DesignError('Thread family mismatch')
  if not close(pa.p,pb.p) or dot(pa.n,pb.n)>-.999999:raise DesignError('Ports not seated and opposed')
  pa.used=b;pb.used=a;self.edges.append((pa.owner,pb.owner,'thread',a,b))
 def tube(self,id,L,start,direction):
  if L not in STOCK:raise DesignError('Tube must be an uncut catalog stock length')
  d=unit(direction);self.part(id,'tube_'+str(L),start,d,length=L)
  self.port(id+'.a',id,'male',start,mul(d,-1));self.port(id+'.b',id,'male',add(start,mul(d,L)),d)
  return id
 def from_port(self,id,L,port):
  p=self.ports[port]
  if p.kind!='female' or p.used:raise DesignError('Start with a free female port')
  self.tube(id,L,p.p,p.n);self.connect(port,id+'.a');return id
 def flange(self,id,p,n,surface):
  if surface not in ('floor','wall','wood'):raise DesignError('Flange must mount to floor, wall or wood')
  if surface=='floor' and (abs(p[2])>.001 or dot(n,(0,0,1))<.999):raise DesignError('Floor mounting plane wrong')
  if surface=='wall' and (abs(p[0]-3450)>.001 or dot(n,(-1,0,0))<.999):raise DesignError('Right-wall mounting plane wrong')
  self.part(id,'flange',p,n);self.mounts[id]=surface
  self.port(id+'.socket',id,'female',add(p,mul(n,self.v('flange_stop'))),n);return id
 def cap(self,id,port):
  # End cover is a separate non-load-bearing attachment, NOT a fabricated female fitting.
  p=self.ports[port]
  if p.used:raise DesignError('Cannot cap an occupied end')
  self.part(id,'cap',p.p,p.n,interface_status='fit unverified; no structural role')
  p.used=id;self.edges.append((p.owner,id,'cover',port,None))
 def column(self,id,x,y,upper=1200,lower=1000):
  self.flange(id+'.foot',(x,y,0),(0,0,1),'floor')
  lo=self.from_port(id+'.lower',lower,id+'.foot.socket');seq=[lo];end=self.ports[lo+'.b'].p
  if upper:
   gap=self.v('extension_gap');c=add(end,(0,0,gap/2));ex=id+'.extension';self.part(ex,'extension',c,gap=gap)
   self.port(ex+'.down',ex,'female',end,(0,0,-1));self.port(ex+'.up',ex,'female',add(end,(0,0,gap)),(0,0,1))
   self.connect(lo+'.b',ex+'.down');hi=self.from_port(id+'.upper',upper,ex+'.up');seq.append(hi);last=hi
  else:last=lo
  self.cap(id+'.cover',last+'.b');self.columns[id]={'x':x,'y':y,'tubes':seq};return id
 def host_at(self,col,z,half):
  c=self.columns[col]
  for tube in c['tubes']:
   p=self.parts[tube];a=p.origin[2];b=a+p.data['length']
   if z-half>=a+10 and z+half<=b-10:return tube,(c['x'],c['y'],z)
  raise DesignError(f'{col}: clamp at {z} crosses tube end/coupling or runs off tube')
 def clamp(self,id,col,z,d,holder=False):
  half=self.v('holder_height')/2 if holder else self.v('tee_half_height');host,p=self.host_at(col,z,half)
  for q in self.clamps:
   if holder and q['host']==host and abs(q['z']-z)<.001 and self.parts[q['id']].kind=='end_holder' and dot(self.parts[q['id']].direction,d)<-.999:
    self.parts[q['id']].kind='middle_holder'
    # The first neighbouring shelf was created using an end-holder screw position.
    # Update that support when this shared fitting becomes a middle holder.
    for board in self.boards.values():
     adjusted=[]
     for sid,x,y,zz in board['supports']:
      if sid==q['id']:
       part=self.parts[sid];v=unit(sub((x,y,part.origin[2]),part.origin));point=add(part.origin,mul(v,self.v('middle_holder_wing')));x,y=point[:2]
      adjusted.append((sid,x,y,zz))
     board['supports']=adjusted
    return q['id']
   if q['host']==host and abs(q['z']-z)<q['half']+half+2:raise DesignError(f'Overlapping clamps: {id} / {q["id"]}')
  kind='end_holder' if holder else 'slide_tee';self.part(id,kind,p,(0,0,1),d,host=host)
  self.clamps.append({'id':id,'host':host,'z':z,'half':half});self.edges.append((host,id,'clamp',None,None))
  if not holder:self.port(id+'.branch',id,'female',add(p,mul(d,self.v('tee_stop'))),d)
  return id
 def body_tee(self,id,tube,distance,direction):
  p=self.parts[tube];axis=p.axis;half=self.v('tee_half_height')
  if abs(dot(axis,direction))>.001:raise DesignError('Branch must be perpendicular to sleeve')
  if distance-half<10 or distance+half>p.data['length']-10:raise DesignError('Sliding sleeve must stay on tube body')
  point=add(p.origin,mul(axis,distance))
  for q in self.clamps:
   if q['host']==tube and norm(sub(self.parts[q['id']].origin,point))<q['half']+half+2:raise DesignError('Overlapping sleeve')
  self.part(id,'slide_tee',point,axis,direction,host=tube);self.clamps.append({'id':id,'host':tube,'z':point[2],'half':half});self.edges.append((tube,id,'clamp',None,None));self.port(id+'.branch',id,'female',add(point,mul(direction,self.v('tee_stop'))),direction)
 def bridge(self,id,c1,c2,z,L):
  p=(self.columns[c1]['x'],self.columns[c1]['y'],z);q=(self.columns[c2]['x'],self.columns[c2]['y'],z);d=unit(sub(q,p))
  if abs(norm(sub(q,p))-2*self.v('tee_stop')-L)>.001:raise DesignError('Stock pipe cannot bridge these post centres')
  self.clamp(id+'.t1',c1,z,d);self.clamp(id+'.t2',c2,z,mul(d,-1));self.from_port(id+'.tube',L,id+'.t1.branch');self.connect(id+'.tube.b',id+'.t2.branch')
 def walltie(self,id,col,z,L=40):
  self.clamp(id+'.tee',col,z,(1,0,0));t=self.from_port(id+'.tube',L,id+'.tee.branch');p=self.ports[t+'.b'].p
  wall=add(p,(self.v('flange_stop'),0,0));self.flange(id+'.wall',wall,(-1,0,0),'wall');self.connect(t+'.b',id+'.wall.socket')
 def board(self,id,bounds,bottom,thickness,supports,holes=(),recess=None,rotation_degrees=0):
  # supports: (component ID, x, y, support plane z); points must be on wood.
  x0,x1,y0,y1=bounds
  if x1<=x0 or y1<=y0 or thickness<=0:raise DesignError('Invalid board dimensions')
  minimum=3 if supports and len({s[0] for s in supports})==1 and self.parts.get(supports[0][0]) and self.parts[supports[0][0]].kind=='flange' else 4
  if len(supports)<minimum:raise DesignError('Each board requires four support points, or one three-hole flange')
  for sid,x,y,z in supports:
   if sid not in self.parts or self.parts[sid].kind not in ('end_holder','middle_holder','hook','flange','saddle'):raise DesignError('Wood needs catalog shelf hardware')
   if not point_in_board(x,y,{'bounds':bounds,'rotation_degrees':rotation_degrees}) or abs(z-bottom)>.001:raise DesignError('Wood support outside board / wrong support plane')
  for other in self.boards.values():
   a=other['bounds'];b=other['bottom'];t=other['thickness']
   if min(x1,a[1])-max(x0,a[0])>.01 and min(y1,a[3])-max(y0,a[2])>.01 and min(bottom+thickness,b+t)-max(bottom,b)>.01:raise DesignError('Boards overlap')
  p=((x0+x1)/2,(y0+y1)/2,bottom+thickness/2);self.part(id,'wood',p,bounds=bounds,bottom=bottom,thickness=thickness,holes=list(holes),recess=recess,rotation_degrees=rotation_degrees)
  data=dict(bounds=bounds,bottom=bottom,thickness=thickness,supports=supports,holes=list(holes),recess=recess,rotation_degrees=rotation_degrees);self.boards[id]=data
  for s,*_ in supports:self.edges.append((s,id,'wood screw',None,None))
 def supported_board(self,id,cols,bounds,bottom,thickness,holes=()):
  supports=[];cy=(bounds[2]+bounds[3])/2
  for i,c in enumerate(cols):
   d=(0,1 if self.columns[c]['y']<cy else -1,0);h=id+'.holder'+str(i+1);h=self.clamp(h,c,bottom-self.v('holder_height')/2,d,True)
   p=add(self.parts[h].origin,mul(d,self.v('middle_holder_wing' if self.parts[h].kind=='middle_holder' else 'holder_wing')));supports.append((h,p[0],p[1],bottom))
  self.board(id,bounds,bottom,thickness,supports,holes)
 def saddle(self,id,tube,distance,direction):
  p=self.parts[tube];half=self.v('saddle_half_width');d=unit(direction)
  if not p.kind.startswith('tube_') or abs(p.axis[2])>.001 or abs(d[2])>.001 or abs(dot(d,p.axis))>.001:raise DesignError('Saddle needs a horizontal host pipe and perpendicular horizontal tab')
  if distance-half<10 or distance+half>p.data['length']-10:raise DesignError('Saddle runs off pipe body')
  point=add(p.origin,mul(p.axis,distance))
  for c in self.clamps:
   if c['host']==tube and norm(sub(point,self.parts[c['id']].origin))<half+c['half']+2:raise DesignError('Saddle overlaps another fitting')
  self.part(id,'saddle',point,p.axis,d,host=tube,distance=distance)
  self.clamps.append({'id':id,'host':tube,'z':point[2],'half':half});self.edges.append((tube,id,'saddle around horizontal pipe',None,None))
  return add(add(point,mul(d,self.v('saddle_tab_offset'))),(0,0,self.v('saddle_rise')))
 def shelf_crossbar(self,c1,c2,z,L=250):
  if not hasattr(self,'shelf_crossbars'):self.shelf_crossbars={}
  key=(c1,c2,round(z,6))
  if key not in self.shelf_crossbars:
   stem='ShelfCross.'+c1+'.'+c2+'.'+str(round(z,3));self.bridge(stem,c1,c2,z,L);self.shelf_crossbars[key]=stem+'.tube'
  return self.shelf_crossbars[key]
 def saddle_board(self,id,pairs,bounds,bottom,thickness,holes=(),recess=None):
  supports=[];cy=(bounds[2]+bounds[3])/2
  for i,(c1,c2) in enumerate(pairs):
   host=self.shelf_crossbar(c1,c2,bottom-self.v('saddle_rise'));toward=1 if self.parts[host].origin[1]<cy else -1
   # Stagger opposing tabs on shared pipes so the metal straps do not overlap.
   for j,offset in enumerate((45,205) if toward>0 else (75,175)):
    k=id+'.saddle'+str(i)+'.'+str(j);point=self.saddle(k,host,offset,(0,toward,0));supports.append((k,*point))
  self.board(id,bounds,bottom,thickness,supports,holes,recess)
 def light_check(self,board,count=2,driver_watts=30,pocket_depth=20,clip=None):
  if count*5.5>driver_watts:raise DesignError('LED load exceeds driver rating')
  if pocket_depth<14+(clip if clip is not None else self.v('clip_height'))+2:raise DesignError('Light and clips do not fit pocket')
  if self.boards[board]['thickness']-pocket_depth<20:raise DesignError('Less than 20 mm timber above routed pocket')
  return {'article':'605.285.84','count':count,'unit_mm':[600,20,14],'watts':count*5.5,'driver_watts':driver_watts,'pocket_mm':[1320,32,pocket_depth],'status':'CUSTOM RECESS UNVERIFIED: clip/plug measurements and IKEA recessed-installation suitability unresolved','surface_alternative':'Mount original clips below shelf; removable front lip conceals housing'}
 def validate(self,fabrication=False):
  errors=[]
  # Reject tampered tube geometry and end positions as well as free structural thread ports.
  for p in self.parts.values():
   if p.kind.startswith('tube_'):
    L=int(p.kind[5:])
    if p.data['length']!=L:errors.append(p.id+': stock length changed')
    for suffix,pt,n in [('a',p.origin,mul(p.axis,-1)),('b',add(p.origin,mul(p.axis,L)),p.axis)]:
     v=self.ports[p.id+'.'+suffix]
     if not close(v.p,pt) or not close(v.n,n):errors.append(p.id+': tube moved independently of its ports')
  for p in self.ports.values():
   if p.kind=='female' and not p.used:errors.append(p.id+': unused structural socket')
   if p.kind=='male' and not p.used:errors.append(p.id+': open tube end')
   if p.used in self.ports:
    q=self.ports[p.used]
    if not close(p.p,q.p) or dot(p.n,q.n)>-.999999 or p.family!=q.family:errors.append(p.id+': broken mate')
  # Clamp stations must still be valid after an editor adjustment.
  for i,c in enumerate(self.clamps):
   h=self.parts[c['host']];p=self.parts[c['id']];z=p.origin[2]
   station=dot(sub(p.origin,h.origin),h.axis)
   if not close(p.origin,add(h.origin,mul(h.axis,station))) or station-c['half']<10 or station+c['half']>h.data['length']-10:errors.append(c['id']+': clamp outside host body')
   for q in self.clamps[i+1:]:
    if c['host']==q['host'] and norm(sub(p.origin,self.parts[q['id']].origin))<c['half']+q['half']+2:errors.append(c['id']+': overlapping clamp '+q['id'])
  for p in self.parts.values():
   if p.kind=='slide_tee':
    v=self.ports[p.id+'.branch']
    if not close(v.p,add(p.origin,mul(p.direction,self.v('tee_stop')))) or not close(v.n,p.direction):errors.append(p.id+': tee port moved independently')
   if p.kind=='flange':
    v=self.ports[p.id+'.socket']
    if not close(v.p,add(p.origin,mul(p.axis,self.v('flange_stop')))):errors.append(p.id+': flange port moved independently')
    if self.mounts.get(p.id)=='wall' and abs(p.origin[0]-3450)>.001:errors.append(p.id+': flange detached from wall')
    if self.mounts.get(p.id)=='floor' and abs(p.origin[2])>.001:errors.append(p.id+': flange detached from floor')
  for p in self.parts.values():
   if p.kind=='saddle':
    host=self.parts.get(p.data.get('host'))
    if not host or not host.kind.startswith('tube_') or abs(host.axis[2])>.001:errors.append(p.id+': saddle has no horizontal pipe host')
    elif not close(p.origin,add(host.origin,mul(host.axis,p.data['distance']))):errors.append(p.id+': saddle detached from host')
  for bid,wood in self.boards.items():
   for sid,x,y,z in wood['supports']:
    p=self.parts[sid]
    if p.kind=='saddle':
     actual=add(add(p.origin,mul(p.direction,self.v('saddle_tab_offset'))),(0,0,self.v('saddle_rise')))
     if not close((x,y,z),actual):errors.append(bid+': saddle screw point disconnected')
  adjacency=defaultdict(set)
  for a,b,*_ in self.edges:adjacency[a].add(b);adjacency[b].add(a)
  reached={k for k,v in self.mounts.items() if v in ('floor','wall')};todo=list(reached)
  while todo:
   for b in adjacency[todo.pop()]-reached:reached.add(b);todo.append(b)
  errors.extend(p+': no connection to a mounting surface' for p in self.parts if p not in reached)
  # All tubes are axis aligned in this builder. Unrelated crossing pipes must not intersect.
  tubes=[p for p in self.parts.values() if p.kind.startswith('tube_')]
  for i,a in enumerate(tubes):
   for b in tubes[i+1:]:
    if tube_boxes_overlap(a,b):
     errors.append('Pipe bodies intersect: '+a.id+' / '+b.id)
  for id,board in self.boards.items():
   x0,x1,y0,y1=board['bounds']
   for sid,x,y,z in board['supports']:
    if not point_in_board(x,y,board) or abs(z-board['bottom'])>.001:errors.append(id+': support outside wood or noncoplanar')
  # Board penetration only allowed at explicit bored post positions or legal supporting pipes.
  for id,b in self.boards.items():
   x0,x1,y0,y1=b['bounds'];z0=b['bottom'];z1=z0+b['thickness']
   for t in tubes:
    if abs(t.axis[2])<.99:continue
    x,y,z=t.origin;end=z+t.data['length']
    if point_in_board(x,y,b,12.5) and min(end,z1)>max(z,z0):
     if not any(math.hypot(x-h[0],y-h[1])<.01 and h[2]>=30 for h in b['holes']):errors.append('Unbored post through wood: '+id+' / '+t.id)
  unresolved=[k for k,v in self.profile.items() if v['status']!='measured']
  if fabrication:
   errors+=['Uncalibrated profile: '+k for k in unresolved]
   errors+=['Fixing specification / load assessment not verified','Custom MITTLED recess installation not verified','Exact MIDI and speakers not measured']
  return {'geometry_errors':sorted(set(errors)),'profile_unresolved':unresolved,'fabrication_ready':False,'scope':'Connection graph, stock lengths, clamp separation, pipe intersections, board supports/bores; fitting surface meshes and structural loads not certified'}
 def move_rail(self,id,z):
  """Transactional edit of a straight rail between two sliding T branches."""
  candidate=copy.deepcopy(self);t=candidate.parts[id]
  if not t.kind.startswith('tube_') or abs(t.axis[2])>.001:raise DesignError('Select a horizontal rail')
  mates=[candidate.ports[candidate.ports[id+'.'+e].used].owner for e in ('a','b') if candidate.ports[id+'.'+e].used in candidate.ports]
  if len(mates)!=2 or any(candidate.parts[x].kind!='slide_tee' for x in mates):raise DesignError('Rail must join two sliding tees')
  dz=z-t.origin[2]
  for pid in [id]+mates:
   p=candidate.parts[pid];p.origin=add(p.origin,(0,0,dz))
   for port in candidate.ports.values():
    if port.owner==pid:port.p=add(port.p,(0,0,dz))
   for c in candidate.clamps:
    if c['id']==pid:c['z']+=dz
  result=candidate.validate()
  if result['geometry_errors']:raise DesignError('; '.join(result['geometry_errors'][:3]))
  self.__dict__=candidate.__dict__
 @classmethod
 def load(cls,path):
  d=json.loads(Path(path).read_text());a=cls(d['profile'])
  a.parts={p['id']:Part(**p) for p in d['parts']};a.ports={p['id']:Port(**p) for p in d['ports']}
  for k in ('edges','mounts','clamps','boards','lights','columns','notes'):
   setattr(a,k,d['connections' if k=='edges' else k])
  return a
 def bom(self):return Counter(p.kind for p in self.parts.values())
 def save(self,path):
  d={'units':'mm','profile':self.profile,'catalog':CATALOG,'parts':[asdict(p) for p in self.parts.values()],'ports':[asdict(p) for p in self.ports.values()],'connections':self.edges,'mounts':self.mounts,'clamps':self.clamps,'boards':self.boards,'lights':self.lights,'columns':self.columns,'notes':self.notes,'validation':self.validate()}
  Path(path).write_text(json.dumps(d,indent=2))
def tube_boxes_overlap(a,b):
 # Conservative flat-ended, axis-aligned cylinder boxes. Unlike capsules,
 # these do not invent rounded tube ends inside legal socket gaps.
 def box(p):
  end=add(p.origin,mul(p.axis,p.data['length']))
  return [(min(p.origin[i],end[i])-(0 if abs(p.axis[i])>.99 else 12.5),max(p.origin[i],end[i])+(0 if abs(p.axis[i])>.99 else 12.5)) for i in range(3)]
 aa,bb=box(a),box(b)
 return all(min(x[1],y[1])-max(x[0],y[0])>.01 for x,y in zip(aa,bb))
def segment_distance(a,b,c,d):
 # General closest points on finite segments, including parallel/degenerate cases.
 u,v,w=sub(b,a),sub(d,c),sub(a,c);A,B,C,D,E=dot(u,u),dot(u,v),dot(v,v),dot(u,w),dot(v,w);den=A*C-B*B
 s=max(0,min(1,(B*E-C*D)/den)) if den>1e-9 else 0
 t=max(0,min(1,(B*s+E)/C)) if C else 0
 s=max(0,min(1,(B*t-D)/A)) if A else 0
 return norm(sub(add(a,mul(u,s)),add(c,mul(v,t))))
def profile_from_measurements(path):
 profile=copy.deepcopy(PROFILE);path=Path(path)
 if not path.exists():return profile
 d=json.loads(path.read_text())
 for key,value in d.get('values_mm',{}).items():
  if key not in profile:raise DesignError('Unknown measurement '+key)
  if value is None:continue
  if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value<=0:raise DesignError('Measurement must be a positive number: '+key)
  profile[key]['value']=value;profile[key]['status']='measured';profile[key]['measurement_note']=d.get('notes',{}).get(key,'Entered in Measurements-v8.json')
 return profile
def build(profile=None,close_gap=False,entry60=False,side_speakers=False,shared_desk=False):
 if shared_desk:return build_shared_desk(profile)
 if side_speakers:entry60=True
 if entry60:close_gap=True
 a=Assembly(profile);s=a.v('tee_stop');f=a.v('flange_stop');back=3450-(40+s+f);front=back-(250+2*s);df=back-(602+2*s)
 shift=250 if entry60 else 0
 y0=(1100 if close_gap else 980)+shift;y1=980+1500+2*s+shift;dy=[2640+shift]
 coat_length=602 if entry60 else 802
 for L in (1000,602,coat_length):dy.append(dy[-1]+L+2*s)
 for row,x in [('F',df),('B',back)]:
  for i,y in enumerate((y0,y1)):
   a.column(f'D{row}{i}',x,y,upper=1200 if row=='B' and i==0 and not side_speakers else 0,lower=1000 if row=='B' and i==0 and not side_speakers else 802)
 for row,x in [('F',front),('B',back)]:
  for i,y in enumerate(dy):a.column(f'R{row}{i}',x,y)
 # Main desktop still has its own short legs; only its near rear post continues upward.
 base_z=712-a.v('saddle_rise');supports=[]
 for i in range(2):
  stem=f'Desk.endframe{i}';a.bridge(stem,f'DF{i}',f'DB{i}',base_z,602)
  d=(0,1 if i==0 else -1,0)
  for j,offset in enumerate((70,532)):
   k='Desk.top.saddle'+str(i)+'.'+str(j);p=a.saddle(k,stem+'.tube',offset,d);supports.append((k,*p))
 holes=[(x,y,40) for x in (df,back) for y in (y0,y1)]
 if close_gap:holes += [(front,dy[0],40),(back,dy[0],40)] + ([(front,y0-50,40),(back,y0-50,40)] if side_speakers else [(2815,2580+shift,70)])
 if close_gap:
  # New support under the integrated wardrobe uprights, behind the retained desk endframe.
  a.bridge('Desk.tail','RF0','RB0',base_z,250)
  for j,offset in enumerate((75,175)):
   sid='Desk.top.tail_saddle'+str(j);pt=a.saddle(sid,'Desk.tail.tube',offset,(0,-1,0));supports.append((sid,*pt))
 a.board('Desk.top',(df-30,back+30,y0-45,(dy[0] if close_gap else y1)+30),712,28,supports,holes)
 # Preview underside reliefs clear the tee branch castings; no visible top pockets.
 reliefs=[]
 for i in range(2):
  for col,sign in ((f'DF{i}',1),(f'DB{i}',-1)):
   x=a.columns[col]['x'];yy=a.columns[col]['y'];zmax=base_z+17.5
   if zmax>712:reliefs.append({'bounds':[min(x,x+sign*31),max(x,x+sign*31),yy-18,yy+18,711,zmax]})
 if close_gap:
  for col,sign in (('RF0',1),('RB0',-1)):
   x=a.columns[col]['x'];yy=a.columns[col]['y'];reliefs.append({'bounds':[min(x,x+sign*31),max(x,x+sign*31),yy-18,yy+18,711,base_z+17.5]})
 a.parts['Desk.top'].data['support_reliefs']=reliefs;a.boards['Desk.top']['support_reliefs']=reliefs
 # New near shelf post is a stock 1500 mm riser anchored onto the desktop.
 if side_speakers:
  a.column('DS0',front,y0-50);a.column('SB0',back,y0-50)
 else:
  a.flange('DS0.base',(front,y0,740),(0,0,1),'wood');a.edges.append(('Desk.top','DS0.base','wood screw',None,None))
  a.from_port('DS0.riser',1500,'DS0.base.socket');a.cap('DS0.cover','DS0.riser.b');a.columns['DS0']={'x':front,'y':y0,'tubes':['DS0.riser']}
 for z in ((1200,2020) if side_speakers else (1100,2020)):a.walltie(f'Desk.wall0.{z}','SB0' if side_speakers else 'DB0',z)
 # Lower rear stiffener retained, upper far-end post/brace removed.
 if close_gap:
  # The moved near frame no longer accepts the old uncut 1500 rear brace.
  a.walltie('Desk.lower_wall0','DB0',550);a.walltie('Desk.lower_wall1','DB1',550)
 else:a.bridge('Desk.back.550','DB0','DB1',550,1500)
 # Real cross-pipes with a sliding T on BOTH ends; far end reuses RF0/RB0.
 gap=a.v('tee_outer_radius')+1
 for j,(bottom,th) in enumerate(((1540,40),(1880,28),(2190,28))):
  bounds=(front-30,back+30,y0+gap-(50 if side_speakers else 0),dy[0]-gap)
  cy=(bounds[2]+bounds[3])/2
  a.saddle_board('Desk.shelf'+str(j),[('DS0','SB0' if side_speakers else 'DB0'),('RF0','RB0')],bounds,bottom,th,recess={'length':1320,'width':32,'depth':20,'centre':[back-215,cy]} if j==0 else None)
 for i in range(4):
  for z in ((200,) if i in (0,1) else () if i==2 else (1800,)):a.bridge(f'Rack.depth{i}.{z}',f'RF{i}',f'RB{i}',z,250)
  a.walltie(f'Rack.wall{i}',f'RB{i}',1970 if i==0 else 1700 if i in (1,2) else 1900)
 for j,L in ((0,1000),(2,coat_length)):
  for z in ((950,1950) if j==0 else (1950,)):a.bridge(f'Rack.clean{j}.{z}',f'RF{j}',f'RF{j+1}',z,L)
 for j in range(3):
  bounds=(front-30,back+30,dy[j]+gap,dy[j+1]-gap);pairs=[(f'RF{j}',f'RB{j}'),(f'RF{j+1}',f'RB{j+1}')]
  a.saddle_board('Rack.top'+str(j),pairs,bounds,2190,28)
  if j==1:
   for k,z in enumerate((700,1100,1500,1850)):a.saddle_board('Rack.fold'+str(k),pairs,bounds,z,28)
  if j==2:a.saddle_board('Rack.coat_shoes',pairs,bounds,200,28)
 # Wear-again rail: sliding tees on the two 200 mm return pipes.
 # The SAME tee stop sets both the bay width and rail width. No unverified
 # assumption that a cast elbow and a sliding tee have equal offsets.
 for j,col in enumerate(('RF1','RF2')):
  id='Wear.return'+str(j);a.clamp(id+'.tee',col,1250,(-1,0,0));a.from_port(id+'.tube',200,id+'.tee.branch');a.cap(id+'.cap',id+'.tube.b');nd=(0,1 if j==0 else -1,0);a.body_tee(id+'.outer',id+'.tube',140,nd)
 a.from_port('Wear.rail',602,'Wear.return0.outer.branch');a.connect('Wear.rail.b','Wear.return1.outer.branch')
 # Floating speaker shelves: two 250 mm side arms and four saddles per tray.
 if side_speakers:
  desktop=a.boards['Desk.top']['bounds'];middle=(desktop[2]+desktop[3])/2;listener_x=2750;cx=back-200;half=175
  cy=desktop[2]+half
  for _ in range(100):
   theta=math.atan2(middle-cy,cx-listener_x);cy=desktop[2]+half*(math.cos(theta)+math.sin(theta))
  for i,(yy,angle,cols,sign) in enumerate(((cy,-math.degrees(theta),('DS0','SB0'),1),(2*middle-cy,math.degrees(theta),('RF0','RB0'),-1))):
   supports=[];bottom=1100;z=bottom-a.v('saddle_rise');id='Speaker'+str(i)
   for j,col in enumerate(cols):
    stem=id+'.arm'+str(j);a.clamp(stem+'.tee',col,z,(0,sign,0));a.from_port(stem+'.tube',250,stem+'.tee.branch');a.cap(stem+'.cap',stem+'.tube.b')
    for k,offset in enumerate((180,230) if i==0 else (110,210)):
     sid=stem+'.saddle'+str(k);point=a.saddle(sid,stem+'.tube',offset,(1 if j==0 else -1,0,0));supports.append((sid,*point))
   a.board(id+'.platform',(cx-half,cx+half,yy-half,yy+half),bottom,25,supports,rotation_degrees=angle)
   a.parts[id+'.platform'].data['speaker_target_mm']=[listener_x,middle,1250]
 else:
  for i,y in enumerate((1350+shift,2360+shift) if close_gap else ((y0+y1)/2-520,(y0+y1)/2+610)):
   id='Speaker'+str(i);x=back-195;a.flange(id+'.base',(x,y,740),(0,0,1),'wood');a.edges.append(('Desk.top',id+'.base','wood screw',None,None))
   a.from_port(id+'.riser',250,id+'.base.socket');p=a.ports[id+'.riser.b'].p;bottom=p[2]+f
   a.flange(id+'.top',(x,y,bottom),(0,0,-1),'wood');a.connect(id+'.riser.b',id+'.top.socket')
   supports=[(id+'.top',x+25*math.cos(t),y+25*math.sin(t),bottom) for t in (0,math.tau/3,2*math.tau/3)]
   a.board(id+'.platform',(x-175,x+175,y-175,y+175),bottom,25,supports)
 light=a.light_check('Desk.shelf0');a.lights=[light]
 a.notes=['V11 wardrobe: 1000 mm stock double hanging; 602 mm stock folded storage; 802 mm stock single long-coat hanging at 1950 mm.','Four coat spaces use about 180 mm rail width each. A 1500 mm garment below a 70 mm hanger drop clears 100 mm shoes above the 228 mm shoe-shelf top by 52 mm. These are design envelopes, not measured garments.','Fold shelf bottoms 700 / 1100 / 1500 / 1850 mm, below the 2190 mm top board. Clear openings are 372 / 372 / 322 / 312 mm at the back, with 272 mm at the highest front opening behind the light lip.','V11: horizontal cross-pipes seat into two sliding T-connectors; one-sided saddle holders screw into each board.','Desk upper shelves reuse wardrobe RF0/RB0. Their top cross-pipe is shared with Rack.top0; opposing saddle straps are staggered.','DS0 is a stock 1500 mm riser on a desktop flange. Its fasteners and desktop load transfer require physical verification.','Desk far rear post shortened to 802 mm; no duplicate full-height post beside the wardrobe.','No split end/middle holders are assumed. Toom 7450897 is the saddle reference; its exact dimensions remain preview fields.','Lowest desk shelf retains the custom MITTLED recess. No final routing/loads verified.']
 if close_gap:a.notes += ['V15: desktop moved 120 mm toward balcony, full 1615 x 702 size retained; six saddle supports.','RF0/RB0 pass through explicit bored desktop holes and provide a tail cross-pipe; old endframe retained 120 mm before these posts.','Near desk support frame moves from y980 to y1100; far frame stays y2520. Two low wall ties replace the rear 1500 brace because its new span is not a stock tube length.','A 70 mm desktop bore reserves clearance for the separate 40 square TV-door support post; this is not a DOLLE post.','Kitchen-corner to desktop-corner gap improves only from about 355 to 434 mm; this does not resolve comfortable entry circulation.']
 if entry60:
  a.notes=[n for n in a.notes if not n.startswith(('V11 wardrobe:', 'Four coat spaces', 'V15:', 'Near desk support', 'Kitchen-corner'))]
  a.notes += ['V16: window-side coat bay uses the NEXT SMALLER uncut catalog tube: 602 mm, DOLLE 96599, replacing 802 mm 96605. No structural pipe is cut or stretched.', 'Desk and first three wardrobe post pairs move 250 mm toward balcony; last post pair moves only 50 mm because coat bay is 200 mm shorter.', 'Desktop remains 1615 x 702 mm with six saddle supports and explicit post holes. Modeled kitchen/desk corner gap 640.9 mm.', 'Four long-coat slots now use about 140 mm pitch each; bulky coats may require fewer slots. Hanging height remains unchanged.', 'Wear-again item is restricted to a 200 mm entrance-side zone so the balcony handle sweep stays clear in the 100-degree proxy test. Ceiling and connector offsets remain unmeasured.']
 if side_speakers:
  a.notes=[n for n in a.notes if not n.startswith(('DS0 is a stock 1500','A 70 mm desktop'))]
  a.notes += ['V17 TV and all its custom support parts removed; the desktop TV bore is removed.', 'DS0 is now a floor-mounted 1000 + 1200 mm stock column with coupling, near support pair offset 50 mm from the desktop endframe to avoid crossing its pipes; eight 40 mm desktop holes include the two open-edge notches. Speaker shelves do not bear on the desktop.', 'Each speaker board is a 350 x 350 x 25 mm oak tray on two uncut 250 mm cantilever arms, each clamped to its own upright by a sliding T. Four one-sided saddle tabs screw each tray to the arms.', 'Near wall tie raised from 1100 to 1200 mm to clear speaker-arm tees. Tray underside 1100, top 1125 mm before thin isolation pads; no desktop speaker risers or flanges.', 'Trays rotate in the connection graph and their outside Y corners align with the two desktop ends. Speakers aim at the middle chair position. This wide stereo geometry is a visual arrangement, not a calibrated acoustic setup.', 'Cantilever capacity, clamp anti-rotation, saddle screw retention, speaker weight and fixing loads remain unverified. No positive manufacturer cantilever rating has been established.']
 return a
def build_shared_desk(profile=None):
 """Reuse four rack uprights; two elbow-return front legs, no separate rear legs."""
 a=build(profile,side_speakers=True);bounds=a.boards['Desk.top']['bounds']
 prefixes=('DF0','DF1','DB0','DB1','Desk.endframe','Desk.top','Desk.tail','Desk.lower_wall')
 removed={id for id in a.parts if id.startswith(prefixes)}
 a.parts={id:p for id,p in a.parts.items() if id not in removed};a.ports={id:p for id,p in a.ports.items() if p.owner not in removed}
 a.edges=[edge for edge in a.edges if edge[0] not in removed and edge[1] not in removed];a.mounts={id:surface for id,surface in a.mounts.items() if id not in removed}
 a.clamps=[c for c in a.clamps if c['id'] not in removed and c['host'] not in removed]
 a.columns={id:c for id,c in a.columns.items() if not id.startswith(('DF','DB'))};del a.boards['Desk.top']
 # Derive the support height from actual stock lengths and the editable fitting profile.
 f=a.v('flange_stop');gap=a.v('extension_gap');e=a.v('elbow_stop');s=a.v('tee_stop')
 axis_z=f+602+gap+40+e;bottom=axis_z+a.v('saddle_rise');supports=[]
 for i,(front,back,direction) in enumerate((('DS0','SB0',1),('RF0','RB0',-1))):
  y=a.columns[front]['y']
  for j,(col,length) in enumerate(((front,250),(back,200))):
   stem=f'Desk.shared{i}.{j}';a.clamp(stem+'.tee',col,axis_z,(-1,0,0));a.from_port(stem+'.tube',length,stem+'.tee.branch')
   for k,offset in enumerate((45,205) if j==0 else (45,155)):
    sid=stem+'.saddle'+str(k);point=a.saddle(sid,stem+'.tube',offset,(0,direction,0));supports.append((sid,*point))
   if j==1:a.cap(stem+'.cap',stem+'.tube.b')
   else:
    # A stock elbow returns the outward arm down to an uncut 40 + 602 mm leg.
    arm_end=a.ports[stem+'.tube.b'].p;x=arm_end[0]-e;id='DF'+str(i)
    a.flange(id+'.foot',(x,y,0),(0,0,1),'floor');a.from_port(id+'.lower',602,id+'.foot.socket')
    end=a.ports[id+'.lower.b'].p;ex=id+'.extension';a.part(ex,'extension',add(end,(0,0,gap/2)),gap=gap)
    a.port(ex+'.down',ex,'female',end,(0,0,-1));a.port(ex+'.up',ex,'female',add(end,(0,0,gap)),(0,0,1));a.connect(id+'.lower.b',ex+'.down');a.from_port(id+'.upper',40,ex+'.up')
    elbow=id+'.elbow';centre=(x,y,axis_z);a.part(elbow,'elbow',centre,(0,0,-1),(1,0,0))
    a.port(elbow+'.down',elbow,'female',(x,y,axis_z-e),(0,0,-1));a.port(elbow+'.in',elbow,'female',(x+e,y,axis_z),(1,0,0));a.connect(id+'.upper.b',elbow+'.down');a.connect(stem+'.tube.b',elbow+'.in')
    a.columns[id]={'x':x,'y':y,'tubes':[id+'.lower',id+'.upper']}
  # Low stock braces keep the reused front/rear rack posts linked below the desk.
  a.bridge(f'Desk.low_depth{i}',front,back,300,250);a.walltie(f'Desk.low_wall{i}',back,450)
 holes=[(a.columns[c]['x'],a.columns[c]['y'],44) for c in ('DS0','SB0','RF0','RB0')]
 a.board('Desk.top',bounds,bottom,28,supports,holes)
 # Preview underside reliefs for elbows and branch castings; the top face is continuous.
 reliefs=[]
 for c in ('DS0','SB0','RF0','RB0'):
  x=a.columns[c]['x'];y=a.columns[c]['y'];reliefs.append({'bounds':[x-31,x,y-18,y+18,bottom-1,axis_z+17.5]})
 for c in ('DF0','DF1'):
  x=a.columns[c]['x'];y=a.columns[c]['y'];reliefs.append({'bounds':[x-18,x+31,y-18,y+18,bottom-1,axis_z+17.5]})
 a.parts['Desk.top'].data['support_reliefs']=reliefs;a.boards['Desk.top']['support_reliefs']=reliefs
 a.notes=[n for n in a.notes if not n.startswith(('Desk far rear post','RF0/RB0 pass','Desktop remains 1615','DS0 is now'))]
 a.notes += ['V18: all four former short desktop columns and both 602 mm endframe cross-pipes removed. Existing DS0/SB0 and RF0/RB0 rack posts now support the desktop through sliding-T arms.', 'Each end uses one 250 mm outward arm from the front rack post, returned down through a stock elbow to a 40 + 602 mm front leg, plus one 200 mm inward arm from the rear rack post. Eight saddle holders support the desktop.', f'Derived desktop underside {bottom:g} mm / top {bottom+28:g} mm. Front support legs terminate under the tabletop through elbows: no front-leg bores or protrusions. Four 44 mm preview clearance bores remain only for the continuing rack posts, including near-edge notches.', 'Two 250 mm low depth ties and two 40 mm low wall ties brace the existing rack frame. Four old short desk legs are replaced by two front returns; no separate rear desk legs.', 'The desktop still measures 1615 x 702 x 28 mm in the same plan position. Main entry corner gap remains 640.9 mm. Closest modeled front foot clearance exceeds 600 mm.', 'Model connection and clearance checks are not a load certification. Verify desk saddle screws, clamp slip/rotation, wall anchorage and leaning loads before construction. Fully floating desk is not assumed approved.']
 return a
if __name__=='__main__':
 out=Path(__file__).parent;a=build(profile_from_measurements(out/'Measurements-v8.json'));a.save(out/'Assembly-v8.json');(out/'Validation-v8.json').write_text(json.dumps(a.validate(),indent=2));print(json.dumps(a.validate(),indent=2));print(dict(a.bom()))
