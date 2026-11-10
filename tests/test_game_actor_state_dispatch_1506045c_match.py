"""Full dispatcher source, ABI, native/guest, guard and linked-image gates."""
import struct,unittest
from tools.experiments import game_actor_state_dispatch_1506045c_match as source
from tools.tests import game_actor_state_dispatch_1506045c_oracle as guest
from tools.tests import game_actor_state_dispatch_1506045c_native as native
from tools.tests import game_actor_state_dispatch_1506045c_controls as controls
from tools.tests import game_actor_state_dispatch_1506045c_boundaries as boundaries
from tools.tests import game_actor_state_dispatch_1506045c_callers as callers
ROOT=source.ROOT
class StateDispatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_actual_Make_three_bodies_and_complete_image(self):
  self.assertEqual(self.report['image']['changed_bytes'],688);self.assertEqual(self.report['image']['strict_exclusions'],0);self.assertEqual(self.report['actual_Make_commands'],10);self.assertEqual(self.report['non_target_Game_neighbors'],88);self.assertEqual(self.report['unchanged_helper_neighbors'],17);self.assertEqual(self.report['guards'],1)
 def test_02_all_words_guest_recursion_and_complete_machine_state(self):
  r=guest.main();self.assertEqual(r['cases'],3384);self.assertEqual(set(r['coverage'].values()),{199});self.assertEqual(r['full_state_and_access_trace_pairs'],3384)
 def test_03_native_SDK32_O0_O2_O3_UBSan(self):
  r=native.main();self.assertEqual(set(r['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==2926 and v['exact_output_bytes']==6505350 and v['UBSan']for v in r['profiles'].values()))
 def test_04_seventeen_effective_compiled_controls(self):
  r=controls.main();self.assertEqual(r['controls'],17);self.assertTrue(all(v['normal_completion']and v['execution_errors']==0 for v in r['effective_compiled_controls'].values()))
 def test_05_register_proof_padders_rebases_and_fault_cuts(self):
  r=boundaries.main();self.assertTrue(r['proof']['copy_dominates_branch']);self.assertEqual(r['padders']['word_and_binding_corruptions'],213);self.assertEqual(r['padders']['stale_guard_rejections'],2);self.assertEqual(r['rebases']['executions'],60);self.assertEqual(r['faults']['exact_instruction_access_cut_pairs'],297)
 def test_06_all_original_caller_windows(self):
  r=callers.main();self.assertEqual(r['executions'],1200);self.assertEqual(r['full_state_and_access_trace_pairs'],600);self.assertEqual(sum(r['window_coverage'].values()),22)
 def test_07_eight_complete_image_corruptions(self):
  before=(source.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=(source.out/'qualified-image.elf').read_bytes();raw,refs=source.payload(source.out/'selected.o');normal,nrefs=source.normalize(raw,refs)
  payloads={'func_1506045C':struct.pack('>199I',*source.g_bound(normal,nrefs))};helper=struct.pack('>7I',0xAFA40000,0xAFA50004,0xAFA60008,0xAFA7000C,0x00001025,0x03E00008,0)
  payloads.update({n:helper for n in('func_150642AC','func_15065A5C')});symbol=next(r for r in source.symbol_rows(before)if r[1]=='func_1506045C')
  for at in [24,source.elf_slot_offset(before,0x1506045C,796),source.elf_slot_offset(before,0x150642AC,28),source.elf_slot_offset(before,0x15065A5C,28),source.elf_slot_offset(before,0x15060778,696),source.elf_slot_offset(before,self.report['protected_data']['address'],1),symbol[0]+8,symbol[3]]:
   wrong=bytearray(actual);wrong[at]^=1
   with self.assertRaises((ValueError,AssertionError)):source.strict_image(before,bytes(wrong),payloads)
 def test_08_closed_live_inputs_addresses_and_data(self):
  source.live_inputs(self.report['source_installed']);self.assertTrue(self.report['all_addresses_fixed']);self.assertEqual(self.report['functions'],6050);self.assertTrue(self.report['protected_data']['exact'])
if __name__=='__main__':unittest.main()
