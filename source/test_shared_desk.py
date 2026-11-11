import unittest,math,copy,json
from pathlib import Path
from pipe_engine import build,PROFILE,STOCK,DesignError,board_outline,point_in_board,room_geometry,WALL_X,EAR_MM,SPEAKER_TRAY
class SharedDesk(unittest.TestCase):
 def setUp(self):self.a=build(shared_desk=True)
 def test_stock_mates_and_clearances(self):
  self.assertEqual(self.a.validate()['geometry_errors'],[])
  for p in self.a.parts.values():
   if p.kind.startswith('tube_'):self.assertEqual(p.data['length'],int(p.kind[5:]));self.assertIn(p.data['length'],STOCK)
 def test_rear_legs_and_old_endframes_removed(self):
  self.assertNotIn('DB0',self.a.columns);self.assertNotIn('DB1',self.a.columns)
  self.assertFalse(any(id.startswith(('Desk.endframe','Desk.tail','Desk.lower_wall')) for id in self.a.parts))
  for c in ('DS0','SB0','RF0','RB0','DF0','DF1'):self.assertEqual(self.a.mounts[c+'.foot'],'floor')
 def test_front_legs_end_below_board(self):
  for i in range(2):
   self.assertEqual([self.a.parts[t].kind for t in self.a.columns[f'DF{i}']['tubes']],['tube_602','tube_40']);self.assertEqual(self.a.parts[f'DF{i}.elbow'].kind,'elbow')
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
 def test_low_line_crosses_the_rear_post_and_tees_the_others(self):
  for i in range(2):
   low=f'Desk.low{i}';y=self.a.columns[f'DF{i}']['y']
   cross=self.a.parts[f'{low}.cross_rear'];self.assertEqual(cross.kind,'cross');self.assertEqual(cross.origin,(self.a.columns[('SB0','RB0')[i]]['x'],y,235))
   for suffix in ('up','down','in','out'):self.assertIn(self.a.ports[f'{low}.cross_rear.{suffix}'].used,self.a.ports,suffix)
   self.assertEqual(self.a.parts[f'{low}.tee'].kind,'slide_tee');self.assertEqual(self.a.parts[f'{low}.tee'].origin[2],235);self.assertEqual(self.a.parts[f'{low}.rear'].kind,'tube_250');self.assertEqual(self.a.parts[f'{low}.wall'].kind,'tube_40')
   self.assertEqual(self.a.mounts[f'{low}.wall_flange'],'wall')
   for suffix in ('t1','t2'):
    t=self.a.parts[f'{low}.front.{suffix}'];self.assertEqual(t.kind,'slide_tee');self.assertEqual(t.origin[2],400)
   self.assertFalse(any(k.startswith(f'{low}.cross_') and not k.endswith('rear') for k in self.a.parts));self.assertNotIn(f'{low}.stub',self.a.parts)
  posts=('DS0','SB0','RF0','RB0','DF0','DF1');low_clamps=sorted(c['id'] for c in self.a.clamps if c['host'].split('.')[0] in posts and c['z']<self.a.boards['Desk.top']['bottom'])
  self.assertEqual(low_clamps,sorted(['Desk.shared0.1.tee','Desk.shared1.1.tee','Desk.low0.tee','Desk.low1.tee','Desk.low0.front.t1','Desk.low0.front.t2','Desk.low1.front.t1','Desk.low1.front.t2']))
  self.assertFalse(any(id.startswith(('Desk.low_front','Desk.low_depth','Desk.low_wall','Desk.service0','Desk.service1','Rack.depth0.')) for id in self.a.parts))
  self.assertIn('Rack.depth1.200.tube',self.a.parts)
 def test_crosses_split_uprights_and_rehost_every_clamp(self):
  for c in ('DS0','RF0'):
   self.assertEqual([self.a.parts[t].data['length'] for t in self.a.columns[c]['tubes']],[602,40,40,1500])
   self.assertEqual(self.a.parts[c+'.upper'].origin[2]+1500,2261)
  for c in ('SB0','RB0'):
   self.assertEqual([self.a.parts[t].data['length'] for t in self.a.columns[c]['tubes']],[200,1000,1000])
   self.assertEqual(self.a.parts[c+'.upper'].origin[2]+1000,2267)
  for clamp in self.a.clamps:self.assertEqual(self.a.parts[clamp['id']].data['host'],clamp['host'])
  for id in ('Desk.wall0.1200.tee','Speaker0.arm1.tee','ShelfCross.DS0.SB0.1525.t2','Rack.wall0.tee','Rack.clean0.950.t1'):self.assertIn(id,self.a.parts)
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
 def test_entrance_corner_is_rounded_without_losing_supports(self):
  b=self.a.boards['Desk.top'];x0,x1,y0,y1=b['bounds'];self.assertEqual(b['corner_radii'],[[x0,y0,100]])
  self.assertGreaterEqual(min(math.hypot(x-2410,y-735) for x,y in board_outline(b)),670)
  self.assertFalse(point_in_board(x0+5,y0+5,b));self.assertTrue(point_in_board(x0+5,y0+150,b))
  for sid,x,y,z in b['supports']:self.assertTrue(point_in_board(x,y,b,-15),sid)
 def test_speaker_trays_sit_inside_the_shelf_column(self):
  desk=self.a.boards['Desk.top']['bounds'];middle=(desk[2]+desk[3])/2;shelf=self.a.boards['Desk.shelf0']['bounds']
  for i in range(2):
   b=self.a.boards[f'Speaker{i}.platform'];x0,x1,y0,y1=b['bounds']
   self.assertEqual((x1-x0,y1-y0,b.get('rotation_degrees',0)),(SPEAKER_TRAY,SPEAKER_TRAY,0));self.assertEqual(x0,shelf[0]);self.assertLessEqual(x1,WALL_X-20)
   self.assertEqual(len(b['supports']),4);self.assertEqual(self.a.parts[f'Speaker{i}.platform'].data['speaker_target_mm'],[EAR_MM[0],middle,EAR_MM[1]])
   for col in (('DS0','SB0'),('RF0','RB0'))[i]:
    post=self.a.columns[col];self.assertFalse(point_in_board(post['x'],post['y'],b,17),col)
  l=self.a.boards['Speaker0.platform']['bounds'];r=self.a.boards['Speaker1.platform']['bounds'];self.assertAlmostEqual(middle-l[2],r[3]-middle)
 def test_wall_plane_comes_from_room_file(self):
  room=room_geometry();self.assertEqual(room['wall_x'],WALL_X)
  if not room['wall_measured']:self.assertEqual(WALL_X,3450)
  for id,surface in self.a.mounts.items():
   if surface=='wall':self.assertEqual(self.a.parts[id].origin[0],WALL_X)
 def test_speakers_and_upper_shelves_preserved(self):
  before=build(side_speakers=True)
  for id in ('Speaker0.platform','Speaker1.platform','Desk.shelf0','Desk.shelf1','Desk.shelf2','Rack.top0','Rack.fold0'):
   self.assertEqual(self.a.boards[id],before.boards[id])
  self.assertNotIn('TV',self.a.parts)
 def test_service_shelf_hangs_on_separate_brackets(self):
  b=self.a.boards['Desk.service_shelf'];self.assertEqual(b['bounds'][0]-self.a.boards['Desk.top']['bounds'][0],472)
  self.assertEqual(self.a.boards['Desk.top']['bottom']-b['bottom']-b['thickness'],186)
  self.assertEqual(len(b['supports']),4)
  for sid,x,y,z in b['supports']:
   p=self.a.parts[sid];self.assertEqual(p.kind,'bracket');self.assertEqual(self.a.mounts[sid],'wall');self.assertEqual(p.origin[0],WALL_X);self.assertEqual((x,z),(WALL_X-p.data['reach'],b['bottom']))
  self.assertFalse(any(p.kind.startswith('tube_') and abs(p.axis[2])<.5 and 400<p.origin[2]<650 for p in self.a.parts.values()))
 def test_front_devices_stay_outside_seated_knees(self):
  d=json.loads((Path(__file__).parent/'equipment-layout.json').read_text());y0,y1=d['knee_zone']['bounds'][2:]
  for m in d['mounts']:
   b=m['bounds'];self.assertTrue(b[3]<=y0 or b[2]>=y1)
  mac=next(x for x in d['devices'] if x['id']=='Mac mini M1');self.assertEqual(mac['size'],[197,197,36])
  self.assertEqual(d['shelf']['clear_height'],self.a.boards['Desk.top']['bottom']-d['shelf']['bottom']-d['shelf']['thickness'])
  top=self.a.boards['Desk.top']['bottom']+28
  for item in d['desk_items']:
   if 'size' in item and not item.get('static'):self.assertEqual(item['location'][2]-item['size'][2]/2,top,item['id'])
if __name__=='__main__':unittest.main()
