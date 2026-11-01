"""Private color-effect candidate qualification; explicit mismatches prevent credit."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_color_effect_initializer_candidates as source
from tools.tests import game_color_effect_initializer_oracle as oracle
from tools.tests import game_color_effect_initializer_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class ColorEffectInitializerCandidatesTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.check_inputs(ROOT,cls.output)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-private');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));assert (cls.raw,cls.bindings)==source.payload(cls.output/'selected-final.o')
  cls.guest=oracle.qualify(ROOT,cls.output);cls.callers=oracle.callers(ROOT,cls.output);cls.native=native.qualify(ROOT,cls.output,source.SELECTED)
 def test_payload_shape_known_mismatches_and_no_adoption(self):
  self.assertEqual(source.ENTRY,oracle.ENTRY);self.assertEqual((len(self.raw),len(self.bindings)),(208,7));self.assertEqual(struct.unpack_from('>I',self.raw)[0],0x27BDFFE8);self.assertFalse(source.ADOPTABLE);self.assertEqual(source.MATCHING_CREDIT,0);self.assertFalse(source.NEW_GUARDS)
  data,functions=source.link_owner(ROOT,self.output,self.output/'selected-final.o',source.OWNER);slot=data[:208];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+208]
  self.assertEqual(sum(a!=b for a,b in zip(struct.unpack('>52I',slot),struct.unpack('>52I',truth))),25)
  with self.assertRaises(ValueError):source.require_adoptable(ROOT,self.output)
  for at in(0,12,24,52,148,204):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
 def test_copied_owner_neighbors_pools_and_actual_make(self):
  for a,b in(('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),5)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game/generated_1B5370.c.o').read_bytes());self.assertEqual(len(json.loads((self.output/'Make-commands.json').read_text())),3)
  q=json.loads((self.output/'private-owner-v20.json').read_text());self.assertEqual(q['diagnostics'],dict(before=0,after=0));self.assertTrue(q['canonical_names_instruction_identical']);self.assertTrue(q['copy_owner_byte_array_declaration_retained'])
 def test_public_guest_semantics_original_callers_and_explicit_access_gap(self):
  q=self.guest;self.assertEqual((q['cases'],q['executions'],q['original_words_covered']),(11256,33768,52));self.assertTrue(q['counter_alias_wrap_cases']);self.assertTrue(q['original_40_word_bzero_connected']);self.assertFalse(q['full_machine_equality_claim']);self.assertFalse(q['access_order_equality_claim']);self.assertFalse(q['native_negative_index_claim'])
  self.assertEqual(q['sparse_full_pool_access_gap'],['returns-minus-one','extra-third-byte-read','extra-third-byte-read'])
  q=self.callers;self.assertEqual((q['cases'],q['executions']),(120,240));self.assertEqual(q['complete_parent_word_coverage'],{'0x15009bd0':43,'0x15009c7c':43,'0x15009f74':45});self.assertTrue(q['real_eight_slot_arguments_and_float_word']);self.assertTrue(q['original_40_word_bzero_and_11_word_memcpy_connected']);self.assertTrue(q['factory_outcomes_stubbed']);self.assertTrue(q['factory_null_does_not_undo_pool_append']);self.assertTrue(q['parent_void_return_not_claimed'])
 def test_native_full_pool_guard_bytes_and_eight_effective_controls(self):
  self.assertEqual(len(self.native),3)
  for q in self.native:
   self.assertEqual((q['cases'],q['executions'],len(q['controls'])),(1760,15840,8));self.assertTrue(q['UBSan']);self.assertTrue(q['all_eight_controls_effective']);self.assertTrue(q['all_288_pool_and_guard_bytes_checked']);self.assertTrue(q['valid_native_counts_only'])
 def test_private_image_prediction_review_provenance_and_frozen_production(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.output/'first-linked.elf').read_bytes();data,_=source.link_owner(ROOT,self.output,self.output/'selected-final.o',source.OWNER);source.check_private_image(before,actual,data[:208])
  self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map']);q=json.loads((self.output/'private-image-v24.json').read_text());self.assertEqual((q['functions'],q['other_bodies_fixed'],q['retail_differences']),(6052,6051,25));self.assertEqual(q['strict_exclusions'],0);self.assertTrue(q['production_ELF_unchanged']);self.assertEqual(q['matching_credit'],0)
  for at in(0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,208)+4):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_private_image(before,bytes(bad),data[:208])
  q=json.loads((self.output/'advisory-review-v25.json').read_text());self.assertEqual((q['calls_attempted'],q['calls_completed'],q['tool_use_events']),(1,1,0));self.assertEqual(q['tools'],[]);self.assertEqual(q['mcp_servers'],[]);self.assertTrue(q['no_claim_that_source_match_is_impossible']);self.assertTrue(q['volatile_diagnostics_unadopted'])
  self.assertEqual(source.sha((self.output/'claude-packet-v13.txt').read_bytes()),q['packet_file_SHA256']);self.assertEqual(source.sha((self.output/'claude-answer-v13.md').read_bytes()),q['reply_file_SHA256']);source.verify_prepared(self.output);source.check_inputs(ROOT,self.output)
