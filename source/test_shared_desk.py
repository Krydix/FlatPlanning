import unittest,math,copy,json
from pathlib import Path
from pipe_engine import build,PROFILE,STOCK
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
   self.assertEqual(self.a.parts[f'Desk.shared{i}.0.tube'].kind,'tube_250');self.assertEqual(self.a.parts[f'Desk.shared{i}.1.tube'].kind,'tube_200')
   for j in range(2):self.assertEqual(self.a.parts[f'Desk.shared{i}.{j}.tee'].kind,'slide_tee')
 def test_four_frame_bores_only(self):
  holes=self.a.boards['Desk.top']['holes'];self.assertEqual(len(holes),4)
  for c in ('DS0','SB0','RF0','RB0'):
   post=self.a.columns[c];self.assertIn((post['x'],post['y'],44),holes)
 def test_full_desktop_and_derived_height(self):
  b=self.a.boards['Desk.top'];x0,x1,y0,y1=b['bounds'];self.assertEqual((y1-y0,x1-x0,b['thickness']),(1615,702,28));self.assertEqual(b['bottom']+28,732)
  p=copy.deepcopy(PROFILE);p['elbow_stop']['value']=21;a=build(p,shared_desk=True);self.assertEqual(a.boards['Desk.top']['bottom']+28,733);self.assertEqual(a.validate()['geometry_errors'],[])
 def test_entry_with_feet_retains_600(self):
  x0,x1,y0,y1=self.a.boards['Desk.top']['bounds'];self.assertGreaterEqual(math.hypot(x0-2410,y0-735),600)
  foot=self.a.columns['DF0'];self.assertGreaterEqual(math.hypot(foot['x']-2410,foot['y']-735)-35,600)
 def test_speakers_and_upper_shelves_preserved(self):
  before=build(side_speakers=True)
  for id in ('Speaker0.platform','Speaker1.platform','Desk.shelf0','Desk.shelf1','Desk.shelf2','Rack.top0','Rack.fold0'):
   self.assertEqual(self.a.boards[id],before.boards[id])
  self.assertNotIn('TV',self.a.parts)
if __name__=='__main__':unittest.main()
