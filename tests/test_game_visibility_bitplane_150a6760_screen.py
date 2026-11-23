"""Private-only decoder gates; intentionally no installation or matching credit."""
import unittest
from tools.experiments import game_visibility_bitplane_150a6760_screen as packet
from tools.tests import game_visibility_bitplane_150a6760_guest as guest
from tools.tests import game_visibility_bitplane_150a6760_native as native
class VisibilityDecoderRecovery(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.rows=packet.inspect_source()
 def test_01_whole_owner_and_rejected_shapes(self):
  self.assertEqual({k:(v['raw_words'],v['frame'])for k,v in self.rows.items()},{'initial':(77,24),'loop':(71,24),'initialized':(70,0)})
  for row in self.rows.values():self.assertEqual(row['neighbors'],16);self.assertTrue(row['pools_equal']and row['diagnostics_equal']);self.assertFalse(row['source_installed']);self.assertEqual(row['matching_credit'],0)
 def test_02_original_and_private_guest_outputs(self):
  q=guest.main();self.assertEqual(q['cases_per_stream'],432);self.assertEqual(len(q['streams']),4);self.assertTrue(q['retail_access_trace_equal']);self.assertEqual(q['retail_unexecuted_words'],[62,63]);self.assertEqual(len(q['effective_controls']),3)
  self.assertEqual(q['candidate_access_trace_differences'],{'retail':0,'initial':432,'loop':432,'initialized':432})
 def test_03_SDK32_defined_fixtures_and_effective_controls(self):
  q=native.main();self.assertEqual(set(q['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v==dict(cases=432,SDK32=True,UBSan=True,strict_aliasing=True)for v in q['profiles'].values()));self.assertEqual(len(q['effective_output_comparison_controls']),3)
 def test_04_direct_call_and_interior_entry_boundary(self):
  q=packet.census();self.assertEqual(len(q['direct_edges']),2);self.assertTrue(q['interior_label_is_absolute_symbol']);packet.prepare()
 def test_05_local_NOR_and_variable_shift_instruction_controls(self):
  rows=[(4,0,0x80000001,0x80000001),(4,31,1,0x80000000),(4,32,1,1),(6,31,0x80000000,1),(6,32,0x80000001,0x80000001),(6,63,0x80000000,1),(7,31,0x80000000,0xFFFFFFFF),(7,32,0x80000001,0x80000001),(7,1,0x80000001,0xC0000000),(0x27,0x0F0F0F0F,0x00FF00FF,0xF000F000)]
  for fn,a,b,want in rows:
   m=guest.DecoderOracle([0x03E00008,0],{},guest.Case(),entry=guest.ENTRY,s={},arguments=(0,));m.r[4]=a;m.r[5]=b
   before=m.r[:];m.execute((4<<21)|(5<<16)|(6<<11)|fn);self.assertEqual(m.r[6],want);self.assertEqual([v for i,v in enumerate(m.r)if i!=6],[v for i,v in enumerate(before)if i!=6])
if __name__=='__main__':unittest.main(verbosity=2)
