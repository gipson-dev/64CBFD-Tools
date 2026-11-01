"""Category mode direct match, byte aliases, callers and whole-image qualification."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_category_color_mode_match as source
from tools.tests import game_category_color_mode_oracle as oracle
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class CategoryColorModeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  cls.object,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected')
  if diag:raise AssertionError(diag)
  cls.raw,cls.bindings=source.checked_payload(*source.payload(cls.object));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_complete_direct_body_and_original_bindings(self):
  self.assertEqual(source.payload(self.object),source.payload(self.output/'original-func_151645C4.o'));self.assertEqual((len(self.raw),len(self.bindings)),(432,27))
  bad=bytearray(self.raw);bad[0]^=1
  with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
 def test_owner_actual_make_and_unchanged_diagnostics(self):
  source.verify_prepared(self.output);self.assertEqual(source.same_functions(self.output/'before-owner.o',self.output/'after-owner.o',(source.FUNCTION,)),77)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game_18D770.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=45,after=45,removed=0))
 def test_all_mode_bytes_live_aliases_and_rebases(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['body_words'],q['alignment_words']),(4502,18008,108,3));self.assertTrue(q['all_body_words_reached']);self.assertTrue(q['all_256_low_bytes']);self.assertTrue(q['all_machine_states_and_traces_equal'])
  self.assertEqual(len(self.runtime['guest_controls']),2);self.assertTrue(all(v['public_memory_control_effective']for v in self.runtime['guest_controls']))
 def test_all_three_original_caller_argument_forms(self):
  q=self.runtime['callers'];self.assertEqual((q['windows'],q['cases'],q['executions']),(3,588,2352));self.assertFalse(q['full_caller_reachability_claimed']);self.assertTrue(q['first_caller_overwrites_return_with_one'])
 def test_native_profiles_and_six_effective_controls(self):
  for q in self.runtime['native']:
   self.assertEqual(q['cases'],5720);self.assertTrue(q['UBSan']);self.assertEqual(len(q['negative_controls']),6);self.assertTrue(q['all_controls_effective'])
 def test_literal_image_metadata_pair_and_current_inputs(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth)
  bad=bytearray(actual);bad[0x100]^=1
  with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  bad=bytearray(actual);bad[source.METADATA_PAIR[0]+5]^=1
  with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:source.audit(ROOT,self.output)
