import unittest,math
from pathlib import Path
from pipe_engine import point_in_board
from speaker_placement import speaker_layout,candidates,clearance,obstacles
import json
ROOT=Path(__file__).resolve().parent.parent
class SpeakerPlacement(unittest.TestCase):
 def setUp(self):
  self.left,self.right=speaker_layout(ROOT);self.graph=json.loads((ROOT/'source/assembly.json').read_text());self.cfg=json.loads((ROOT/'source/equipment-layout.json').read_text())
 def test_mirrored_and_equidistant(self):
  self.assertEqual(self.left['centre'][0],self.right['centre'][0]);mid=sum(self.graph['boards']['Desk.top']['bounds'][2:])/2
  self.assertAlmostEqual(mid-self.left['centre'][1],self.right['centre'][1]-mid,places=0)
 def test_fully_on_tray_and_clear_of_frame(self):
  for side,tray in zip((self.left,self.right),self.cfg['speakers']['trays']):
   b=self.graph['boards'][tray];self.assertTrue(all(point_in_board(x,y,b,-5) for x,y in side['footprint']))
   self.assertGreaterEqual(side['nearest'][0],15)
 def test_pushed_rear_and_outward_from_tray_centre(self):
  for side,tray in zip((self.left,self.right),self.cfg['speakers']['trays']):
   b=self.graph['boards'][tray];cx=(b['bounds'][0]+b['bounds'][1])/2;cy=(b['bounds'][2]+b['bounds'][3])/2;mid=sum(self.graph['boards']['Desk.top']['bounds'][2:])/2
   self.assertGreater(side['centre'][0],cx);self.assertGreater(abs(side['centre'][1]-mid),abs(cy-mid))
   self.assertGreaterEqual(math.dist(side['centre'],(cx,cy)),25)
 def test_clearance_detects_overlap(self):
  square=[(0,0),(10,0),(10,10),(0,10)];self.assertEqual(clearance(square,(5,5),(5,5)),-1);self.assertAlmostEqual(clearance(square,(13,5),(13,5)),3)
if __name__=='__main__':unittest.main()
