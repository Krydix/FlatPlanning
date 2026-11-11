import unittest,math,copy,json,tempfile
from pathlib import Path
from unittest import mock
import pipe_engine
from pipe_engine import build,PROFILE,STOCK,DesignError,WALL_X,ROOM,portal_layout,portal_geometry,profile_from_measurements,point_in_board
HERE=Path(__file__).parent
class Portal(unittest.TestCase):
 def setUp(self):self.a=build(portal=True);self.d=portal_layout();self.g=portal_geometry(self.a,self.d);self.p=self.a.portal
 def test_graph_is_valid_uncut_stock(self):
  self.assertEqual(self.a.validate()['geometry_errors'],[])
  for p in self.a.parts.values():
   if p.kind.startswith('tube_'):self.assertEqual(p.data['length'],int(p.kind[5:]));self.assertIn(p.data['length'],STOCK)
 def test_v18_is_untouched(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'a.json';build(profile_from_measurements(HERE/'Measurements-v8.json'),shared_desk=True).save(path)
   self.assertEqual(path.read_text(),(HERE/'assembly.json').read_text())
 def test_posts_stand_on_the_floor_and_ties_reach_the_ceiling(self):
  for c in ('PF0','PB0','PF1','PB1','PF2','PF3','DS0','SB0'):self.assertEqual(self.a.mounts[c+'.foot'],'floor')
  for i in range(4):
   tie=self.a.parts[f'Portal.tie{i}.ceiling'];self.assertEqual(self.a.mounts[tie.id],'ceiling');self.assertEqual(tie.origin[2],ROOM['ceiling'])
   self.assertTrue(self.a.ports[f'Portal.tie{i}.tube.b'].used)
 def test_divider_spans_bar_end_to_wall_with_clearance(self):
  b=self.a.boards['Portal.lintel0']['bounds'];self.assertGreaterEqual(b[0]-self.d['fixed']['bar_end_x'],10);self.assertGreaterEqual(self.p['xs'][0]-35-self.d['fixed']['bar_end_x'],10)
  self.assertLess(b[1],WALL_X);self.assertEqual(self.p['xs'][3],WALL_X-75)
 def test_boards_stay_clear_of_the_bed(self):
  for k,b in self.a.boards.items():
   if k.startswith('Portal.'):self.assertLess(b['bounds'][3],self.d['fixed']['bed_near_y']-200)
 def test_six_crates_fit_between_the_inner_posts(self):
  c=self.d['crate']['size'];xs=self.p['xs'];crates=self.p['crates'];self.assertEqual(len(crates),6)
  self.assertGreaterEqual(min(x-c[0]/2 for x,_,_ in crates)-xs[1],12.5+5);self.assertGreaterEqual(xs[2]-max(x+c[0]/2 for x,_,_ in crates),12.5+5)
  b=self.a.boards['Portal.lintel0']['bounds'];self.assertGreaterEqual(self.p['ymid']-c[1]/2-b[2],20);self.assertGreaterEqual(b[3]-self.p['ymid']-c[1]/2,20)
  pairs=sorted({x for x,_,_ in crates});self.assertTrue(all(q-p>=c[0] for p,q in zip(pairs,pairs[1:])))
 def test_crates_clear_every_board_and_the_ceiling(self):
  c=self.d['crate']['size']
  for x,y,z in self.p['crates']:
   self.assertLessEqual(z+c[2],ROOM['ceiling']-30)
   for k,b in self.a.boards.items():
    x0,x1,y0,y1=b['bounds']
    if x0<x+c[0]/2 and x1>x-c[0]/2 and y0<y+c[1]/2 and y1>y-c[1]/2:self.assertTrue(b['bottom']+b['thickness']<=z or b['bottom']>=z+c[2],k)
 def test_no_pipe_crosses_a_crate(self):
  c=self.d['crate']['size']
  for x,y,z in self.p['crates']:
   lo=(x-c[0]/2,y-c[1]/2,z);hi=(x+c[0]/2,y+c[1]/2,z+c[2])
   for p in self.a.parts.values():
    if not p.kind.startswith('tube_'):continue
    end=pipe_engine.add(p.origin,pipe_engine.mul(p.axis,p.data['length']));box=[(min(p.origin[i],end[i])-(0 if abs(p.axis[i])>.99 else 12.5),max(p.origin[i],end[i])+(0 if abs(p.axis[i])>.99 else 12.5)) for i in range(3)]
    self.assertFalse(all(box[i][0]<hi[i] and box[i][1]>lo[i] for i in range(3)),p.id)
 def test_opening_is_clear_and_walkable(self):
  g=self.g;hw=self.d['opening']['half_width'];cz=self.d['opening']['centre_z'];self.assertGreaterEqual(self.p['head'],1950)
  self.assertGreaterEqual(2*g['half_width'](0),800);self.assertGreaterEqual(2*g['half_width'](1500),700)
  self.assertLess(hw,(self.p['xs'][2]-self.p['xs'][1])/2-17)
  for k,b in self.a.boards.items():
   if not k.startswith('Portal.') or k.startswith('Portal.lintel'):continue
   x0,x1,_,_=b['bounds'];z0,z1=b['bottom'],b['bottom']+b['thickness'];near=x1 if x1<self.p['cx'] else x0
   for z in (z0,z1):self.assertGreaterEqual(abs(near-self.p['cx']),g['half_width'](z)-.01,k)
 def test_shelf_ends_step_like_a_circle(self):
  ends=[self.a.boards[f'Portal.shelfL{k}']['bounds'][1] for k in range(len(self.d['levels']))]+[self.a.boards['Portal.capL0']['bounds'][1]]
  self.assertLess(min(ends[1:4]),ends[0]);self.assertLess(min(ends[1:4]),ends[-1]);self.assertEqual(ends[-1],max(ends))
  for k in range(len(self.d['levels'])):
   l=self.a.boards[f'Portal.shelfL{k}']['bounds'];r=self.a.boards[f'Portal.shelfR{k}']['bounds'];self.assertAlmostEqual(l[1]-self.p['cx'],self.p['cx']-r[0])
 def test_bores_keep_a_timber_web(self):
  for k,b in self.a.boards.items():
   if not k.startswith('Portal.'):continue
   for x,y,dia in b['holes']:
    self.assertGreaterEqual(min(x-b['bounds'][0],b['bounds'][1]-x,y-b['bounds'][2],b['bounds'][3]-y)-dia/2,8,k)
 def test_every_arm_ends_inside_its_board(self):
  for p in self.a.parts.values():
   if p.id.startswith('Portal.') and '.arm' in p.id and p.kind.startswith('tube_'):
    board=self.a.boards[p.id.split('.arm')[0]];tip=pipe_engine.add(p.origin,pipe_engine.mul(p.axis,p.data['length']+4));self.assertTrue(point_in_board(tip[0],tip[1],board),p.id)
 def test_lintel_follows_the_ceiling(self):
  room=dict(ROOM);room['ceiling']=ROOM['ceiling']-20
  with mock.patch.object(pipe_engine,'ROOM',room):
   a=build(portal=True);self.assertEqual(a.validate()['geometry_errors'],[]);self.assertEqual(a.portal['crate_top'],room['ceiling']-self.d['crate']['ceiling_gap']);self.assertEqual(a.portal['lintel'],self.p['lintel']-20)
   self.assertEqual(a.parts['Portal.tie0.ceiling'].origin[2],room['ceiling'])
 def test_desk_module_moves_rigidly(self):
  v=build(shared_desk=True);o=self.p['desk_offset']
  self.assertEqual(self.a.boards['Desk.top']['bounds'][2]-v.boards['Desk.top']['bounds'][2],o)
  self.assertEqual(o,self.p['rows'][1]-1300)
  for k in ('Desk.top','Desk.service_shelf','Desk.shelf0','Desk.shelf1','Desk.shelf2','Speaker0.platform','Speaker1.platform'):
   a,b=self.a.boards[k],v.boards[k];self.assertEqual(a['bounds'][1]-a['bounds'][0],b['bounds'][1]-b['bounds'][0],k);self.assertEqual(a['bottom'],b['bottom']);self.assertAlmostEqual(a['bounds'][3]-a['bounds'][2],b['bounds'][3]-b['bounds'][2])
   self.assertAlmostEqual(a['bounds'][2]-b['bounds'][2],o);self.assertAlmostEqual(a.get('rotation_degrees',0),b.get('rotation_degrees',0))
 def test_no_upright_is_doubled(self):
  cols=list(self.a.columns.values());self.assertNotIn('PB2',self.a.columns);self.assertNotIn('PB3',self.a.columns)
  self.assertGreaterEqual(min(math.hypot(a['x']-b['x'],a['y']-b['y']) for i,a in enumerate(cols) for b in cols[i+1:]),200)
 def test_desk_posts_are_the_rear_divider_row(self):
  xs=self.p['xs'];yb=self.p['rows'][1]
  self.assertEqual((self.a.columns['DS0']['x'],self.a.columns['DS0']['y']),(xs[2],yb));self.assertEqual((self.a.columns['SB0']['x'],self.a.columns['SB0']['y']),(xs[3],yb))
  for c in ('DS0','SB0'):
   tubes=[self.a.parts[t] for t in self.a.columns[c]['tubes']];self.assertGreaterEqual(max(t.origin[2]+t.data['length'] for t in tubes),self.g['tie_z']+45)
   self.assertTrue(any(k.startswith('ShelfCross.') and c in k for k in self.a.parts))
 def test_tower_sleeves_clear_the_desk_low_cross(self):
  supports=[s[0] for s in self.a.boards['Portal.shelfR1']['supports']];self.assertTrue(all(s.startswith('Portal.shelfR1.') for s in supports))
  for c in self.a.clamps:
   if c['host'].split('.')[0]=='SB0' or (c['host'].split('.')[0]=='DS0' and c['id']!='Desk.low0.tee'):self.assertGreaterEqual(abs(c['z']-235)-c['half'],30,c['id'])
  self.assertLessEqual(self.a.parts['SB0.upper'].origin[2]+self.a.parts['SB0.upper'].data['length'],ROOM['ceiling']-100)
 def test_wardrobe_stays_inside_the_room_and_drops_the_wear_rail(self):
  self.assertLessEqual(self.a.columns['RF2']['y'],5214);self.assertFalse(any(k.startswith('Wear.') for k in self.a.parts));self.assertFalse(any(k.startswith('Rack.fold') for k in self.a.boards))
if __name__=='__main__':unittest.main()
