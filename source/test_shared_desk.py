import unittest,math,copy,json
from pathlib import Path
from pipe_engine import build,PROFILE,STOCK,DesignError,board_outline,point_in_board,room_geometry,WALL_X,EAR_MM,SPEAKER_TRAY,ROOM
class SharedDesk(unittest.TestCase):
 def setUp(self):self.a=build(shared_desk=True)
 def test_stock_mates_and_clearances(self):
  self.assertEqual(self.a.validate()['geometry_errors'],[])
  for p in self.a.parts.values():
   if p.kind.startswith('tube_'):self.assertEqual(p.data['length'],int(p.kind[5:]));self.assertIn(p.data['length'],STOCK)
 def test_front_legs_end_below_board(self):
  for i in range(2):
   self.assertEqual([self.a.parts[t].kind for t in self.a.columns[f'DF{i}']['tubes']],['tube_602','tube_40']);self.assertEqual(self.a.parts[f'DF{i}.elbow'].kind,'elbow')
   end=self.a.parts[f'DF{i}.upper'].origin[2]+40;self.assertLess(end,self.a.boards['Desk.top']['bottom'])
   x=self.a.columns[f'DF{i}']['x'];y=self.a.columns[f'DF{i}']['y'];self.assertFalse(any(h[:2]==(x,y) for h in self.a.boards['Desk.top']['holes']))
 def test_cross_movement_is_rejected(self):
  self.a.parts['Desk.cross0'].origin=(3086,1300,689)
  self.assertTrue(any('cross port moved independently' in error for error in self.a.validate()['geometry_errors']))
 def test_four_frame_bores_only(self):
  holes=self.a.boards['Desk.top']['holes'];self.assertEqual(len(holes),4)
  for c in ('DS0','SB0','RF0','RB0'):
   post=self.a.columns[c];self.assertIn((post['x'],post['y'],44),holes)
 def test_entry_with_feet_retains_600(self):
  x0,x1,y0,y1=self.a.boards['Desk.top']['bounds'];self.assertGreaterEqual(math.hypot(x0-2410,y0-735),600)
  foot=self.a.columns['DF0'];self.assertGreaterEqual(math.hypot(foot['x']-2410,foot['y']-735)-35,600)
 def test_entrance_corner_is_rounded_without_losing_supports(self):
  b=self.a.boards['Desk.top'];x0,x1,y0,y1=b['bounds'];self.assertEqual(b['corner_radii'],[[x0,y0,100]])
  self.assertGreaterEqual(min(math.hypot(x-2410,y-735) for x,y in board_outline(b)),670)
  self.assertFalse(point_in_board(x0+5,y0+5,b));self.assertTrue(point_in_board(x0+5,y0+150,b))
  for sid,x,y,z in b['supports']:self.assertTrue(point_in_board(x,y,b,-15),sid)
 def test_wall_plane_comes_from_room_file(self):
  room=room_geometry();self.assertEqual(room['wall_x'],WALL_X)
  if not room['wall_measured']:self.assertEqual(WALL_X,3450)
  for id,surface in self.a.mounts.items():
   if surface=='wall':self.assertEqual(self.a.parts[id].origin[0],WALL_X)
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
 def test_post_bores_open_to_the_edge_instead_of_leaving_a_thin_web(self):
  for id,count in (('Desk.top',4),('Desk.service_shelf',2)):
   b=self.a.boards[id];X0,X1,Y0,Y1=b['bounds'];self.assertEqual(len(b['notches']),count);self.assertEqual(self.a.parts[id].data['notches'],b['notches'])
   for x,y,diam in b['holes']:
    r=diam/2;inside=[n for n in b['notches'] if n[0]<=x-r+.01 and n[1]>=min(x+r,X1)-.01]
    self.assertTrue(inside,(id,x,y))
    for edge,web in ((X1,X1-x-r),(Y1,Y1-y-r),(Y0,y-r-Y0)):
     if web<20:self.assertTrue(any(edge in n for n in inside),(id,x,y,edge))
   for sid,x,y,z in b['supports']:self.assertFalse(any(n[0]-10<x<n[1]+10 and n[2]-10<y<n[3]+10 for n in b['notches']),sid)
  for id in ('Desk.shelf0','Rack.top0','Speaker0.platform'):self.assertNotIn('notches',self.a.boards[id])
 def test_no_sliding_fitting_anywhere(self):
  kinds={p.kind for p in self.a.parts.values()};self.assertNotIn('slide_tee',kinds);self.assertNotIn('end_holder',kinds)
  # The only clamps left are saddle straps on horizontal arms: nothing is held at its height by a clamp on a post.
  for c in self.a.clamps:
   self.assertEqual(self.a.parts[c['id']].kind,'saddle');self.assertLess(abs(self.a.parts[c['host']].axis[2]),.5)
 def test_threaded_parts_never_close_a_loop(self):
  # A frame closed only by threads cannot be screwed together: the thread graph must be a forest.
  parent={}
  def find(k):
   while parent.setdefault(k,k)!=k:parent[k]=parent[parent[k]];k=parent[k]
   return k
  threads=[e for e in self.a.edges if e[2]=='thread'];self.assertGreater(len(threads),200)
  for a,b,*_ in threads:
   ra,rb=find(a),find(b);self.assertNotEqual(ra,rb,f'thread loop closed by {a} / {b}');parent[ra]=rb
 def test_levels_follow_the_stock_stacks(self):
  self.assertEqual(self.a.levels,{'Sh':185,'D':689,'F1':689,'Rl':929,'S':1029,'F2':1029,'W':1369,'A1':1469,'F3':1469,'A2':1809,'F4':1809,'tie':1909,'R':1909,'T':2149})
  for c in ('DS0','SB0','RF0','RB0','RF1','RB1'):self.assertEqual([self.a.parts[t].data['length'] for t in self.a.columns[c]['tubes']][:2],[602,40])
  for id,bottom in (('Desk.shelf0',1484),('Desk.shelf1',1824),('Desk.shelf2',2164),('Rack.top0',2164),('Rack.fold0',704),('Rack.fold1',1044),('Rack.fold2',1484),('Rack.fold3',1824),('Rack.coat_shoes',200),('Speaker0.platform',1044)):
   self.assertEqual(self.a.boards[id]['bottom'],bottom,id)
  # A different seating depth moves every level, and the stacks either still agree or the build is rejected.
  p=copy.deepcopy(PROFILE);p['cross_stop']['value']=21;p['elbow_stop']['value']=21
  try:
   b=build(p,shared_desk=True);self.assertEqual(b.validate()['geometry_errors'],[]);self.assertNotEqual(b.levels['T'],2149)
  except DesignError as error:self.assertIn('level',str(error))
 def test_every_board_rests_on_four_capped_arms(self):
  for id,b in self.a.boards.items():
   if id in ('Desk.top','Desk.service_shelf'):continue
   arms={self.a.parts[s[0]].data['host'] for s in b['supports']};self.assertEqual(len(arms),2 if id.startswith('Speaker') else 4,id)
   x0,x1,y0,y1=b['bounds']
   for t in arms:
    tube=self.a.parts[t];self.assertEqual(tube.kind,'tube_250');self.assertEqual(abs(tube.axis[1]),1);self.assertEqual(self.a.parts[t[:-5]+'.cap'].kind,'cap')
    self.assertAlmostEqual(tube.origin[2]+self.a.v('saddle_rise'),b['bottom'])
   # Boards stop clear of the fitting castings at the posts.
   for col in self.a.columns.values():
    if x0<col['x']<x1:self.assertFalse(y0-30<col['y']<y1+30 and not id.startswith('Speaker'),id)
 def test_desk_crosses_and_wall_fixings(self):
  for i in range(2):
   for id in (f'Desk.cross{i}',f'Desk.cross_rear{i}'):
    self.assertEqual(self.a.parts[id].kind,'cross');self.assertEqual(self.a.parts[id].origin[2],689)
    for suffix in ('up','down','in','out'):self.assertIn(self.a.ports[f'{id}.{suffix}'].used,self.a.ports)
   self.assertEqual(self.a.parts[f'Desk.shared{i}.0.tube'].kind,'tube_250');self.assertEqual(self.a.parts[f'Desk.shared{i}.1.tube'].kind,'tube_250')
   self.assertEqual(self.a.parts[f'Desk.shared{i}.1.wall'].kind,'tube_40');self.assertEqual(self.a.mounts[f'Desk.shared{i}.1.wall_flange'],'wall')
  self.assertEqual(len(self.a.boards['Desk.top']['supports']),8);self.assertFalse(any(id.startswith('Desk.low') for id in self.a.parts))
  walls=sorted(p.origin[2] for id,p in self.a.parts.items() if self.a.mounts.get(id)=='wall' and p.kind=='flange');self.assertEqual(walls,[689,689,1909,1909,1909,1909,1909])
  # Sockets and their feeds usually run 150-450 mm above the floor; no flange screw goes into that band.
  for z in walls:self.assertFalse(150-35<=z<=450+35)
 def test_rails_hang_like_before(self):
  for id,L,z,x in (('Rack.clean0.1909.tube',1000,1909,3085),('Rack.clean2.1909.tube',602,1909,3085),('Rack.clean0.929.tube',1000,929,3135),('Wear.rail',602,1369,2945)):
   t=self.a.parts[id];self.assertEqual(t.data['length'],L);self.assertEqual(t.origin[2],z);self.assertEqual(t.origin[0],x);self.assertEqual(t.axis,(0,1,0))
  # The lower rail hangs from the rear posts so that no two posts share two threaded pipes.
  self.assertEqual(self.a.ports['RB0.joint.Rl.out'].used,'Rack.clean0.929.arm0.tube.a')
 def test_top_boards_still_take_the_crates(self):
  top=self.a.boards['Rack.top0'];self.assertEqual(top['bottom']+top['thickness'],2192)
  self.assertGreaterEqual(ROOM['ceiling']-(2192+250),150)
  self.assertGreaterEqual(top['bounds'][3]-top['bounds'][2],2*460);self.assertGreaterEqual(self.a.boards['Rack.top1']['bounds'][3]-self.a.boards['Rack.top1']['bounds'][2],460)
 def test_full_desktop_and_derived_height(self):
  b=self.a.boards['Desk.top'];x0,x1,y0,y1=b['bounds'];self.assertEqual((y1-y0,x1-x0,b['thickness']),(1615,702,28));self.assertEqual(b['bottom']+28,732)
  p=copy.deepcopy(PROFILE);p['elbow_stop']['value']=21
  with self.assertRaises(DesignError):build(p,shared_desk=True)
 def test_speaker_trays_sit_inside_the_shelf_column(self):
  desk=self.a.boards['Desk.top']['bounds'];middle=(desk[2]+desk[3])/2;shelf=self.a.boards['Desk.shelf0']['bounds']
  for i in range(2):
   b=self.a.boards[f'Speaker{i}.platform'];x0,x1,y0,y1=b['bounds']
   self.assertEqual((x1-x0,y1-y0,b.get('rotation_degrees',0)),(SPEAKER_TRAY,SPEAKER_TRAY,0));self.assertEqual(x0,shelf[0]);self.assertLessEqual(x1,WALL_X-20)
   self.assertEqual(len(b['supports']),4);self.assertEqual(self.a.parts[f'Speaker{i}.platform'].data['speaker_target_mm'],[EAR_MM[0],middle,EAR_MM[1]])
   for col in (('DS0','SB0'),('RF0','RB0'))[i]:
    post=self.a.columns[col];self.assertFalse(point_in_board(post['x'],post['y'],b,30),col)
  l=self.a.boards['Speaker0.platform']['bounds'];r=self.a.boards['Speaker1.platform']['bounds'];self.assertAlmostEqual(middle-l[2],r[3]-middle)
if __name__=='__main__':unittest.main()
