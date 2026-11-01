"""Actor position query: direct C, private scope, aliases and original helper/callers."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_actor_transform_position_match as source
from tools.tests import game_actor_transform_position_oracle as oracle
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class ActorTransformPositionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag,diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_all_53_words_direct_bindings_and_payload_negative_controls(self):
  self.assertEqual((len(self.raw),len(self.bindings)),(212,1));self.assertFalse(source.NEW_GUARDS)
  self.assertEqual((self.raw,self.bindings),source.payload(self.output/('original-'+source.FUNCTION+'.o')))
  for at in (0,28,100,116,160,208):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner(self.values[source.SOURCE].decode()))
 def test_owner_neighbors_pools_zero_warnings_and_actual_make(self):
  for a,b in (('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),15)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game_A9D90.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=0,after=0,removed=0));self.assertEqual(q['actual_Make_commands'],5)
 def test_guest_live_aliases_registers_matrix_selection_and_fault_prefixes(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['rebases'],q['alias_layouts']),(3584,14336,3,7));self.assertEqual(q['reachable_words'],52);self.assertEqual(q['unreachable_duplicate_constant_words'],1)
  self.assertTrue(q['four_programs_complete_state_trace_equal']);self.assertTrue(q['live_null_path_positions_and_y_home_reloaded']);self.assertTrue(q['z_home_captured_before_stores']);self.assertTrue(q['all_matrix_selectors']);self.assertTrue(q['saved_state_and_stack'])
  q=self.runtime['faults'];self.assertEqual((q['prefixes'],q['executions']),(79,316));self.assertTrue(q['complete_machine_state_and_access_order'])
 def test_complete_original_helpers_and_both_actual_caller_windows(self):
  q=self.runtime['helpers'];self.assertEqual((q['cases'],q['executions'],q['original_and_retained_helper_words']),(1536,6144,98));self.assertEqual([x['words'] for x in q['lower_helpers']],[46,40,49]);self.assertTrue(q['all_transform_and_translation_words_executed']);self.assertTrue(q['zero_offset_and_float_fixed_routes'])
  q=self.runtime['callers'];self.assertTrue(q['success']);self.assertEqual((q['cases'],q['executions'],q['original_windows'],q['reachable_caller_words']),(2048,8192,2,27));self.assertEqual(q['return_poisons'],4);self.assertTrue(q['void_return_ignored']);self.assertTrue(q['actual_argument_setup_branch_gates_and_output_consumers']);self.assertFalse(q['complete_parent_routines_emulated'])
  q=json.loads((self.output/'caller-census.json').read_text());self.assertEqual(q['aligned_ROM_JALs'],[0xAA030,0x152344]);self.assertFalse(q['aligned_ROM_Js']);self.assertFalse(q['aligned_ROM_pointer_literals'])
 def test_native_profiles_ubsan_whole_actor_canaries_and_seven_controls(self):
  self.assertEqual([q['profile'] for q in self.runtime['native']],['-O0','-O2','-O3'])
  for q in self.runtime['native']:
   self.assertEqual((q['cases'],q['executions'],q['portable_float_field_aliases']),(2048,16384,4));self.assertTrue(q['UBSan']);self.assertTrue(q['whole_actor_and_output_canaries']);self.assertTrue(q['all_seven_controls_effective']);self.assertTrue(q['private_and_incoming_home_aliases_excluded'])
 def test_literal_whole_image_symbol_extent_alignment_and_unchanged_map(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+224];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before),len(actual));self.assertEqual(truth[-12:],bytes(12))
  definitions={n:(at,f,st) for at,n,f,st in source.symbol_rows(actual)};at,f,st=definitions[source.FUNCTION];self.assertEqual(f[1:3],(source.ENTRY,212))
  offsets=[0x100,len(actual)-1,at+8,st,source.elf_slot_offset(actual,source.ENTRY,224)+4,source.elf_slot_offset(actual,source.ENTRY,224)+220]
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual((ROOT/'conker/build/conker.us.map').read_bytes(),self.values['conker/build/conker.us.map'])
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:
   q=source.audit(ROOT,self.output);self.assertEqual((q['functions'],q['other_bodies_fixed']),(6053,6052));self.assertTrue(q['all_addresses_fixed'])
