"""Private renderer qualification; finite agreement grants no match credit."""
import json,struct,unittest
from tools.experiments import game_strip_draw_151ad92c_private_recovery as source

class StripDrawPrivateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  source.check_inputs()
 @classmethod
 def tearDownClass(cls):
  source.check_inputs()
 def test_01_complete_owner_and_original_frame(self):
  report=source.compile_and_check()
  self.assertEqual((report['raw_words'],report['retail_words'],report['frame']),(458,464,304))
  self.assertEqual(report['neighbors'],32)
 def test_02_original_and_raw_public_matrix_and_open_frontier(self):
  from tools.tests import game_strip_draw_151ad92c_private_oracle as oracle
  oracle.main()
 def test_03_complete_original_caller_and_selector(self):
  from tools.tests import game_strip_draw_151ad92c_private_caller as caller
  caller.main()
 def test_04_native_sdk_c_and_semantic_controls(self):
  from tools.tests import game_strip_draw_151ad92c_private_native as native
  native.main()
 def test_05_instruction_controls_and_xor_zero_register(self):
  from tools.tests import game_strip_draw_151ad92c_private_oracle as g
  truth=list(struct.unpack('>464I',(source.OUT/'retail.bin').read_bytes()))
  controls=[]
  cases=[('zero-length-fallback',0x3C0142C8,0x3C013F80,g.Case(count=3,pattern=2)),
         ('texture-shift',0x24190005,0x24190004,g.Case(count=3)),
         ('helper-last-argument',0x240E003E,0x240E003D,g.Case(count=0)),
         ('incoming-viewport-width',0xAFA60138,0xA7A60138,g.Case(count=0,viewport=0xABCDEF01)),
         ('signed-texture-height',0x946F0008,0x846F0008,g.Case(count=3,height=65535))]
  for name,before,after,case in cases:
   self.assertEqual(truth.count(before),1,name);bad=truth[:];bad[bad.index(before)]=after
   with self.assertRaises(AssertionError,msg=name):g.verify(bad,case)
   controls.append(name)
  for a,b in((0,0),(0,0xFFFFFFFF),(0xA5A5A5A5,0x5A5A5A5A),(0x80000000,1)):
   machine=g.Oracle([0],g.fixture(g.Case()),g.Case());machine.r[4]=a;machine.r[5]=b
   machine.execute(0x00851826);self.assertEqual(machine.r[3],a^b)
   machine.execute(0x00850026);self.assertEqual(machine.r[0],0)
  report=dict(retail_controls_rejected=controls,xor_cases=4,zero_register_preserved=True,source_installed=False,c_match_credit=0)
  (source.OUT/'controls-report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':unittest.main()
