import unittest,math,copy,json
from pathlib import Path
from pipe_engine import build,PROFILE,STOCK,DesignError
class SharedDesk(unittest.TestCase):
 def setUp(self):self.a=build(shared_desk=True)
 def test_stock_mates_and_clearances(self):
  self.assertEqual(self.a.validate()['geometry_errors'],[])
  for p in self.a.parts.values():
   if p.kind.startswith('tube_'):self.assertEqual(p.data['length'],int(p.kind[5:]));self.assertIn(p.data['length'],STOCK)
 def test_rear_legs_and_old_endframes_removed(self):
  self.assertNotIn('DB0',self.a.columns);self.assertNotIn('DB1',self.a.columns)
  self.assertFalse(any(id.startswith(('Desk.endframe','Desk.tail','Desk.lower_wall')) for id in self.a.parts))
  for c in ('DS0','SB0','RF0','RB0'):self.assertEqual(self.a.mounts[c+'.foot'],'floor')
 def test_front_legs_end_below_board(self):
  for i in range(2):
   self.assertEqual(self.a.parts[f'DF{i}.lower'].kind,'tube_602');self.assertEqual(self.a.parts[f'DF{i}.upper'].kind,'tube_40');self.assertEqual(self.a.parts[f'DF{i}.elbow'].kind,'elbow')
   end=self.a.parts[f'DF{i}.upper'].origin[2]+40;self.assertLess(end,self.a.boards['Desk.top']['bottom'])
   x=self.a.columns[f'DF{i}']['x'];y=self.a.columns[f'DF{i}']['y'];self.assertFalse(any(h[:2]==(x,y) for h in self.a.boards['Desk.top']['holes']))
 def test_eight_saddles_and_real_arms(self):
  self.assertEqual(len(self.a.boards['Desk.top']['supports']),8)
  for i in range(2):
   self.assertEqual(self.a.parts[f'Desk.shared{i}.0.tube'].kind,'tube_250');self.assertEqual(self.a.parts[f'Desk.shared{i}.1.tube'].kind,'tube_250')
   self.assertEqual(self.a.parts[f'Desk.shared{i}.1.tee'].kind,'slide_tee')
   self.assertEqual(self.a.parts[f'Desk.cross{i}'].kind,'cross')
   for suffix in ('up','down','in','out'):self.assertIn(self.a.ports[f'Desk.cross{i}.{suffix}'].used,self.a.ports)
   self.assertNotIn(f'Desk.shared{i}.1.cap',self.a.parts)
 def test_lower_front_braces_have_real_seated_tees(self):
  for i in range(2):
   for suffix in ('t1','t2'):
    t=self.a.parts[f'Desk.low_front{i}.{suffix}'];self.assertEqual(t.kind,'slide_tee');self.assertEqual(t.origin[2],400)
   self.assertEqual(self.a.parts[f'Desk.low_depth{i}.t1'].origin[2],300)
 def test_crosses_split_uprights_and_rehost_every_clamp(self):
  for c in ('DS0','RF0'):
   self.assertEqual([self.a.parts[t].data['length'] for t in self.a.columns[c]['tubes']],[602,40,1500,40])
   self.assertEqual(self.a.parts[c+'.upper'].origin[2]+1500,2261)
  for clamp in self.a.clamps:self.assertEqual(self.a.parts[clamp['id']].data['host'],clamp['host'])
 def test_cross_movement_is_rejected(self):
  self.a.parts['Desk.cross0'].origin=(3086,1300,689)
  self.assertTrue(any('cross port moved independently' in error for error in self.a.validate()['geometry_errors']))
 def test_four_frame_bores_only(self):
  holes=self.a.boards['Desk.top']['holes'];self.assertEqual(len(holes),4)
  for c in ('DS0','SB0','RF0','RB0'):
   post=self.a.columns[c];self.assertIn((post['x'],post['y'],44),holes)
 def test_full_desktop_and_derived_height(self):
  b=self.a.boards['Desk.top'];x0,x1,y0,y1=b['bounds'];self.assertEqual((y1-y0,x1-x0,b['thickness']),(1615,702,28));self.assertEqual(b['bottom']+28,732)
  p=copy.deepcopy(PROFILE);p['elbow_stop']['value']=21
  with self.assertRaises(DesignError):build(p,shared_desk=True)
  p['cross_stop']['value']=21;p['tee_stop']['value']=21;a=build(p,shared_desk=True);self.assertEqual(a.boards['Desk.top']['bottom']+28,733);self.assertEqual(a.validate()['geometry_errors'],[])
 def test_entry_with_feet_retains_600(self):
  x0,x1,y0,y1=self.a.boards['Desk.top']['bounds'];self.assertGreaterEqual(math.hypot(x0-2410,y0-735),600)
  foot=self.a.columns['DF0'];self.assertGreaterEqual(math.hypot(foot['x']-2410,foot['y']-735)-35,600)
 def test_speakers_and_upper_shelves_preserved(self):
  before=build(side_speakers=True)
  for id in ('Speaker0.platform','Speaker1.platform','Desk.shelf0','Desk.shelf1','Desk.shelf2','Rack.top0','Rack.fold0'):
   self.assertEqual(self.a.boards[id],before.boards[id])
  self.assertNotIn('TV',self.a.parts)
 def test_service_shelf_keeps_rear_depth_and_device_height(self):
  b=self.a.boards['Desk.service_shelf'];self.assertEqual(b['bounds'][0]-self.a.boards['Desk.top']['bounds'][0],472)
  self.assertEqual(self.a.boards['Desk.top']['bottom']-b['bottom']-b['thickness'],186)
  self.assertEqual(len(b['supports']),4)
  for i in range(2):
   self.assertEqual(self.a.parts[f'Desk.service{i}.t1'].kind,'slide_tee')
   self.assertEqual(self.a.parts[f'Desk.low_wall{i}.tee'].origin[2],400)
 def test_front_devices_stay_outside_seated_knees(self):
  d=json.loads((Path(__file__).parent/'equipment-layout.json').read_text());y0,y1=d['knee_zone']['bounds'][2:]
  for m in d['mounts']:
   b=m['bounds'];self.assertTrue(b[3]<=y0 or b[2]>=y1)
  mac=next(x for x in d['devices'] if x['id']=='Mac mini M1');self.assertEqual(mac['size'],[197,197,36])
if __name__=='__main__':unittest.main()
