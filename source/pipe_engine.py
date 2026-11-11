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
def room_geometry(path=Path(__file__).parent/'room-measurements.json'):
 """Right-wall plane and ceiling: measured readings win; otherwise the labelled CAD assumption."""
 d=json.loads(Path(path).read_text());m=d['measured'];a=d['assumed']
 widths=[v for k,v in m.items() if k.startswith('room_width_x') and v is not None];ceilings=[v for k,v in m.items() if k.startswith('ceiling') and v is not None]
 return {'wall_x':sum(widths)/len(widths) if widths else a['room_width_x'],'wall_measured':bool(widths),'wall_spread':max(widths)-min(widths) if widths else None,
  'ceiling':min(ceilings) if ceilings else a['ceiling_height'],'ceiling_measured':bool(ceilings)}
ROOM=room_geometry();WALL_X=ROOM['wall_x']
# Seated listening/viewing reference: ear above the rear third of the parked chair seat.
EAR_MM=(2620,1220)
ENTRY_CORNER_RADIUS=100
# Speaker trays sit inside the shelf column: 370 mm square is the smallest board that takes a 280 x 220 mm speaker aimed at the ear.
SPEAKER_TRAY=370
# Rear service shelf on separate wall brackets (allowance, type not selected): arm reach from the wall to the shelf screw point.
SERVICE_BRACKET_REACH=200
STOCK={40:('96193','https://www.obi.de/p/4964102/dolle-rohr-tube-fuer-pipe-regalsystem-25-mm-x-40-mm-schwarz-matt'),200:('96247','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-200-mm-20-mm-3-4-schwarz-matt-0763202832/'),250:('96254','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-250-mm-20-mm-3-4-schwarz-matt-0763202837/'),602:('96599','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-602-mm-20-mm-3-4-schwarz-matt-0763202834/'),802:('96605','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-802-mm-20-mm-3-4-schwarz-matt-0763202835/'),1000:('96292','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-1000-mm-20-mm-3-4-schwarz-matt-0763202825/'),1200:('96322','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-1200-mm-20-mm-3-4-schwarz-matt-0763202841/'),1500:('96339','https://www.globus-baumarkt.de/p/dolle-rohr-fuer-pipe-regalsystem-oe-25-x-1500-mm-20-mm-3-4-schwarz-matt-0763202820/')}
PROFILE={
 'saddle_rise':{'value':15,'status':'preview','measure':'Horizontal tube axis to wood underside at the saddle tab'},
 'saddle_tab_offset':{'value':32,'status':'preview','measure':'Tube axis to shelf screw hole, perpendicular to tube'},
 'saddle_half_width':{'value':7,'status':'preview','measure':'Half the strap width along the horizontal tube'},
 'flange_stop':{'value':15,'status':'preview','measure':'Mounting face to fully seated tube end'},
 'cross_stop':{'value':20,'status':'preview','measure':'DOLLE 96384 cross centre to seated tube end; verify on all four sockets'},
 'cross_engagement':{'value':10,'status':'preview','measure':'DOLLE 96384 cross socket mouth to seating stop'},
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
 'cross':{'sku':'96384 / EAN 4007557096384 — UNCONFIRMED: Bauhaus SE lists this EAN as a 4×3/4" corner coupling','name':'DOLLE PIPE four-way threaded cross, four female sockets (article to confirm)','source':'https://toom.de/p/kreuzverbinder-fuer-regalsystem-pipe-34-schwarz/7450886'},
 'slide_tee':{'sku':'96544','name':'DOLLE sliding T, one female branch, Ø25 sleeve','source':'https://www.globus-baumarkt.de/p/dolle-t-verbinder-fuer-pipe-regalsystem-20-mm-3-4-verschiebbar-schwarz-matt-0763202823/'},
 'extension':{'sku':'96445','name':'DOLLE Extension, TWO FEMALE THREADS','source':'https://www.obi.de/p/4978219/dolle-doppelmuffe-extension-fuer-pipe-regalsystem-20-mm-3-4-schwarz-matt'},
 'elbow':{'sku':'96353','name':'DOLLE 90 degree elbow, two female threads','source':'https://www.obi.de/p/4974440/dolle-90-eckverbinder-fuer-pipe-regalsystem-2-innengewinden-20-mm-3-4-schwarz'},
 'end_holder':{'sku':'supplier item 115610071; DOLLE no. pending','name':'DOLLE PIPE split end shelf holder, one assembled holder','source':'https://www.sonderpreis-baumarkt.de/renovieren-und-wohnen/inneneinrichtung/wohneinrichtung/regale/regalbodenhalter-endstueck-pipe-%C3%B8-25-mm-schwarz-2er-set-115610071.html'},
 'middle_holder':{'sku':'supplier item 115610070; DOLLE no. pending','name':'DOLLE PIPE split middle shelf holder, one assembled holder','source':'https://www.sonderpreis-baumarkt.de/renovieren-und-wohnen/inneneinrichtung/wohneinrichtung/regale/regalbodenhalter-mittelstueck-pipe-%C3%B8-25-mm-schwarz-115610070.html'},
 'hook':{'sku':'96490','name':'DOLLE shelf hook, 4 hooks + 8 screws per set','source':'https://www.globus-baumarkt.de/p/dolle-regalbodenhalter-set-fuer-pipe-regalsystem-haken-schrauben-schwarz-matt-0763202817/'},
 'cap':{'sku':'96476','name':'DOLLE end stopper, fit to verify, 2 per pack','source':'https://www.globus-baumarkt.de/p/dolle-abdeckstopfen-fuer-pipe-regalsystem-20-mm-3-4-schwarz-matt-2-stueck-0763202816/'},
 'bracket':{'sku':'allowance; bracket type not selected','name':'Separate wall shelf bracket for the rear service shelf (allowance)','source':None},
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
def corner_centres(board):
 # Rounded plan corners: [corner x, corner y, radius] on an unrotated board.
 x0,x1,y0,y1=board['bounds']
 for x,y,r in board.get('corner_radii',[]):yield x,y,r,x+(r if x==x0 else -r),y+(r if y==y0 else -r)
def point_in_board(x,y,board,margin=0):
 x0,x1,y0,y1=board['bounds'];cx=(x0+x1)/2;cy=(y0+y1)/2;theta=-math.radians(board.get('rotation_degrees',0));c=math.cos(theta);s=math.sin(theta);dx=x-cx;dy=y-cy
 u,v=cx+c*dx-s*dy,cy+s*dx+c*dy
 if not (x0-margin<=u<=x1+margin and y0-margin<=v<=y1+margin):return False
 for x,y,r,ax,ay in corner_centres(board):
  if (u-ax)*(x-ax)>0 and (v-ay)*(y-ay)>0 and math.hypot(u-ax,v-ay)>r+margin:return False
 return True
def board_outline(board,segments=12):
 """Plan outline including rounded corners, counter-clockwise from (x0, y0)."""
 x0,x1,y0,y1=board['bounds'];radii={(x,y):r for x,y,r in board.get('corner_radii',[])};pts=[]
 for (x,y),start in (((x0,y0),180),((x1,y0),270),((x1,y1),0),((x0,y1),90)):
  r=radii.get((x,y))
  if not r:pts.append((x,y));continue
  ax=x+(r if x==x0 else -r);ay=y+(r if y==y0 else -r)
  pts+=[(ax+r*math.cos(math.radians(start+90*i/segments)),ay+r*math.sin(math.radians(start+90*i/segments))) for i in range(segments+1)]
 cx=(x0+x1)/2;cy=(y0+y1)/2;theta=math.radians(board.get('rotation_degrees',0));c=math.cos(theta);s=math.sin(theta)
 return [(cx+c*(x-cx)-s*(y-cy),cy+s*(x-cx)+c*(y-cy)) for x,y in pts]
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
  if surface not in ('floor','wall','wood','ceiling'):raise DesignError('Flange must mount to floor, wall, wood or ceiling')
  if surface=='floor' and (abs(p[2])>.001 or dot(n,(0,0,1))<.999):raise DesignError('Floor mounting plane wrong')
  if surface=='wall' and (abs(p[0]-WALL_X)>.001 or dot(n,(-1,0,0))<.999):raise DesignError('Right-wall mounting plane wrong')
  if surface=='ceiling' and (abs(p[2]-ROOM['ceiling'])>.001 or dot(n,(0,0,-1))<.999):raise DesignError('Ceiling mounting plane wrong')
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
 def board(self,id,bounds,bottom,thickness,supports,holes=(),recess=None,rotation_degrees=0,corner_radii=()):
  # supports: (component ID, x, y, support plane z); points must be on wood.
  x0,x1,y0,y1=bounds
  if x1<=x0 or y1<=y0 or thickness<=0:raise DesignError('Invalid board dimensions')
  minimum=3 if supports and len({s[0] for s in supports})==1 and self.parts.get(supports[0][0]) and self.parts[supports[0][0]].kind=='flange' else 4
  if len(supports)<minimum:raise DesignError('Each board requires four support points, or one three-hole flange')
  for sid,x,y,z in supports:
   if sid not in self.parts or self.parts[sid].kind not in ('end_holder','middle_holder','hook','flange','saddle','bracket'):raise DesignError('Wood needs catalog shelf hardware')
   if not point_in_board(x,y,{'bounds':bounds,'rotation_degrees':rotation_degrees,'corner_radii':[list(c) for c in corner_radii]}) or abs(z-bottom)>.001:raise DesignError('Wood support outside board / wrong support plane')
  for other in self.boards.values():
   a=other['bounds'];b=other['bottom'];t=other['thickness']
   if min(x1,a[1])-max(x0,a[0])>.01 and min(y1,a[3])-max(y0,a[2])>.01 and min(bottom+thickness,b+t)-max(bottom,b)>.01:raise DesignError('Boards overlap')
  p=((x0+x1)/2,(y0+y1)/2,bottom+thickness/2);extra={'corner_radii':[list(c) for c in corner_radii]} if corner_radii else {}
  self.part(id,'wood',p,bounds=bounds,bottom=bottom,thickness=thickness,holes=list(holes),recess=recess,rotation_degrees=rotation_degrees,**extra)
  data=dict(bounds=bounds,bottom=bottom,thickness=thickness,supports=supports,holes=list(holes),recess=recess,rotation_degrees=rotation_degrees,**extra);self.boards[id]=data
  for s,*_ in supports:self.edges.append((s,id,'wood screw',None,None))
 def bracket(self,id,y,z,reach):
  """Separate shelf bracket on the right wall: a budget allowance, not a DOLLE fitting. Returns the board support point."""
  if reach<=0:raise DesignError('Bracket needs a positive reach')
  self.part(id,'bracket',(WALL_X,y,z),(0,0,1),(-1,0,0),reach=reach,interface_status='allowance; bracket type, size and wall fixings not selected');self.mounts[id]='wall'
  return (id,WALL_X-reach,y,z)
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
   if p.kind=='cross':
    for suffix,d in [('up',p.axis),('down',mul(p.axis,-1)),('out',p.direction),('in',mul(p.direction,-1))]:
     v=self.ports[p.id+'.'+suffix]
     if not close(v.p,add(p.origin,mul(d,self.v('cross_stop')))) or not close(v.n,d):errors.append(p.id+': cross port moved independently')
   if p.kind=='flange':
    v=self.ports[p.id+'.socket']
    if not close(v.p,add(p.origin,mul(p.axis,self.v('flange_stop')))):errors.append(p.id+': flange port moved independently')
    if self.mounts.get(p.id)=='wall' and abs(p.origin[0]-WALL_X)>.001:errors.append(p.id+': flange detached from wall')
    if self.mounts.get(p.id)=='floor' and abs(p.origin[2])>.001:errors.append(p.id+': flange detached from floor')
    if self.mounts.get(p.id)=='ceiling' and abs(p.origin[2]-ROOM['ceiling'])>.001:errors.append(p.id+': flange detached from ceiling')
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
  reached={k for k,v in self.mounts.items() if v in ('floor','wall','ceiling')};todo=list(reached)
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
  for p in self.parts.values():
   if self.mounts.get(p.id)=='ceiling':continue
   top=p.origin[2]+(p.data['length'] if p.kind.startswith('tube_') and p.axis[2]>.99 else 0)
   if top>ROOM['ceiling']-10:errors.append(p.id+': reaches the ceiling plane')
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
  if getattr(self,'portal',None):d['portal']=self.portal
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
def build(profile=None,close_gap=False,entry60=False,side_speakers=False,shared_desk=False,portal=False,offset=0,rack=None,desk_walls=(1200,2020),rear_upper=1200):
 if portal:return build_portal(profile)
 if shared_desk:return build_shared_desk(profile)
 if side_speakers:entry60=True
 if entry60:close_gap=True
 a=Assembly(profile);s=a.v('tee_stop');f=a.v('flange_stop');back=WALL_X-(40+s+f);front=back-(250+2*s);df=back-(602+2*s)
 shift=(250 if entry60 else 0)+offset
 y0=(1100 if close_gap else 980)+shift;y1=980+1500+2*s+shift;dy=[2640+shift]
 coat_length=602 if entry60 else 802
 bays=rack or (('short',1000,(950,1950)),('fold',602,()),('coat',coat_length,(1950,)))
 for _,L,_ in bays:dy.append(dy[-1]+L+2*s)
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
  a.column('DS0',front,y0-50);a.column('SB0',back,y0-50,upper=rear_upper)
 else:
  a.flange('DS0.base',(front,y0,740),(0,0,1),'wood');a.edges.append(('Desk.top','DS0.base','wood screw',None,None))
  a.from_port('DS0.riser',1500,'DS0.base.socket');a.cap('DS0.cover','DS0.riser.b');a.columns['DS0']={'x':front,'y':y0,'tubes':['DS0.riser']}
 for z in (desk_walls if side_speakers else (1100,2020)):a.walltie(f'Desk.wall0.{z}','SB0' if side_speakers else 'DB0',z)
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
 last=len(dy)-1
 for i in range(last+1):
  # The shoe shelf's own 185 mm cross-pipe already braces the post that starts a coat bay.
  for z in ((1800,) if i==last else (200,) if i<2 and bays[i][0]!='coat' else ()):a.bridge(f'Rack.depth{i}.{z}',f'RF{i}',f'RB{i}',z,250)
  a.walltie(f'Rack.wall{i}',f'RB{i}',1970 if i==0 else 1900 if i==last else 1700)
 for j,(_,L,rails) in enumerate(bays):
  for z in rails:a.bridge(f'Rack.clean{j}.{z}',f'RF{j}',f'RF{j+1}',z,L)
 for j,(role,_,_) in enumerate(bays):
  bounds=(front-30,back+30,dy[j]+gap,dy[j+1]-gap);pairs=[(f'RF{j}',f'RB{j}'),(f'RF{j+1}',f'RB{j+1}')]
  a.saddle_board('Rack.top'+str(j),pairs,bounds,2190,28)
  if role=='fold':
   for k,z in enumerate((700,1100,1500,1850)):a.saddle_board('Rack.fold'+str(k),pairs,bounds,z,28)
  if role=='coat':a.saddle_board('Rack.coat_shoes',pairs,bounds,200,28)
 # Wear-again rail: sliding tees on the two 200 mm return pipes.
 # The SAME tee stop sets both the bay width and rail width. No unverified
 # assumption that a cast elbow and a sliding tee have equal offsets.
 if any(role=='fold' for role,_,_ in bays):
  for j,col in enumerate(('RF1','RF2')):
   id='Wear.return'+str(j);a.clamp(id+'.tee',col,1250,(-1,0,0));a.from_port(id+'.tube',200,id+'.tee.branch');a.cap(id+'.cap',id+'.tube.b');nd=(0,1 if j==0 else -1,0);a.body_tee(id+'.outer',id+'.tube',140,nd)
  a.from_port('Wear.rail',602,'Wear.return0.outer.branch');a.connect('Wear.rail.b','Wear.return1.outer.branch')
 # Floating speaker shelves: two 250 mm side arms and four saddles per tray.
 if side_speakers:
  # Trays sit inside the shelf column between the middle and rear posts, flush with the shelf fronts, so nothing hangs over the desktop.
  # Both trays mirror about the desk centre line; the far posts stand 30 mm inside the desktop end, so they set the reach.
  desktop=a.boards['Desk.top']['bounds'];middle=(desktop[2]+desktop[3])/2;tray_x=(front-30,front-30+SPEAKER_TRAY)
  reach=min(a.columns['RF0']['y']-gap-middle,middle-a.columns['DS0']['y']-gap)
  for i,(cols,sign) in enumerate(((('DS0','SB0'),1),(('RF0','RB0'),-1))):
   outer=middle-sign*reach;ys=(outer,outer+SPEAKER_TRAY) if sign>0 else (outer-SPEAKER_TRAY,outer)
   supports=[];bottom=1100;z=bottom-a.v('saddle_rise');id='Speaker'+str(i);tray={'bounds':(*tray_x,*ys),'rotation_degrees':0}
   for j,col in enumerate(cols):
    stem=id+'.arm'+str(j);a.clamp(stem+'.tee',col,z,(0,sign,0));a.from_port(stem+'.tube',250,stem+'.tee.branch');a.cap(stem+'.cap',stem+'.tube.b')
    # Spread the two saddle tabs as far apart as the tray allows, 15 mm inside its edge.
    tube=a.parts[stem+'.tube'];tab=(1 if j==0 else -1,0,0)
    fits=[o for o in range(20,231,5) if point_in_board(*add(add(tube.origin,mul(tube.axis,o)),mul(tab,a.v('saddle_tab_offset')))[:2],tray,-15)]
    if len(fits)<2 or fits[-1]-fits[0]<40:raise DesignError(id+': speaker tray cannot reach two saddle stations on its arm')
    for k,offset in enumerate((fits[0],fits[-1])):
     sid=stem+'.saddle'+str(k);point=a.saddle(sid,stem+'.tube',offset,tab);supports.append((sid,*point))
   a.board(id+'.platform',tray['bounds'],bottom,25,supports)
   a.parts[id+'.platform'].data['speaker_target_mm']=[EAR_MM[0],middle,EAR_MM[1]]
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
  a.notes += ['V17 TV and all its custom support parts removed; the desktop TV bore is removed.', 'DS0 is now a floor-mounted 1000 + 1200 mm stock column with coupling, near support pair offset 50 mm from the desktop endframe to avoid crossing its pipes; eight 40 mm desktop holes include the two open-edge notches. Speaker shelves do not bear on the desktop.', f'Each speaker board is a {SPEAKER_TRAY} x {SPEAKER_TRAY} x 25 mm oak tray inside the shelf column, flush with the shelf fronts, on two uncut 250 mm cantilever arms, each clamped to its own upright by a sliding T. Four one-sided saddle tabs screw each tray to the arms. Nothing overhangs the desktop.', 'Near wall tie raised from 1100 to 1200 mm to clear speaker-arm tees. Tray underside 1100, top 1125 mm before angled isolation pads. The arm tees cannot drop lower while the 1000 + 1200 mm posts keep their coupling at 1015-1027 mm, so the downward tweeter aim comes from the pads. No desktop speaker risers or flanges.', 'Trays are square to the frame, between the middle and rear posts at each desk end. Each speaker turns on its tray to face the seated ear reference (x 2620, z 1220 mm), not the seat centre; angled pads tilt the tweeters down to that height. This wide stereo geometry is a visual arrangement, not a calibrated acoustic setup.', 'Cantilever capacity, clamp anti-rotation, saddle screw retention, speaker weight and fixing loads remain unverified. No positive manufacturer cantilever rating has been established.']
 return a
def build_shared_desk(profile=None,desk_shift=0,rack=None,desk_walls=(1200,2020),rear_upper=1000,near_upper=(1500,)):
 """Reuse four rack uprights; two elbow-return front legs, no separate rear legs.

 At desk height a DOLLE four-way cross on each middle post joins the 250 mm front arm, the
 250 mm rear bridge and the post sections above and below it. Low down, a cross at 235 mm on
 each rear post carries one straight 250 + 40 mm line from a sliding T on the middle post into
 a wall flange; the front leg is braced to the middle post by a 250 mm sliding-T bridge at
 400 mm. The front leg keeps a plain T: no stock stack puts a cross there without a spare
 socket, and a cross on the middle post would not meet the front leg's elbow height.
 A cross cannot slide onto a continuous upright: those posts are stacked from catalog
 lengths and every sleeve already on them is rehosted on the new tubes.
 """
 # The provisional 1000 + 1200 rear post from build() only hosts the sleeves until it is restacked below.
 a=build(profile,side_speakers=True,offset=desk_shift,rack=rack,desk_walls=desk_walls,rear_upper=1200);bounds=a.boards['Desk.top']['bounds']
 if abs(a.v('cross_stop')-a.v('tee_stop'))>.001 or abs(a.v('cross_stop')-a.v('elbow_stop'))>.001:
  raise DesignError('Measured cross, sliding-T and elbow stops do not close this stock desk module; redesign stock stack, do not stretch pipes')
 def remove(ids):
  ids=set(ids);removed_ports={id for id,p in a.ports.items() if p.owner in ids}
  # Release surviving sockets previously mated to a removed component.
  for p in a.ports.values():
   if p.used in removed_ports or p.used in ids:p.used=None
  a.parts={id:p for id,p in a.parts.items() if id not in ids};a.ports={id:p for id,p in a.ports.items() if p.owner not in ids}
  a.edges=[e for e in a.edges if e[0] not in ids and e[1] not in ids];a.mounts={id:surface for id,surface in a.mounts.items() if id not in ids}
  a.clamps=[c for c in a.clamps if c['id'] not in ids]
 # The far end's 200 mm wardrobe depth bar gives way to the low cross line at 235 mm.
 removed={id for id in a.parts if id.startswith(('DF0','DF1','DB0','DB1','Desk.endframe','Desk.top','Desk.tail','Desk.lower_wall','Rack.depth0.'))}
 remove(removed);a.clamps=[c for c in a.clamps if c['host'] not in removed]
 a.columns={id:c for id,c in a.columns.items() if not id.startswith(('DF','DB'))};del a.boards['Desk.top']
 # Derive every height from the stock stack and the editable fitting profile.
 f=a.v('flange_stop');gap=a.v('extension_gap');e=a.v('elbow_stop');c=a.v('cross_stop')
 low_z=f+200+c;axis_z=f+602+gap+40+c;bottom=axis_z+a.v('saddle_rise');supports=[]
 def coupling(id,port):
  p=a.ports[port];a.part(id,'extension',add(p.p,(0,0,gap/2)),gap=gap)
  a.port(id+'.down',id,'female',p.p,(0,0,-1));a.port(id+'.up',id,'female',add(p.p,(0,0,gap)),(0,0,1));a.connect(port,id+'.down');return id+'.up'
 def cross(id,port):
  # Threaded four-way joint seated on an upward tube end: up/down on the post, out toward the room, in toward the wall.
  centre=add(a.ports[port].p,(0,0,c));a.part(id,'cross',centre,(0,0,1),(-1,0,0))
  for suffix,d in (('up',(0,0,1)),('down',(0,0,-1)),('out',(-1,0,0)),('in',(1,0,0))):a.port(id+'.'+suffix,id,'female',add(centre,mul(d,c)),d)
  a.connect(port,id+'.down');return id
 for i,(front,back,direction) in enumerate((('DS0','SB0',1),('RF0','RB0',-1))):
  y=a.columns[front]['y'];low=f'Desk.low{i}';retained=[]
  for col in (front,back):
   old=set(a.columns[col]['tubes']);retained+=[q for q in a.clamps if q['host'] in old];remove(list(old)+[col+'.extension',col+'.cover'])
  # Middle post: 602 + coupling + 40, desk cross, then 40 + coupling + the upper sections.
  a.from_port(front+'.lower',602,front+'.foot.socket');a.from_port(front+'.joint_riser',40,coupling(front+'.extension',front+'.lower.b'));joint=cross(f'Desk.cross{i}',front+'.joint_riser.b')
  a.from_port(front+'.top_stub',40,joint+'.up');a.from_port(front+'.upper',near_upper[0] if i==0 else 1500,coupling(front+'.top_extension',front+'.top_stub.b'));tubes=[front+'.lower',front+'.joint_riser',front+'.top_stub',front+'.upper']
  for k,L in enumerate(near_upper[1:] if i==0 else ()):
   last=f'{front}.upper{k+2}';a.from_port(last,L,coupling(f'{front}.top_extension{k+2}',tubes[-1]+'.b'));tubes.append(last)
  a.cap(front+'.cover',tubes[-1]+'.b');a.columns[front]['tubes']=tubes
  # Rear post: 200, low cross, 1000 + coupling + the upper section.
  a.from_port(back+'.lower',200,back+'.foot.socket');cross(low+'.cross_rear',back+'.lower.b')
  a.from_port(back+'.mid',1000,low+'.cross_rear.up');a.from_port(back+'.upper',rear_upper if i==0 else 1000,coupling(back+'.extension',back+'.mid.b'));a.cap(back+'.cover',back+'.upper.b');a.columns[back]['tubes']=[back+'.lower',back+'.mid',back+'.upper']
  for q in retained:
   host,_=a.host_at(q['host'].split('.')[0],a.parts[q['id']].origin[2],q['half']);q['host']=host;a.parts[q['id']].data['host']=host;a.edges.append((host,q['id'],'clamp',None,None))
  # Desk level: the front arm runs out of the cross to the front leg's elbow; the rear bridge seats in a sliding T on the rear post.
  arm=f'Desk.shared{i}.0';a.from_port(arm+'.tube',250,joint+'.out')
  bridge=f'Desk.shared{i}.1';a.clamp(bridge+'.tee',back,axis_z,(-1,0,0));a.from_port(bridge+'.tube',250,bridge+'.tee.branch');a.connect(bridge+'.tube.b',joint+'.in')
  for stem in (arm,bridge):
   for k,offset in enumerate((45,205)):
    sid=stem+'.saddle'+str(k);point=a.saddle(sid,stem+'.tube',offset,(0,direction,0));supports.append((sid,*point))
  # Front leg: 602 + coupling + 40 to a stock elbow under the arm; a plain continuous leg with no spare socket.
  leg='DF'+str(i);x=a.ports[arm+'.tube.b'].p[0]-e
  a.flange(leg+'.foot',(x,y,0),(0,0,1),'floor');a.from_port(leg+'.lower',602,leg+'.foot.socket');a.from_port(leg+'.upper',40,coupling(leg+'.extension',leg+'.lower.b'))
  elbow=leg+'.elbow';a.part(elbow,'elbow',(x,y,axis_z),(0,0,-1),(1,0,0))
  a.port(elbow+'.down',elbow,'female',(x,y,axis_z-e),(0,0,-1));a.port(elbow+'.in',elbow,'female',(x+e,y,axis_z),(1,0,0));a.connect(leg+'.upper.b',elbow+'.down');a.connect(arm+'.tube.b',elbow+'.in')
  a.columns[leg]={'x':x,'y':y,'tubes':[leg+'.lower',leg+'.upper']}
  # Low line: rear cross to a sliding T on the middle post, and on into the wall. The front leg is braced higher, at 400 mm,
  # because a second sleeve cannot share the middle post's 235 mm station.
  a.clamp(low+'.tee',front,low_z,(1,0,0));a.from_port(low+'.rear',250,low+'.cross_rear.out');a.connect(low+'.rear.b',low+'.tee.branch')
  a.from_port(low+'.wall',40,low+'.cross_rear.in');wall=add(a.ports[low+'.wall.b'].p,(f,0,0));a.flange(low+'.wall_flange',wall,(-1,0,0),'wall');a.connect(low+'.wall.b',low+'.wall_flange.socket')
  a.bridge(low+'.front',leg,front,400,250)
 holes=[(a.columns[k]['x'],a.columns[k]['y'],44) for k in ('DS0','SB0','RF0','RB0')]
 # Round the entrance corner: the kitchen-corner pinch is the main circulation path.
 # R100 keeps the nearest saddle screw (x 2860) on full-width timber.
 a.board('Desk.top',bounds,bottom,28,supports,holes,corner_radii=[(bounds[0],bounds[2],ENTRY_CORNER_RADIUS)])
 # Preview underside reliefs for the cross, tee and elbow castings; the top face is continuous.
 reliefs=[]
 for k,(lo,hi) in (('DS0',(-31,31)),('SB0',(-31,0)),('RF0',(-31,31)),('RB0',(-31,0)),('DF0',(-18,31)),('DF1',(-18,31))):
  x=a.columns[k]['x'];yy=a.columns[k]['y'];reliefs.append({'bounds':[x+lo,x+hi,yy-18,yy+18,bottom-1,axis_z+17.5]})
 a.parts['Desk.top'].data['support_reliefs']=reliefs;a.boards['Desk.top']['support_reliefs']=reliefs
 mid_top=a.parts[a.columns['RF0']['tubes'][-1]];rear_top=a.parts[a.columns['RB0']['tubes'][-1]]
 a.notes=[n for n in a.notes if not n.startswith(('Desk far rear post','RF0/RB0 pass','Desktop remains 1615','DS0 is now'))]
 a.notes += ['V18 desk module: all four former short desktop columns and both 602 mm endframe cross-pipes removed. The existing DS0/SB0 and RF0/RB0 rack posts carry the desktop: a DOLLE four-way cross at desk height on each middle post joins its 250 mm front arm, its 250 mm rear bridge and the post sections above and below. The rear bridge seats in a sliding T on the rear post.',
  'Each front arm returns down through a stock elbow to a 602 + coupling + 40 mm front leg. Eight saddle holders support the desktop; no separate rear desk legs.',
  f'Derived desktop underside {bottom:g} mm / top {bottom+28:g} mm. Front legs finish under the tabletop through elbows: no front-leg bores. Four 44 mm preview clearance bores remain only for the continuing rack posts, including near-edge notches.',
  f'Low line at {low_z:g} mm: a four-way cross on each rear post takes a 250 mm pipe from a sliding T on the middle post and a 40 mm pipe into a wall flange, replacing the old 300 mm rear brace, the 400 mm low wall tie and the far end\'s 200 mm wardrobe depth bar. The front leg keeps a plain sliding T: its 250 mm brace to the middle post sits at 400 mm, because two sleeves cannot share one station and no stock stack puts a cross on the leg without a spare socket.',
  f'Cross-bearing posts: middle posts 602 + coupling + 40, cross, 40 + coupling + 1500 mm (capped top {mid_top.origin[2]+mid_top.data["length"]:g} mm); rear posts 200, cross, 1000 + coupling + 1000 mm (capped top {rear_top.origin[2]+rear_top.data["length"]:g} mm). Boards, equipment and the upper shelf sleeves keep their positions.',
  'The desktop still measures 1615 x 702 x 28 mm in the same plan position. Main entry corner gap remains 640.9 mm. Closest modeled front foot clearance exceeds 600 mm.',
  'The cross is a threaded fitting, not a slide-on clamp. Preassemble free modules and stage all sleeves before feeding posts; verify the physical closure sequence and measured socket stops before purchasing or cutting timber.',
  'Model connection and clearance checks are not a load certification. Verify desk saddle screws, clamp slip/rotation, wall anchorage and leaning loads before construction. Fully floating desk is not assumed approved.']
 return add_equipment_shelf(a,desk_shift)
def add_equipment_shelf(a,desk_shift=0):
 """Rear service shelf on four separate wall brackets behind a 472 mm deep central knee zone; no pipes under the desk."""
 y0,y1=1305+desk_shift,2920+desk_shift;bottom=500
 supports=[a.bracket(f'Desk.service_bracket{j}',y,bottom,SERVICE_BRACKET_REACH) for j,y in enumerate((y0+120,y0+580,y1-580,y1-120))]
 holes=[(a.columns[k]['x'],a.columns[k]['y'],44) for k in ('SB0','RB0')]
 a.board('Desk.service_shelf',(3175,3405,y0,y1),bottom,18,supports,holes)
 clear=a.boards['Desk.top']['bottom']-bottom-18
 a.notes += [f'Rear equipment shelf: 1615 x 230 x 18 mm, underside 500 / top 518 mm, {clear:g} mm clear below the desktop. It begins 472 mm behind the desktop front; the middle knee zone remains open. It hangs on four separate shelf brackets fixed to the wall, {SERVICE_BRACKET_REACH} mm reach, not on the pipe frame: bracket type, size and wall fixings are an allowance still to be chosen.',
  'M1 Mac mini 197 x 197 x 36 mm sits on the rear shelf with ports facing along its length for cable access. Router and power-brick sizes remain space allowances, not measured products. Keep the shelf open and separate the bricks; do not stack or strap across vents.',
  'Focusrite and OWC dock use separate adjustable open-bottom/side U holders under the front ends. Their exposed front panels and cable reserves remain outside the 700 mm central seated knee width; bracket screw lengths and exact Focusrite generation remain to verify.']
 return a
def portal_layout(path=Path(__file__).parent/'portal-layout.json'):
 return json.loads(Path(path).read_text())
def portal_geometry(a,layout=None):
 """Every divider coordinate, derived from the room file, the fitting profile and portal-layout.json."""
 d=layout or portal_layout();fr=d['frame'];c=d['crate'];o=d['opening'];s=a.v('tee_stop');f=a.v('flange_stop');t=fr['board_thickness'];cl,cd,ch=c['size']
 back=WALL_X-(40+s+f);xr=back-(250+2*s);span=sum(fr['span_tubes'])+a.v('extension_gap')+2*s;xl=xr-span;xs=(xl-250-2*s,xl,xr,back)
 # Back of the boards lines up with the back of the bar; bar-side posts stay clear of its end.
 yb=d['fixed']['bar_back_y']-30;yf=yb-(250+2*s);ymid=(yf+yb)/2;cx=(xl+xr)/2
 # Crates stack down from the measured ceiling: top row, upper board, lower row, lintel.
 top=ROOM['ceiling']-c['ceiling_gap'];upper=top-ch-t;lintel=upper-c['row_gap']-ch-t
 head=lintel-a.v('saddle_rise')-12.5-3-o['head_margin'];b=head-o['centre_z']
 def half_width(z):return 0 if abs(z-o['centre_z'])>=b else o['half_width']*math.sqrt(1-((z-o['centre_z'])/b)**2)
 def edge(z0,z1):
  # Stay outside the opening over the full board thickness, and keep a timber web past the post bore.
  near=min(max(z0,o['centre_z']),z1) if z0<=o['centre_z']<=z1 else (z1 if z1<o['centre_z'] else z0);return max(half_width(near),0)
 return {'xs':xs,'rows':(yf,yb),'ymid':ymid,'cx':cx,'lintel':lintel,'upper':upper,'crate_top':top,'head':head,'b':b,'half_width':half_width,'edge':edge,'tie_z':ROOM['ceiling']-f-fr['ceiling_tie']-s,'board_y':(yf-fr['board_overhang'],yb+fr['board_overhang'])}
def portal_crates(a,layout=None):
 """Six KNAGGLIG positions on the two lintel boards: (centre x, centre y, underside z), long side across."""
 d=layout or portal_layout();g=portal_geometry(a,d);c=d['crate'];cl=c['size'][0];pitch=cl+c['side_gap'];t=d['frame']['board_thickness'];out=[]
 for z in (g['lintel']+t,g['upper']+t):
  for i in range(c['per_row']):out.append((g['cx']+(i-(c['per_row']-1)/2)*pitch,g['ymid'],z))
 return out
def add_portal(a,layout=None):
 """Floor-to-ceiling divider from the bar end to the right wall; stepped board ends hint a round door."""
 d=layout or portal_layout();g=portal_geometry(a,d);fr=d['frame'];o=d['opening'];s=a.v('tee_stop');rise=a.v('saddle_rise');t=fr['board_thickness'];bore=fr['post_bore'];xs=g['xs'];yf,yb=g['rows'];ymid=g['ymid'];by=g['board_y'];rows=(('F',yf),('B',yb))
 # The desk's near posts stand in as the rear right pair, so no upright is doubled.
 shared=d['shared_posts'];rear=shared['rear_columns']
 def col(r,i):return rear[str(i)] if r=='B' and str(i) in rear else f'P{r}{i}'
 for i,x in enumerate(xs):
  for r,y in rows:
   if col(r,i).startswith('P'):a.column(col(r,i),x,y,upper=fr['upper_post'],lower=fr['lower_post'])
 def holes(indices):return [(xs[i],y,bore) for i in indices for _,y in rows]
 def relief(x,y,direction,bottom):
  # Preview underside pocket for the T casting that sits just proud of the board underside.
  dx,dy=direction;x0,x1=(min(x,x+dx*31),max(x,x+dx*31)) if dx else (x-18,x+18);y0,y1=(min(y,y+dy*31),max(y,y+dy*31)) if dy else (y-18,y+18)
  return {'bounds':[x0,x1,y0,y1,bottom-1,bottom-rise+17.5]}
 def bar(i,z):return a.shelf_crossbar(col('F',i),col('B',i),z)
 def tabs(stem,tube,toward,supports,stations=(45,205)):
  for j,offset in enumerate(stations):
   sid=f'{stem}.saddle{j}';supports.append((sid,*a.saddle(sid,tube,offset,toward)))
 def arm(stem,col,y,z,sign,cantilever,supports):
  # Stock arm from a post sleeve, as on the speaker trays; the tip stays clear of the opening.
  L=max((n for n in (200,250) if s+n+4<=cantilever-o['arm_tip_clearance']),default=None)
  if L is None:raise DesignError(stem+': no stock arm fits inside the board end')
  a.clamp(stem+'.tee',col,z,(sign,0,0));a.from_port(stem+'.tube',L,stem+'.tee.branch');a.cap(stem+'.cap',stem+'.tube.b')
  tabs(stem,stem+'.tube',(0,1 if y<ymid else -1,0),supports,(45,L-45));return relief(xs[1] if sign>0 else xs[2],y,(sign,0),z+rise)
 def finish(id,reliefs):
  a.parts[id].data['support_reliefs']=reliefs;a.boards[id]['support_reliefs']=reliefs
 def shelf(id,level,left):
  outer,inner,sign=(0,1,1) if left else (3,2,-1);width=g['edge'](level,level+t);end=g['cx']-sign*width
  end=(max(end,xs[1]+o['post_web']) if left else min(end,xs[2]-o['post_web']))
  z=level-rise;supports=[];reliefs=[relief(xs[outer],y,(0,1 if y<ymid else -1),level) for _,y in rows];cantilever=abs(end-xs[inner])
  pipe=None if left else shared['shared_pipes'].get(str(round(z)))
  if pipe:
   # A desk brace already crosses this tower here: reuse it and add only the front pipe.
   stem=f'Portal.front{round(z)}';a.bridge(stem,col('F',2),col('F',3),z,250);reliefs=[relief(xs[2],yf,(1,0),level),relief(xs[3],yf,(-1,0),level),relief(xs[2],yb,(1,0),level),relief(xs[3],yb,(-1,0),level)]
   tabs(id+'.front',stem+'.tube',(0,1,0),supports);tabs(id+'.rear',pipe,(0,-1,0),supports)
  elif tabs(id+'.outer',bar(outer,z),(sign,0,0),supports) or cantilever>o['arm_above_cantilever']:
   for r,y in rows:reliefs.append(arm(f'{id}.arm{r}',col(r,inner),y,z,sign,cantilever,supports))
  else:
   tabs(id+'.inner',bar(inner,z),(-sign,0,0),supports);reliefs+=[relief(xs[inner],y,(0,1 if y<ymid else -1),level) for _,y in rows]
  bounds=(xs[0]-30,end,*by) if left else (end,xs[3]+30,*by)
  a.board(id,bounds,level,t,supports,holes((outer,inner)));finish(id,reliefs)
 for k,level in enumerate(d['levels']):
  shelf(f'Portal.shelfL{k}',level,True);shelf(f'Portal.shelfR{k}',level,False)
 # Short floating caps above the last full level close the crown of the circle.
 gap=a.v('tee_outer_radius')+1
 for k,level in enumerate(d['cap_steps']):
  for left,side in ((True,'L'),(False,'R')):
   sign=1 if left else -1;inner=1 if left else 2;id=f'Portal.cap{side}{k}';z=level-rise;width=g['edge'](level,level+t);end=g['cx']-sign*width;supports=[];reliefs=[]
   for r,y in rows:arm(f'{id}.arm{r}',col(r,inner),y,z,sign,abs(end-xs[inner]),supports)
   bounds=(xs[1]+gap,end,*by) if left else (end,xs[2]-gap,*by);a.board(id,bounds,level,t,supports)
 # Lintel: lower board rests on the end bars and a central rail, upper board on the end bars only.
 for id,level,railed in (('Portal.lintel0',g['lintel'],True),('Portal.lintel1',g['upper'],False)):
  z=level-rise;supports=[];reliefs=[]
  for i,sign in ((0,1),(1,1),(2,-1),(3,-1)):
   tube=bar(i,z);tabs(f'{id}.bar{i}',tube,(sign,0,0),supports);reliefs+=[relief(xs[i],y,(0,1 if y<ymid else -1),level) for _,y in rows]
  if railed:
   left=bar(1,z);right=bar(2,z);a.body_tee('Portal.rail.t1',left,125,(1,0,0));a.body_tee('Portal.rail.t2',right,125,(-1,0,0))
   L1,L2=fr['span_tubes'];a.from_port('Portal.rail.a',L1,'Portal.rail.t1.branch');end=a.ports['Portal.rail.a.b'].p;gap_=a.v('extension_gap');ex='Portal.rail.extension'
   a.part(ex,'extension',add(end,(gap_/2,0,0)),(1,0,0),gap=gap_);a.port(ex+'.down',ex,'female',end,(-1,0,0));a.port(ex+'.up',ex,'female',add(end,(gap_,0,0)),(1,0,0));a.connect('Portal.rail.a.b',ex+'.down')
   a.from_port('Portal.rail.b',L2,ex+'.up');a.connect('Portal.rail.b.b','Portal.rail.t2.branch')
   for j,(offset,toward) in enumerate(((360,1),(840,-1))):
    sid=f'{id}.rail_saddle{j}';supports.append((sid,*a.saddle(sid,'Portal.rail.a',offset,(0,toward,0))))
   reliefs+=[{'bounds':[xs[1]-18,xs[1]+31,ymid-36,ymid+36,level-1,z+17.5]},{'bounds':[xs[2]-31,xs[2]+18,ymid-36,ymid+36,level-1,z+17.5]}]
  a.board(id,(xs[0]-30,xs[3]+30,*by),level,t,supports,holes((0,1,2,3)));finish(id,reliefs)
 # Ceiling ties: a sliding T on each tower bar takes up the height, so the posts stay uncut stock.
 z=g['tie_z']
 for i in range(4):
  id=f'Portal.tie{i}';tube=bar(i,z);a.body_tee(id+'.tee',tube,125,(0,0,1));a.from_port(id+'.tube',fr['ceiling_tie'],id+'.tee.branch')
  a.flange(id+'.ceiling',(xs[i],ymid,ROOM['ceiling']),(0,0,-1),'ceiling');a.connect(id+'.tube.b',id+'.ceiling.socket')
 # The rear post keeps the desk's own wall ties, moved to the same heights in build_portal.
 for z in fr['wall_tie_heights']:a.walltie(f'Portal.wallF.{z}','PF3',z)
 return a
def build_portal(profile=None):
 """Portal variant: divider across the room, then the V18 desk module, then a shorter wardrobe."""
 d=portal_layout();probe=Assembly(profile);rows=portal_geometry(probe,d)['rows']
 # DS0 sits at y 1300 in V18; the rigid desk module moves until its near posts are the rear divider row.
 offset=rows[1]-1300;rack=tuple((b['role'],b['tube'],tuple(b['rails'])) for b in d['wardrobe']);sh=d['shared_posts']
 a=add_portal(build_shared_desk(profile,offset,rack,tuple(d['frame']['wall_tie_heights']),sh['rear_upper_tube'],tuple(sh['near_upper_tubes'])),d)
 g=portal_geometry(a,d);a.portal={'desk_offset':offset,'xs':list(g['xs']),'rows':list(g['rows']),'cx':g['cx'],'ymid':g['ymid'],'head':g['head'],'lintel':g['lintel'],'upper':g['upper'],'crate_top':g['crate_top'],'half_width':d['opening']['half_width'],'centre_z':d['opening']['centre_z'],'semi_height':g['b'],'tie_z':g['tie_z'],'crates':portal_crates(a,d)}
 a.notes=[n for n in a.notes if not n.startswith(('V11','Four coat','Fold shelf','V16','Wear-again','Desk and first'))]
 a.notes+=['Portal variant: a floor-to-ceiling divider runs from the bar end to the right wall. Six new posts stand on the floor and the two near desk posts complete the frame, so no upright is doubled. Four ceiling ties and four wall ties hold it.',f'Board ends step along an ellipse {2*d["opening"]["half_width"]} mm wide and {g["head"]:.0f} mm high above the floor, so the round door is hinted by the cut of the shelves. Nothing is curved.','Six KNAGGLIG crates sit 3 x 2 on the two lintel boards, long side across the room. Lintel heights are derived from the measured ceiling.','The desk module moves as one rigid block to stand behind the divider. The wardrobe becomes one 602 mm short bay and one 602 mm coat bay; folded clothes move onto the divider shelves and the wear-again rail is dropped.','Ceiling ties take up height through a sliding T, so a re-measured ceiling moves the tie and lintel without changing any stock pipe length.','Ceiling construction, anchors, cantilever arms and the 1,416 mm crate-loaded span are not load-certified; verify before building.']
 return a
if __name__=='__main__':
 out=Path(__file__).parent;a=build(profile_from_measurements(out/'Measurements-v8.json'));a.save(out/'Assembly-v8.json');(out/'Validation-v8.json').write_text(json.dumps(a.validate(),indent=2));print(json.dumps(a.validate(),indent=2));print(dict(a.bom()))
