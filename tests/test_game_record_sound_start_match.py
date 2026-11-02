"""Private semantic qualification is not an exact-match or installation claim."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_record_sound_start_match as source
from tools.tests import game_record_sound_start_oracle as oracle
from tools.tests import game_record_sound_start_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class RecordSoundStartTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.check_inputs(ROOT,cls.output)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));cls.guest=oracle.qualify(ROOT,cls.output);cls.helpers=oracle.helpers(ROOT,cls.output);cls.callers=oracle.callers(ROOT,cls.output);cls.native=native.qualify(ROOT,cls.output,source.SELECTED,source.HEADERS,oracle)
 def test_natural_candidate_and_unclosed_epilogue_are_not_matching_credit(self):
  self.assertEqual(len(self.raw),216);self.assertEqual(self.bindings,{172:[('R_MIPS_26','func_1000FA64')]})
  original,refs=source.payload(self.output/'original-func_150A23E4.o');self.assertEqual((len(original),refs),(220,self.bindings))
  a=struct.unpack('>54I',self.raw);b=struct.unpack('>55I',original);self.assertEqual(sum(x!=y for x,y in zip(a,b)),9);self.assertEqual(a[8:46],b[8:46])
  for at in(0,24,32,172,184,212):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.output/'proposed-owner.c').read_text())
  self.assertNotIn(b',func_150A23E4,',self.values['conker/retail_word_patches.us.csv'])
  for name in('context-screen-v9.json','assembler-profile-screen-v15.json'):
   for q in json.loads((self.output/name).read_text()):self.assertEqual((q['words'],q['raw_SHA256']),(54,source.RAW_SHA))
 def test_guest_full_width_state_all_bytes_mutations_and_access_prefixes(self):
  q=self.guest;self.assertTrue(q['success']);self.assertEqual((q['cases'],q['executions'],q['covered_original_words'],q['covered_candidate_words'],q['access_prefix_pairs']),(7740,15480,54,53,48));self.assertTrue(q['all_selector_and_flag_bytes']);self.assertTrue(q['provider_record_and_incoming_home_mutations']);self.assertFalse(q['PC_and_delay_identity_claim'])
 def test_original_enqueue_and_two_original_caller_windows(self):
  q=self.helpers;self.assertEqual((q['cases'],q['executions'],q['original_helper_words'],q['helper_words_covered']),(756,1512,109,88));self.assertTrue(q['queue_full_and_sort_count_mutation']);self.assertTrue(q['retained_helper_equals_original']);self.assertTrue(q['lower_CENTS_and_SORT_mocked'])
  q=self.callers;self.assertEqual(q['original_callers'],2);self.assertTrue(q['result_not_consumed']);self.assertTrue(q['parent_functions_still_unrecovered']);self.assertFalse(q['full_parent_claim']);self.assertEqual([(v['words'],v['executions'])for v in q['windows']],[(6,120),(4,120)])
 def test_native_typed_enqueue_fences_and_effective_controls(self):
  q=self.native;self.assertEqual((q['cases_per_profile'],q['effective_controls_each']),(2580,7));self.assertEqual(q['profiles'],['O0','O2','O3']);self.assertTrue(q['typed_12_argument_helper']);self.assertTrue(q['callee_halfword_narrowing']);self.assertTrue(q['helper_observes_state_before_final_publication']);self.assertTrue(q['record_and_surrounding_fences']);self.assertTrue(q['UBSan'])
 def test_private_generated_owner_make_complete_image_and_unchanged_production(self):
  for a,b in(('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):
   self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),27);self.assertEqual(source.normalized_pools(self.output/a),source.normalized_pools(self.output/b))
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game/generated_CDE80.c.o').read_bytes());self.assertEqual(len(json.loads((self.output/'Make-commands.json').read_text())),5)
  q=source.audit(ROOT,self.output);self.assertEqual((q['matching_credit'],q['strict_exclusions'],q['functions'],q['other_bodies_fixed']),(0,0,6052,6051));self.assertTrue(q['private_only']);self.assertFalse(q['installed']);self.assertTrue(q['all_function_addresses_fixed'])
  self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map']);actual=(self.output/'first-linked.elf').read_bytes();before=self.values['conker/build/conker.us.elf']
  for at in(0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,220)+24):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),self.raw,self.bindings)
  with self.assertRaises(ValueError):source.predict(actual,self.raw,self.bindings)
  self.assertEqual(source.sha((ROOT/'conker/build/conker.us.elf').read_bytes()),source.BASELINE);source.verify_prepared(self.output);source.check_inputs(ROOT,self.output)
