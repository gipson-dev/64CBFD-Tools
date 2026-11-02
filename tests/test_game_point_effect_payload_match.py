"""Attached-point effect payload, guarded roles, original helpers and strict linked image."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_point_effect_payload_match as source
from tools.tests import game_point_effect_payload_oracle as oracle
from tools.tests import game_point_effect_payload_integration as integration
from tools.tests import game_point_effect_payload_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class PointEffectPayloadTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.installed=os.environ.get('CBFD_POINT_EFFECT_INSTALLED')=='1';cls.values=source.check_inputs(ROOT,cls.output,cls.installed)
 def test_01_payload_bindings_symbolic_closure_and_independent_links(self):
  function,owner,entry,rom=source.SPECS[0];obj,diag=source.compile_owner(ROOT,self.output,source.HEADERS+source.SELECTED,'public-fresh-'+function)
  self.assertFalse(diag);raw,refs=source.checked_payload(*source.payload(obj,function));original,bindings=source.payload(self.output/('original-'+function+'.o'),function)
  self.assertEqual(source.normalized(raw,refs),(original,bindings));proof=source.prove_roles(raw,original,refs,bindings,source.GUARDS);self.assertEqual(proof['ordered_observations'],63);self.assertEqual(proof['helper_call_offsets'],[52,380]);self.assertEqual(len(source.PATCHES),18);self.assertEqual(struct.unpack_from('>I',raw)[0],0x27BDFF68)
  self.assertEqual(source.recovered_owner(self.values['conker/src/game/'+owner+'.c'].decode(),0),(self.output/('proposed-'+owner+'.c')).read_text())
  for at,_,_ in source.PATCHES:
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),refs)
  with self.assertRaises(ValueError):source.checked_payload(raw,{})
  q=json.loads((self.output/'private-layout-v6.json').read_text());self.assertEqual((q['words'],q['frame'],q['guards'],len(q['layouts'])),(101,152,18,3))
  for i in range(3):
   _,_,words=oracle.programs(self.output,i);self.assertEqual(words[0],words[1])
  self.assertTrue((self.output/'proposed-guards.csv').read_bytes().startswith(self.values['conker/retail_word_patches.us.csv']))
 def test_02_guest_live_payload_prefixes_and_original_resolver_factory(self):
  q=oracle.qualify(ROOT,self.output);self.assertEqual((q['cases'],q['executions'],q['covered_words'],q['access_prefix_triples']),(3561,10683,101,125));self.assertTrue(q['all256_mode_bytes'])
  q=oracle.helpers(ROOT,self.output);self.assertEqual((q['cases'],q['executions'],q['point_words'],q['factory_words'],q['covered_nontrap_helper_words']),(112,336,49,213,258));self.assertEqual(q['particle_counts'],[8,9,15]);self.assertTrue(q['factory_is_still_an_unrestored_stub']);self.assertTrue(q['independent_all_spawn_arguments_and_descriptor_vector_snapshots'])
 def test_03_all_three_original_callers_and_o32_ABI(self):
  q=integration.qualify(ROOT,self.output,oracle);self.assertEqual((q['original_callers'],q['total_cases'],q['executions']),(3,648,1944));self.assertEqual([v['words']for v in q['windows']],[8,4,12]);self.assertTrue(q['dynamic_first_mode_byte_and_zero_extra']);self.assertTrue(q['complete_wrapper_executed']);self.assertFalse(q['whole_large_parents_executed'])
 def test_04_native_defined_fields_live_provider_fences_and_controls(self):
  q=native.qualify(ROOT,self.output,source.SELECTED,source.HEADERS,oracle);self.assertEqual((q['cases_per_profile'],q['effective_controls_each']),(336,9));self.assertEqual(q['profiles'],['O0','O2','O3']);self.assertTrue(q['UBSan']);self.assertTrue(q['untouched_padding_not_read'])
 def test_05_actual_owner_Make_neighbors_and_strict_whole_image(self):
  function,owner,_,_=source.SPECS[0]
  for before,after in(('before-'+owner+'.o','after-'+owner+'.o'),('before-padded-'+owner+'.o','qualified-'+owner+'.o')):
   self.assertEqual(source.same_functions(self.output/before,self.output/after,(function,)),3);self.assertEqual(source.normalized_pools(self.output/before),source.normalized_pools(self.output/after))
  self.assertEqual((self.output/('qualified-'+owner+'.o')).read_bytes(),(self.output/('make-shadow-'+owner+'/src/game/'+owner+'.c.o')).read_bytes());self.assertEqual(len(json.loads((self.output/('Make-commands-'+owner+'.json')).read_text())),3)
  q=source.audit(ROOT,self.output,self.installed);self.assertEqual((q['functions'],q['other_bodies_fixed'],q['strict_exclusions'],q['closed_metadata_groups']),(6052,6051,0,9));self.assertTrue(q['all_function_addresses_fixed'])
  self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
  before=self.values['conker/build/conker.us.elf'];rom=self.values['conker/conker.us.bin'];actual=(self.output/'private-joint-linked.elf').read_bytes()
  for at in(0x100,len(actual)-1,source.elf_slot_offset(actual,source.SPECS[0][2],404)+24,*[v[0]for v in source.METADATA_GROUPS]):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),rom)
  with self.assertRaises(ValueError):source.predict(actual,rom)
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
