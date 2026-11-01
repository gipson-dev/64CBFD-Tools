"""Spherical offsets: closed spill pair, original callers and complete image."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_spherical_vector_match as source
from tools.tests import game_spherical_vector_oracle as oracle
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class SphericalVectorTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag,diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_complete_payload_bindings_and_closed_spill_controls(self):
  self.assertEqual((len(self.raw),len(self.bindings)),(204,8));self.assertEqual(len(source.NEW_GUARDS),2)
  self.assertEqual((source.normalized_payload(self.raw,self.bindings),self.bindings),source.payload(self.output/('original-'+source.FUNCTION+'.o')))
  self.assertEqual(source.derive_guards(self.raw,self.bindings),[(0x8C,0xE7AC0024,0xE7AC0020),(0x90,0xC7AC0024,0xC7AC0020)])
  for at in (0,36,80,140,144,200):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner(self.values[source.SOURCE].decode()))
  with self.assertRaises(ValueError):source.proposed_guards(source.proposed_guards(self.values['conker/retail_word_patches.us.csv']))
  q=json.loads((self.output/'spill-runtime-controls.json').read_text());self.assertTrue(q['success']);self.assertEqual(len(q['effective_controls']),2)
 def test_owner_neighbors_pools_diagnostics_actual_make_and_guard_append(self):
  for a,b in (('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),88)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game_83300.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  old=self.values['conker/retail_word_patches.us.csv'];new=source.proposed_guards(old);self.assertTrue(new.startswith(old));self.assertEqual(len(new.splitlines())-len(old.splitlines()),2)
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=8,after=8,removed=0));self.assertEqual(q['actual_Make_commands'],5)
 def test_guest_aliases_saved_state_access_prefixes_and_original_trig(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['rebases'],q['alias_layouts']),(3456,13824,3,9));self.assertEqual(q['reachable_root_words'],48);self.assertEqual(q['unreachable_unsigned_correction_words'],3)
  self.assertTrue(q['all_three_normalized_programs_full_state_trace_equal']);self.assertTrue(q['raw_C_public_state_equal']);self.assertTrue(q['raw_private_difference_only_two_four_byte_slots'])
  q=self.runtime['faults'];self.assertEqual((q['prefixes'],q['executions']),(84,252));self.assertTrue(q['normalized_programs_complete_machine_state_and_trace_equal'])
  q=self.runtime['connected'];self.assertEqual((q['cases'],q['executions'],q['original_trig_span_words']),(2304,9216,76));self.assertEqual(q['original_trig_words_executed'],73);self.assertTrue(q['retail_code_and_12_coefficient_words_pinned'])
 def test_all_original_call_boundaries_and_complete_wrapper(self):
  q=self.runtime['callers'];self.assertTrue(q['success']);self.assertEqual((q['cases'],q['executions'],q['original_JAL_delay_pairs']),(3712,14848,29));self.assertTrue(q['six_argument_boundary_qualified'] if 'six_argument_boundary_qualified' in q else all(row['six_argument_boundary_qualified'] for row in q['rows']))
  self.assertTrue(q['all_output_pointers_outside_callee_private_frame']);self.assertFalse(q['complete_parent_routines_emulated'])
  q=self.runtime['wrapper'];self.assertEqual((q['cases'],q['executions'],q['original_wrapper_words']),(512,2048,32));self.assertTrue(q['all_original_wrapper_words_executed']);self.assertTrue(q['six_argument_X_Z_Y_ABI'])
  q=json.loads((self.output/'caller-census.json').read_text());self.assertEqual(len(q['aligned_ROM_JALs']),29);self.assertFalse(q['aligned_ROM_Js']);self.assertFalse(q['aligned_ROM_pointer_literals'])
  q=json.loads((self.output/'retargeted-trampoline.json').read_text());self.assertTrue(q['success']);self.assertEqual((q['cases'],q['executions'],len(q['entries'])),(16,32,2));self.assertTrue(q['all_registers_and_memory_unchanged'])
 def test_native_profiles_ubsan_canaries_and_nine_effective_controls(self):
  self.assertEqual([q['profile'] for q in self.runtime['native']],['-O0','-O2','-O3'])
  for q in self.runtime['native']:
   self.assertEqual((q['cases'],q['executions'],q['alias_layouts']),(1280,12800,5));self.assertTrue(q['UBSan']);self.assertTrue(q['canaries']);self.assertTrue(q['all_nine_controls_effective']);self.assertTrue(q['guest_formal_homes_excluded'])
 def test_literal_entire_elf_map_and_complete_executable_closure(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+204];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before)-len(actual),284)
  q=source.closure_audit(self.output/'before-conker_build_conker.us.elf',self.output/'first-linked.elf');self.assertEqual((q['functions_before'],q['functions'],q['canonical_function_addresses_fixed'],q['other_bodies_fixed']),(6054,6053,6045,6050));self.assertEqual(len(q['private_bodies_moved']),5);self.assertEqual(q['retargeted_trampolines'],['func_150768DC','func_150A7D00'])
  rows={n:(at,f,st) for at,n,f,st in source.symbol_rows(actual)};offsets=[0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,204)+4]
  for n in q['private_bodies_moved']+q['retargeted_trampolines']+['__romPos']:
   at,f,st=rows[n];offsets.extend((at+4,st))
   if n!='__romPos':offsets.append(source.elf_slot_offset(actual,f[1],4))
  for at in offsets:
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.check_map(self.values['conker/build/conker.us.map'],(self.output/'predicted-production.map').read_bytes())
  with self.assertRaises(ValueError):source.check_map(self.values['conker/build/conker.us.map'],b'broken map')
  q=json.loads((self.output/'overflow-control-flow.json').read_text());self.assertTrue(q['success']);self.assertEqual(len(q['moved_bodies']),5);self.assertTrue(q['all_relative_targets_local'])
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:source.audit(ROOT,self.output)
