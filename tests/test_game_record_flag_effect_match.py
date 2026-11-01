"""Direct record flags, all nine helper arguments and original dispatch/reloads."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_record_flag_effect_match as source
from tools.tests import game_record_flag_effect_oracle as oracle
from tools.tests import game_record_flag_effect_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class RecordFlagEffectTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));assert (cls.raw,cls.bindings)==source.payload(cls.output/'selected-final.o')
  cls.guest,cls.census=oracle.qualify(ROOT,cls.output);cls.dispatch=oracle.dispatch(ROOT,cls.output);cls.helper=oracle.helper(ROOT,cls.output);cls.native=native.qualify(ROOT,cls.output)
 def test_all_55_direct_words_and_binding_controls(self):
  self.assertEqual((len(self.raw),len(self.bindings)),(220,3));self.assertFalse(source.NEW_GUARDS)
  self.assertEqual((self.raw,self.bindings),source.payload(self.output/'original-func_15014144.o'))
  for at in(0,20,24,40,100,132,192,216):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner(self.values[source.SOURCE].decode()))
 def test_owner_pools_diagnostics_and_actual_make(self):
  for a,b in(('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),31)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game_40490.c.o').read_bytes());self.assertEqual(len(json.loads((self.output/'Make-commands.json').read_text())),5)
  q=json.loads((self.output/'private-owner-qualification.json').read_text());self.assertEqual((q['before_diagnostics'],q['after_diagnostics']),('',''))
  self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
 def test_guest_original_dispatcher_and_helper_boundaries(self):
  q=self.guest;self.assertEqual((q['cases'],q['executions'],q['rebases'],q['retail_words_covered']),(12288,24576,3,55));self.assertTrue(q['original_private_complete_machine_memory_register_trace_equal']);self.assertTrue(q['complete_nine_argument_boundary']);self.assertTrue(q['global_float_bits_preserved']);self.assertTrue(q['return_one_after_caller_saved_clobber']);self.assertEqual((q['access_prefix_cuts'],q['access_prefix_executions']),(10,20));self.assertFalse(q['full_fault_register_equivalence_claim'])
  q=self.dispatch;self.assertEqual((q['cases'],q['executions'],q['original_dispatcher_words']),(2304,4608,45));self.assertTrue(q['all_original_dispatcher_words_covered']);self.assertTrue(q['live_count_and_base_reloads']);self.assertTrue(q['callback_result_ignored']);self.assertEqual(q['return_poisons'],4);self.assertEqual(q['relocated_second_record_reads'],512)
  q=self.helper;self.assertEqual((q['cases'],q['executions'],q['original_helper_words'],q['helper_words_executed']),(1024,2048,169,143));self.assertEqual(len(q['unexecuted_helper_PCs']),26);self.assertTrue(q['all_copy_words_executed']);self.assertTrue(q['lower_factory_payload_checked']);self.assertTrue(q['second_payload_and_signed_live_coordinates_checked']);self.assertTrue(q['template_copy_and_output_flags_checked']);self.assertTrue(q['lower_factory_and_secondary_calls_stubbed'])
  self.assertEqual(self.census['aligned_ROM_pointer_literals'],[0x227938]);self.assertFalse(self.census['aligned_ROM_JALs']);self.assertFalse(self.census['aligned_ROM_Js'])
 def test_native_profiles_canaries_and_seven_controls(self):
  self.assertEqual([q['profile']for q in self.native],['-O0','-O2','-O3'])
  for q in self.native:
   self.assertEqual((q['cases'],q['executions']),(2560,20480));self.assertTrue(q['UBSan']);self.assertTrue(q['all_seven_controls_effective']);self.assertTrue(q['whole_record_canaries']);self.assertTrue(q['all_nine_arguments_checked']);self.assertTrue(q['return_one'])
 def test_literal_entire_image_extent_and_unchanged_map(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+220];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before),len(actual))
  self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
  q=json.loads((self.output/'private-image-qualification.json').read_text());self.assertEqual((q['functions'],q['other_bodies_fixed']),(6052,6051));self.assertTrue(q['all_function_addresses_fixed'])
  for at in(0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,220)+4):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
