"""Direct actor matrix-position matching and complete installed-image gates."""
from pathlib import Path
import hashlib,json,os,unittest
from tools.experiments import game_actor_matrix_position_match as source
from tools.tests import game_actor_matrix_position_oracle as oracle
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class ActorMatrixPositionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  source.check_inputs(ROOT,cls.output,cls.installed)
  cls.object,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected')
  if diag:raise AssertionError(diag)
  cls.raw,cls.bindings=source.checked_payload(*source.payload(cls.object))
  cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_direct_52_words_and_original_bindings(self):
  self.assertEqual(source.payload(self.object),source.payload(self.output/'original-func_151644F4.o'))
  self.assertEqual((len(self.raw),len(self.bindings)),(208,2))
  bad=bytearray(self.raw);bad[0]^=1
  with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
 def test_actual_owner_make_padder_and_diagnostics(self):
  source.verify_prepared(self.output)
  self.assertEqual(source.same_functions(self.output/'before-owner.o',self.output/'after-owner.o',(source.FUNCTION,)),77)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game_18D770.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=48,after=45,removed=3))
 def test_guest_live_load_aliases_and_rebases(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['body_words']),(870,3480,52))
  self.assertTrue(q['all_body_words_reached']);self.assertTrue(q['full_public_memory_canaries_saved_state']);self.assertTrue(q['all_machine_states_and_traces_equal'])
 def test_original_parent_and_point_helper(self):
  q=self.runtime['guest'];self.assertEqual((q['parent_cases'],q['parent_executions'],q['original_parent_words'],q['original_point_helper_words']),(80,320,19,40));self.assertTrue(q['rotation_provider_opaque'])
 def test_native_profiles_and_effective_controls(self):
  for q in self.runtime['native']:
   self.assertEqual(q['cases'],48);self.assertTrue(q['UBSan']);self.assertEqual(len(q['negative_controls']),6);self.assertTrue(q['all_controls_effective'])
 def test_literal_image_and_current_inputs(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE]
  expected=source.predicted_image(before,truth);actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth)
  bad=bytearray(actual);bad[0x100]^=1
  with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:source.audit(ROOT,self.output)
