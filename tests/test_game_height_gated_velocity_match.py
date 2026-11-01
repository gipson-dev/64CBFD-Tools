"""Height-gated velocity: signed jitter, original helper, float order and dispatch ABI."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_height_gated_velocity_match as source
from tools.tests import game_height_gated_velocity_oracle as oracle
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class HeightGatedVelocityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  cls.object,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected')
  if diag:raise AssertionError(diag)
  cls.raw,cls.bindings=source.checked_payload(*source.payload(cls.object));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_complete_direct_body_and_relocation_pin(self):
  self.assertEqual(len(self.raw),288)
  self.assertEqual(len(source.payload(self.output/'original-func_1506BCC8.o')[0]),288)
  bad=bytearray(self.raw);bad[0]^=1
  with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
 def test_owner_actual_make_and_unchanged_diagnostics(self):
  source.verify_prepared(self.output);self.assertEqual(source.same_functions(self.output/'before-owner.o',self.output/'after-owner.o',(source.FUNCTION,)),327)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game_981E0.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=36,after=36,removed=0))
 def test_signed_jitter_float_order_aliases_and_original_rng(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['body_words'],q['frame']),(3963,15852,72,24));self.assertTrue(q['all_71_reachable_words_executed']);self.assertTrue(q['all_machine_states_and_traces_equal']);self.assertEqual(q['rebases'],3);self.assertEqual((q['original_rng_words'],q['connected_cases'],q['connected_executions']),(11,144,576));self.assertTrue(q['all_original_rng_words_executed']);self.assertFalse(q['hardware_FCSR_claimed']);self.assertTrue(self.runtime['guest_control']['compiled_cached_actor_control_effective'])
 def test_original_indirect_dispatch_and_return_poisons(self):
  q=self.runtime['callers'];self.assertEqual((q['callback_slot'],q['cases'],q['executions']),(2,96,1536));self.assertEqual(q['return_poisons'],4);self.assertTrue(q['return_ignored']);self.assertFalse(q['full_dispatcher_reachability_claimed'])
 def test_native_profiles_and_seven_effective_controls(self):
  for q in self.runtime['native']:
   self.assertEqual(q['cases'],1320);self.assertTrue(q['UBSan']);self.assertEqual(len(q['controls']),7);self.assertTrue(q['all_controls_effective']);self.assertTrue(q['wrapping_addition_defined'])
 def test_literal_whole_image_and_current_inputs(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth)
  bad=bytearray(actual);bad[0x100]^=1
  with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  bad=bytearray(actual);bad[source.elf_slot_offset(actual,source.ENTRY,source.SIZE)+4]^=1
  with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:source.audit(ROOT,self.output)
