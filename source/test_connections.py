import unittest,copy,tempfile,json
from pathlib import Path
from pipe_engine import *
class ConnectionRules(unittest.TestCase):
 def test_complete_graph(self):self.assertEqual(build().validate()['geometry_errors'],[])
 def test_no_pipe_to_pipe(self):
  a=Assembly();a.tube('a',250,(0,0,0),(1,0,0));a.tube('b',250,(250,0,0),(1,0,0))
  with self.assertRaisesRegex(DesignError,'male/female'):a.connect('a.b','b.a')
 def test_wrong_family(self):
  a=Assembly();a.flange('f',(0,0,0),(0,0,1),'floor');a.tube('t',250,(0,0,15),(0,0,1));a.ports['t.a'].family='old-26mm'
  with self.assertRaisesRegex(DesignError,'family'):a.connect('f.socket','t.a')
 def test_socket_occupied(self):
  a=Assembly();a.flange('f',(0,0,0),(0,0,1),'floor');a.from_port('t',250,'f.socket')
  with self.assertRaisesRegex(DesignError,'free female'):a.from_port('q',250,'f.socket')
 def test_stock_only(self):
  with self.assertRaisesRegex(DesignError,'stock length'):Assembly().tube('t',580,(0,0,0),(1,0,0))
 def test_unseated(self):
  a=Assembly();a.flange('f',(0,0,0),(0,0,1),'floor');a.tube('t',250,(0,0,16),(0,0,1))
  with self.assertRaisesRegex(DesignError,'seated'):a.connect('f.socket','t.a')
 def test_opposed_axes(self):
  a=Assembly();a.flange('f',(0,0,0),(0,0,1),'floor');a.tube('t',250,(0,0,15),(1,0,0))
  with self.assertRaisesRegex(DesignError,'opposed'):a.connect('f.socket','t.a')
 def test_flange_wall_plane(self):
  with self.assertRaisesRegex(DesignError,'plane'):Assembly().flange('f',(3400,0,0),(-1,0,0),'wall')
 def test_no_floating_wood(self):
  with self.assertRaisesRegex(DesignError,'four'):Assembly().board('b',(0,500,0,500),500,28,[])
 def test_coupling_no_clamp(self):
  a=build()
  with self.assertRaisesRegex(DesignError,'coupling'):a.clamp('bad','RF0',1020,(1,0,0))
 def test_clamp_overlap(self):
  a=build()
  with self.assertRaisesRegex(DesignError,'Overlapping'):a.clamp('bad','RF0',960,(1,0,0))
 def test_span_requires_stock(self):
  a=Assembly();a.column('a',0,0);a.column('b',580,0)
  with self.assertRaisesRegex(DesignError,'bridge'):a.bridge('bad','a','b',500,602)
 def test_rail_change_transaction(self):
  a=build();a.move_rail('Rack.clean0.950.tube',900);self.assertEqual(a.parts['Rack.clean0.950.tube'].origin[2],900);self.assertEqual(a.validate()['geometry_errors'],[])
 def test_bad_edit_rolls_back(self):
  a=build();before=a.parts['Rack.clean0.950.tube'].origin
  with self.assertRaises(DesignError):a.move_rail('Rack.clean0.950.tube',1020)
  self.assertEqual(a.parts['Rack.clean0.950.tube'].origin,before)
 def test_tamper_length(self):
  a=build();a.parts['Wear.rail'].data['length']=580;self.assertTrue(a.validate()['geometry_errors'])
 def test_tamper_position(self):
  a=build();a.parts['Wear.rail'].origin=(0,0,0);self.assertTrue(a.validate()['geometry_errors'])
 def test_board_post_without_bore(self):
  a=build();a.boards['Desk.top']['holes']=[];self.assertTrue(any('Unbored' in x for x in a.validate()['geometry_errors']))
 def test_driver_overload(self):
  with self.assertRaisesRegex(DesignError,'driver'):build().light_check('Desk.shelf0',count=6)
 def test_too_thin_recess_board(self):
  a=build();a.boards['Desk.shelf0']['thickness']=28
  with self.assertRaisesRegex(DesignError,'timber'):a.light_check('Desk.shelf0')
 def test_clips_need_clearance(self):
  with self.assertRaisesRegex(DesignError,'clips'):build().light_check('Desk.shelf0',clip=6)
 def test_export_gate(self):self.assertTrue(build().validate(fabrication=True)['geometry_errors'])
 def test_roundtrip(self):
  a=build()
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'assembly.json';a.save(p);b=Assembly.load(p);self.assertEqual(b.validate()['geometry_errors'],[]);self.assertEqual(a.bom(),b.bom())
 def test_pipe_crossing(self):
  a=build();a.tube('crash',250,(3000,3000,500),(1,0,0));a.tube('cross',250,(3100,2900,500),(0,1,0));self.assertTrue(any('intersect' in x for x in a.validate()['geometry_errors']))
 def test_calibrated_tee_offset_recalculates_all_spans(self):
  p=copy.deepcopy(PROFILE);p['tee_stop']['value']=21;p['tee_stop']['status']='measured';a=build(p);self.assertEqual(a.validate()['geometry_errors'],[]);self.assertEqual(a.boards['Desk.top']['bounds'][3]-a.boards['Desk.top']['bounds'][2],1617)
 def test_separate_middle_holder_measurement(self):
  p=copy.deepcopy(PROFILE);p['middle_holder_wing']['value']=35;a=build(p);self.assertEqual(a.validate()['geometry_errors'],[])
 def test_measurement_file(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/'m.json';f.write_text(json.dumps({'values_mm':{'flange_stop':17}}));p=profile_from_measurements(f);self.assertEqual(p['flange_stop']['value'],17);self.assertEqual(p['flange_stop']['status'],'measured')
class SharedShelfReview(unittest.TestCase):
 def test_shared_far_frame(self):
  a=build();left={a.parts[s[0]].data['host'] for s in a.boards['Desk.shelf2']['supports']};right={a.parts[s[0]].data['host'] for s in a.boards['Rack.top0']['supports']};self.assertEqual(len(left&right),1)
 def test_every_saddle_has_two_tee_crosspipe(self):
  a=build()
  for p in a.parts.values():
   if p.kind!='saddle':continue
   host=p.data['host'];tube=a.parts[host];self.assertLess(abs(tube.axis[2]),.001)
   for suffix in ['a','b']:self.assertEqual(a.parts[a.ports[a.ports[host+'.'+suffix].used].owner].kind,'slide_tee')
 def test_no_unverified_split_holders(self):
  a=build();self.assertEqual(a.bom()['end_holder']+a.bom()['middle_holder'],0);self.assertEqual(a.bom()['saddle'],48)
 def test_vertical_saddle_rejected(self):
  a=build()
  with self.assertRaisesRegex(DesignError,'horizontal'):a.saddle('bad','RF0.lower',500,(0,1,0))
 def test_saddle_tamper_rejected(self):
  a=build();p=next(p for p in a.parts.values() if p.kind=='saddle');p.origin=add(p.origin,(0,0,5));self.assertTrue(any('saddle detached' in e for e in a.validate()['geometry_errors']))
class WardrobeUse(unittest.TestCase):
 def test_one_long_coat_rail(self):
  a=build();rails=[p for k,p in a.parts.items() if k.startswith('Rack.clean2.') and p.kind.startswith('tube_')];self.assertEqual(len(rails),1);self.assertEqual(rails[0].origin[2],1950)
 def test_pullover_openings(self):
  a=build();levels=[a.boards['Rack.fold'+str(i)] for i in range(4)]+[a.boards['Rack.top1']];gaps=[b['bottom']-(a0['bottom']+a0['thickness']) for a0,b in zip(levels,levels[1:])];self.assertEqual(gaps,[372,372,322,312]);self.assertGreaterEqual(gaps[-1]-40,270)
 def test_longest_coat_clears_shoes(self):
  a=build();b=a.boards['Rack.coat_shoes'];self.assertGreaterEqual(1950-70-1500-b['bottom']-b['thickness']-100,50)
if __name__=='__main__':unittest.main(verbosity=2)
