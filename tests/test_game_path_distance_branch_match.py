"""Direct distance branch, original helper/callers and complete overflow closure."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_path_distance_branch_match as source
from tools.tests import game_path_distance_branch_oracle as oracle
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class PathDistanceBranchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag,diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_complete_direct_payload_bindings_and_negative_controls(self):
  self.assertEqual(len(self.raw),216);self.assertEqual(len(self.bindings),13);self.assertFalse(source.NEW_GUARDS)
  self.assertEqual((self.raw,self.bindings),source.payload(self.output/'original-func_150781F4.o'))
  for at in(0,32,136,152,192,212):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner(self.values[source.SOURCE].decode()))
 def test_owner_neighbors_pools_warnings_and_actual_make(self):
  self.assertEqual(source.same_functions(self.output/'before-owner.o',self.output/'after-owner.o',(source.FUNCTION,)),210)
  self.assertEqual(source.same_functions(self.output/'before-padded.o',self.output/'qualified-padded.o',(source.FUNCTION,)),210)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game_A28B0.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=14,after=14,removed=0));self.assertEqual(q['actual_Make_commands'],5)
 def test_guest_float32_strict_boundaries_aliases_and_access_prefixes(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['rebases'],q['alias_layouts']),(12292,49168,3,4));self.assertTrue(q['all_54_words_executed']);self.assertTrue(q['all_256_input_bytes']);self.assertEqual(q['nonfinite_guest_cases'],4);self.assertTrue(q['four_programs_full_state_equal'])
  q=self.runtime['faults'];self.assertEqual((q['prefixes'],q['executions']),(41,164));self.assertTrue(q['complete_states_equal'])
 def test_complete_original_helper_both_callers_and_retargeted_trampoline(self):
  q=self.runtime['connected'];self.assertEqual((q['cases'],q['executions'],q['original_helper_words']),(1024,4096,38));self.assertTrue(q['all_helper_words_executed']);self.assertTrue(q['fast_advance_and_100_scan_and_matching_sentinel']);self.assertTrue(q['matching_sentinel_net_cursor_minus_4']);self.assertTrue(q['no_nested_providers'])
  q=self.runtime['callers'];self.assertEqual((q['cases'],q['executions'],q['reachable_words']),(120,480,28));self.assertEqual(q['return_poisons'],4);self.assertTrue(q['packet_advance_5_or_1']);self.assertTrue(q['void_return_ignored']);self.assertFalse(q['full_dispatcher_emulation'])
  q=self.runtime['direct_wrapper'];self.assertEqual((q['cases'],q['executions'],q['complete_original_wrapper_words']),(64,256,12));self.assertTrue(q['all_wrapper_words_executed']);self.assertTrue(q['node_copy_and_return_poisons_verified'])
  q=json.loads((self.output/'caller-census.json').read_text());self.assertEqual(q['aligned_ROM_JALs'],[0xA6DC0]);self.assertEqual(q['aligned_ROM_pointer_literals'],[0x22B474]);self.assertEqual(q['row'],161);self.assertFalse(q['aligned_ROM_Js'])
  q=json.loads((self.output/'retargeted-trampoline.json').read_text());self.assertTrue(q['success']);self.assertEqual((q['cases'],q['executions']),(8,16));self.assertTrue(q['all_registers_and_memory_unchanged'])
 def test_native_profiles_ubsan_canaries_and_eight_effective_controls(self):
  self.assertEqual([q['profile']for q in self.runtime['native']],['-O0','-O2','-O3'])
  for q in self.runtime['native']:
   self.assertEqual(q['cases'],1024);self.assertTrue(q['UBSan']);self.assertTrue(q['full_actor_and_path_canaries']);self.assertTrue(q['all_eight_controls_effective']);self.assertEqual(q['sqrt_instruction'],'SSE sqrtss');self.assertTrue(q['pointer_aliases_guest_only'])
 def test_literal_entire_elf_map_and_complete_executable_closure(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+216];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before)-len(actual),284)
  q=source.closure_audit(self.output/'before-conker_build_conker.us.elf',self.output/'first-linked.elf');self.assertEqual((q['functions_before'],q['functions'],q['canonical_function_addresses_fixed'],q['other_bodies_fixed']),(6055,6054,6045,6052));self.assertEqual(len(q['private_bodies_moved']),3);self.assertEqual(q['retargeted_trampolines'],['func_150A7D00'])
  rows={n:(at,f,st)for at,n,f,st in source.symbol_rows(actual)};offsets=[0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,216)+4]
  for n in(q['private_bodies_moved']+q['retargeted_trampolines']+['__romPos']):
   at,f,st=rows[n];offsets.extend((at+4,st))
   if n!='__romPos':offsets.append(source.elf_slot_offset(actual,f[1],4))
  for at in offsets:
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  old=self.values['conker/build/conker.us.map'];new=(self.output/'predicted-production.map').read_bytes();source.check_map(old,new)
  bad=bytearray(new);bad[0]^=1
  with self.assertRaises(ValueError):source.check_map(old,bytes(bad))
  q=json.loads((self.output/'overflow-control-flow.json').read_text());self.assertTrue(q['success']);self.assertEqual(len(q['moved_bodies']),3);self.assertTrue(q['all_relative_targets_local']);self.assertTrue(q['absolute_control_targets_unchanged'])
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:source.audit(ROOT,self.output)
