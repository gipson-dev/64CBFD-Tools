"""Direct record effect C, live signed fields, seeded payload and overflow closure."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_record_effect_spawn_match as source
from tools.tests import game_record_effect_spawn_oracle as oracle
from tools.tests import game_record_effect_spawn_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class RecordEffectSpawnTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));assert (cls.raw,cls.bindings)==source.payload(cls.output/'selected-final.o')
  cls.guest=oracle.qualify(ROOT,cls.output);cls.helpers,cls.census=oracle.helpers(ROOT,cls.output);cls.native=native.qualify(ROOT,cls.output)
 def test_direct_all_44_words_and_relocation_controls(self):
  self.assertEqual((len(self.raw),len(self.bindings)),(176,5));self.assertFalse(source.NEW_GUARDS)
  self.assertEqual((self.raw,self.bindings),source.payload(self.output/'original-func_15014094.o'))
  for at in (0,24,32,68,128,152,172):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner(self.values[source.SOURCE].decode()))
 def test_owner_pools_and_actual_make(self):
  for a,b in (('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),31)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game_40490.c.o').read_bytes())
  self.assertEqual(len(json.loads((self.output/'Make-commands.json').read_text())),5)
  self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
 def test_guest_payload_signed_fields_fault_prefixes_and_dispatcher(self):
  q=self.guest;self.assertEqual((q['root_cases'],q['root_executions'],q['retail_words_covered']),(1728,3456,44));self.assertTrue(q['original_private_complete_memory_registers_and_trace_equal']);self.assertTrue(q['seeded_untouched_payload_bytes_preserved'])
  self.assertEqual((q['access_prefix_cuts'],q['access_prefix_executions']),(18,36));self.assertFalse(q['full_fault_register_equivalence_claim'])
  self.assertEqual((q['callback_dispatcher_words'],q['callback_executions'],q['callback_return_poison_values']),(16,576,4));self.assertTrue(q['dispatcher_ignores_callback_return'])
  self.assertEqual(self.census['aligned_ROM_pointer_literals'],[0x2279D0]);self.assertFalse(self.census['aligned_ROM_JALs']);self.assertFalse(self.census['aligned_ROM_Js'])
  q=self.helpers;self.assertEqual((q['cases'],q['executions'],q['original_factory_words'],q['original_memcpy_words']),(128,256,49,11));self.assertTrue(q['all_target_reachable_helper_words_executed']);self.assertEqual(q['reachable_factory_words'],47)
 def test_native_defined_payload_canaries_and_seven_controls(self):
  self.assertEqual([q['profile']for q in self.native],['-O0','-O2','-O3'])
  for q in self.native:
   self.assertEqual((q['cases'],q['executions']),(192,1536));self.assertTrue(q['UBSan']);self.assertTrue(q['all_seven_controls_effective']);self.assertTrue(q['whole_record_and_destination_canaries']);self.assertTrue(q['untouched_stack_payload_bytes_not_asserted']);self.assertTrue(q['return_value_unused'])
 def test_literal_entire_image_and_overflow_removal(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+176];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth)
  q=source.predict(before,truth)[1];self.assertEqual((q['removed_body_bytes'],q['ELF_bytes_removed'],q['strict_exclusions']),(184,248,0));self.assertEqual(len(q['moved_private_definitions']),7);self.assertEqual(len(q['retargeted_trampolines']),4)
  for at in (0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,176)+4):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
