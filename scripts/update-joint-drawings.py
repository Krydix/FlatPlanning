"""Refresh graph layers of the retained metre-unit DXF plans (requires ezdxf)."""
import sys,math,json
from pathlib import Path
import ezdxf
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT/'source'))
from pipe_engine import Assembly,add,mul,board_corners,board_outline
A=Assembly.load(ROOT/'source/assembly.json')
def draw(m,p,project,plan=False):
 kind=p.kind;o=p.origin;layer='V8_CLAMPS'
 def line(a,b,layer=layer):m.add_line(project(a),project(b),dxfattribs={'layer':layer})
 if kind.startswith('tube_'):
  end=add(o,mul(p.axis,p.data['length']))
  if math.dist(project(o),project(end))<1e-8:m.add_circle(project(o),.0125,dxfattribs={'layer':'V8_PIPE'})
  else:line(o,end,'V8_PIPE')
 elif kind=='wood':
  c=board_outline(p.data);n=len(c);bt=p.data['bottom'];th=p.data['thickness'];pts=[project((x,y,z)) for z in (bt,bt+th) for x,y in c]
  for i in range(n):
   # Arc points get outline edges only; vertical edges are drawn at true corners and arc ends.
   straight=max(math.dist(c[i],c[(i+1)%n]),math.dist(c[i],c[i-1]))>50
   for a,b in [(i,(i+1)%n),(i+n,(i+1)%n+n)]+([(i,i+n)] if straight else []):m.add_line(pts[a],pts[b],dxfattribs={'layer':'V8_OVERHEAD' if plan and p.id!='Desk.top' else 'V8_TIMBER'})
  if plan:
   for x,y,diam in p.data['holes']:m.add_circle(project((x,y,bt)),diam/2000,dxfattribs={'layer':'V8_CLAMPS'})
 elif kind in ('slide_tee','cross','elbow'):
  for d in (p.axis,p.direction):
   negative=-30 if kind in ('slide_tee','cross') and (d==p.axis or kind=='cross') else 0
   line(add(o,mul(d,negative)),add(o,mul(d,30)))
 elif kind=='flange':m.add_circle(project(o),.035,dxfattribs={'layer':layer})
 elif kind=='saddle':line(o,add(add(o,mul(p.direction,A.v('saddle_tab_offset'))),(0,0,A.v('saddle_rise'))))
 elif kind in ('extension','cap'):m.add_circle(project(o),.017,dxfattribs={'layer':layer})
for name in ['flat-v18.dxf','frame-elevations-v18.dxf']:
 path=ROOT/'public/downloads'/name;d=ezdxf.readfile(path);m=d.modelspace()
 fixed=[e.dxfattribs() for e in m if e.dxf.layer in ('F_Fixed_Kitchen','F_Fixed_Bar')]
 for e in list(m):
  if e.dxf.layer in ('V8_PIPE','V8_TIMBER','V8_OVERHEAD','V8_CLAMPS','V18_EQUIPMENT_SERVICE'):m.delete_entity(e)
 if name=='flat-v18.dxf':views=[(lambda p:(.472818559556786+p[0]/1000,1.606022766620499+p[1]/1000),list(A.parts))]
 else:
  views=[(lambda p:((p[1]-950)/1000,p[2]/1000),list(A.parts)),(lambda p:(4.75+(3450-p[0])/1000,p[2]/1000),[id for id in A.parts if id.startswith(('DF0','DS0','SB0','Speaker0','Desk.shared0','Desk.cross0','Desk.low_front0','Desk.low_depth0','Desk.low_wall0','Desk.service0','Desk.service_shelf','Desk.shelf','Desk.top'))]),(lambda p:(6.05+(3450-p[0])/1000,p[2]/1000),[id for id in A.parts if id.startswith(('RF2','RB2','Rack.fold','Rack.coat_shoes','Rack.top2','Rack.depth2','Wear'))])]
 for project,ids in views:
  for id in ids:draw(m,A.parts[id],project,name=='flat-v18.dxf')
 if 'V18_EQUIPMENT_SERVICE' not in d.layers:d.layers.new('V18_EQUIPMENT_SERVICE',dxfattribs={'color':5})
 cfg=json.loads((ROOT/'source/equipment-layout.json').read_text())
 for project,_ in views[:2]:
  for eq in cfg['devices']:
   centre=eq['location'];size=eq['size'];corners=[project(tuple(centre[k]+sign[k]*size[k]/2 for k in range(3))) for sign in [(-1,-1,-1),(-1,1,-1),(1,1,-1),(1,-1,-1),(-1,-1,1),(-1,1,1),(1,1,1),(1,-1,1)]]
   x0=min(p[0] for p in corners);x1=max(p[0] for p in corners);y0=min(p[1] for p in corners);y1=max(p[1] for p in corners)
   m.add_lwpolyline([(x0,y0),(x1,y0),(x1,y1),(x0,y1)],close=True,dxfattribs={'layer':'V18_EQUIPMENT_SERVICE'})
 for e in m.query('TEXT'):
  if '200 REAR ARMS' in e.dxf.text:e.dxf.text='DESK: TWO FOUR-WAY CROSSES / 250 FRONT + 250 REAR / LOW FRONT T BRACES 400 / REAR 300 MM'
 if name=='frame-elevations-v18.dxf':
  for e in list(m.query('TEXT')):
   if e.dxf.text.startswith('SERVICE SHELF:'):m.delete_entity(e)
  m.add_text('SERVICE SHELF: 230 DEPTH / 518 TOP / 186 CLEAR ABOVE / CENTRAL KNEE DEPTH 472 MM',dxfattribs={'insert':(0,-1.68),'height':.043,'layer':'V8_NOTES'})
 assert fixed==[e.dxfattribs() for e in m if e.dxf.layer in ('F_Fixed_Kitchen','F_Fixed_Bar')]
 assert not d.audit().errors;assert d.units==6;d.saveas(path)
 print('DXF_UPDATED',name)
