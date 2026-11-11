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
 def test_speaker_stays_inside_the_shelf_column(self):
  shelf=self.graph['boards']['Desk.shelf0']['bounds'];wall=self.graph['columns']['SB0']['x']+75
  for side,tray in zip((self.left,self.right),self.cfg['speakers']['trays']):
   b=self.graph['boards'][tray];xs=[x for x,_ in side['footprint']];ys=[y for _,y in side['footprint']]
   # Nothing in front of the shelf line or closer than 20 mm to the wall; the tray is the smallest board that takes the aimed speaker.
   self.assertGreaterEqual(min(xs),shelf[0]);self.assertLessEqual(max(xs),wall-20)
   self.assertLessEqual(b['bounds'][1]-b['bounds'][0]-(max(xs)-min(xs)),2*self.cfg['speakers']['placement']['margin']+10)
   self.assertGreaterEqual(min(ys),b['bounds'][2]+5);self.assertLessEqual(max(ys),b['bounds'][3]-5)
 def test_clearance_detects_overlap(self):
  square=[(0,0),(10,0),(10,10),(0,10)];self.assertEqual(clearance(square,(5,5),(5,5)),-1);self.assertAlmostEqual(clearance(square,(13,5),(13,5)),3)
if __name__=='__main__':unittest.main()
