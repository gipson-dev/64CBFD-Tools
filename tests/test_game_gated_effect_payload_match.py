"""Gated effect payload: direct C, sparse packet, original callers and whole-image closure."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_gated_effect_payload_match as source
from tools.tests import game_gated_effect_payload_oracle as oracle
from tools.tests import game_gated_effect_payload_integration as integration
from tools.tests import game_gated_effect_payload_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class GatedEffectPayloadTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.installed=os.environ.get('CBFD_GATED_EFFECT_INSTALLED')=='1';cls.values=source.check_inputs(ROOT,cls.output,cls.installed)
 def test_01_direct_payload_bindings_and_independent_links(self):
  function,owner,entry,rom=source.SPECS[0]
  obj,diag=source.compile_owner(ROOT,self.output,source.HEADERS+source.SELECTED,'public-fresh-'+function)
  self.assertFalse(diag);raw,refs=source.checked_payload(*source.payload(obj,function));original,bindings=source.payload(self.output/('original-'+function+'.o'),function)
  self.assertEqual((raw,refs),(original,bindings));self.assertEqual(source.PATCHES,());self.assertEqual(struct.unpack_from('>I',raw)[0],0x27BDFFA8)
  self.assertEqual(source.recovered_owner(self.values['conker/src/game/'+owner+'.c'].decode(),0),(self.output/('proposed-'+owner+'.c')).read_text())
  for at in(0,100,216,236):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),refs)
  with self.assertRaises(ValueError):source.checked_payload(raw,{})
  q=json.loads((self.output/'private-layout-v2.json').read_text());self.assertEqual((q['words'],q['frame'],q['guards'],len(q['layouts'])),(60,88,0,3))
  for i in range(3):
   _,_,words=oracle.programs(self.output,i);self.assertEqual(words[0],words[1])
 def test_02_guest_sparse_packet_prefixes_original_factory_and_copy(self):
  q=oracle.qualify(ROOT,self.output);self.assertEqual((q['cases'],q['executions'],q['covered_words'],q['access_prefix_pairs']),(2742,5484,60,65));self.assertTrue(q['full60byte_packets_compared'])
  q=oracle.helpers(ROOT,self.output);self.assertEqual((q['cases'],q['executions'],q['original_factory_words'],q['original_copy_words']),(672,1344,39,11));self.assertTrue(q['all50_helper_words_executed'])
  self.assertTrue(oracle.padding_control(ROOT,self.output,source.SELECTED,source.HEADERS)['copied_padding_observably_different'])
 def test_03_all_three_original_callers_and_o32_ABI(self):
  q=integration.qualify(ROOT,self.output,oracle);self.assertEqual((q['original_callers'],q['total_cases'],q['executions']),(3,432,864));self.assertEqual([v['words']for v in q['windows']],[8,4,12]);self.assertFalse(q['whole_parents_executed'])
 def test_04_native_defined_fields_gates_fences_and_controls(self):
  q=native.qualify(ROOT,self.output,source.SELECTED,source.HEADERS,oracle);self.assertEqual((q['cases_per_profile'],q['effective_controls_each']),(262,9));self.assertEqual(q['profiles'],['O0','O2','O3']);self.assertTrue(q['UBSan']);self.assertTrue(q['uninitialized_padding_not_read_by_native_harness'])
 def test_05_actual_owner_Make_neighbors_and_strict_whole_image(self):
  function,owner,_,_=source.SPECS[0]
  for before,after in(('before-'+owner+'.o','after-'+owner+'.o'),('before-padded-'+owner+'.o','qualified-'+owner+'.o')):
   self.assertEqual(source.same_functions(self.output/before,self.output/after,(function,)),3);self.assertEqual(source.normalized_pools(self.output/before),source.normalized_pools(self.output/after))
  self.assertEqual((self.output/('qualified-'+owner+'.o')).read_bytes(),(self.output/('make-shadow-'+owner+'/src/game/'+owner+'.c.o')).read_bytes());self.assertEqual(len(json.loads((self.output/('Make-commands-'+owner+'.json')).read_text())),3)
  q=source.audit(ROOT,self.output,self.installed);self.assertEqual((q['functions'],q['other_bodies_fixed'],q['strict_exclusions'],q['closed_metadata_groups']),(6052,6051,0,2));self.assertTrue(q['all_function_addresses_fixed'])
  self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
  before=self.values['conker/build/conker.us.elf'];rom=self.values['conker/conker.us.bin'];actual=(self.output/'private-joint-linked.elf').read_bytes()
  for at in(0x100,len(actual)-1,source.elf_slot_offset(actual,source.SPECS[0][2],240)+24,2751800,3009480):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),rom)
  with self.assertRaises(ValueError):source.predict(actual,rom)
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
