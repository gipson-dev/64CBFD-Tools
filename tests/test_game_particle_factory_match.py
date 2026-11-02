"""Particle factory scratch closure, real caller and spawn-copy chain, native and strict image."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_particle_factory_match as source
from tools.tests import game_particle_factory_oracle as oracle
from tools.tests import game_particle_factory_integration as integration
from tools.tests import game_particle_factory_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class ParticleFactoryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.installed=os.environ.get('CBFD_PARTICLE_FACTORY_INSTALLED')=='1';cls.values=source.check_inputs(ROOT,cls.output,cls.installed)
 def test_01_payload_bindings_symbolic_closure_and_independent_links(self):
  function,owner,entry,rom=source.SPECS[0];obj,diag=source.compile_owner(ROOT,self.output,source.HEADERS+source.SELECTED,'public-fresh-'+function)
  self.assertFalse(diag);raw,refs=source.checked_payload(*source.payload(obj,function));original,bindings=source.payload(self.output/('original-'+function+'.o'),function)
  self.assertEqual(source.normalized(raw,refs),(original,bindings));proof=source.prove(raw,original,refs,bindings);self.assertEqual(proof['ordered_observations'],132);self.assertEqual(proof['call_sites'],16);self.assertEqual(proof['branch_sites'],6);self.assertTrue(proof['loop_body_and_backedge_closed']);self.assertEqual(len(source.PATCHES),66);self.assertEqual(struct.unpack_from('>I',raw)[0],0x27BDFF00)
  self.assertEqual(source.recovered_owner(self.values['conker/src/game/'+owner+'.c'].decode(),0),(self.output/('proposed-'+owner+'.c')).read_text())
  for at,_,_ in source.PATCHES:
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),refs)
  with self.assertRaises(ValueError):source.checked_payload(raw,{})
  q=json.loads((self.output/'private-layout-v8.json').read_text());self.assertEqual((q['words'],q['frame'],len(q['patches']),len(q['layouts'])),(213,256,66,3))
  for i in range(3):
   entry=q['layouts'][i]['entry'];a=(self.output/('layout-%d-original.elf'%i)).read_bytes();b=(self.output/('layout-%d-C.elf'%i)).read_bytes();self.assertEqual(a[source.elf_slot_offset(a,entry,852):source.elf_slot_offset(a,entry,852)+852],b[source.elf_slot_offset(b,entry,852):source.elf_slot_offset(b,entry,852)+852])
  self.assertTrue((self.output/'proposed-guards.csv').read_bytes().startswith(self.values['conker/retail_word_patches.us.csv']))
 def test_02_guest_live_payload_prefixes_and_original_resolver_factory(self):
  q=oracle.qualify(ROOT,self.output);self.assertEqual((q['cases'],q['executions'],q['covered_nontrap_root_words'],q['access_prefix_triples']),(192,576,209,657));self.assertEqual((q['unreachable_divisor_traps'],q['complete56byte_copies'],q['real_wrapper_words'],q['real_memcpy_words']),(4,504,32,11));self.assertTrue(q['original_normalized_complete_state_equal']);self.assertTrue(q['finite_FP_operands_and_intermediates_enforced'])
 def test_03_complete_original_caller_and_o32_ABI(self):
  q=integration.qualify(ROOT,self.output,oracle);self.assertEqual((q['original_callers'],q['cases'],q['executions'],q['factory_entered_cases']),(1,768,2304,192));self.assertEqual((q['complete_caller_words'],q['complete_point_resolver_words']),(101,49));self.assertTrue(q['real_wrapper_copy_chain_connected']);self.assertFalse(q['gameplay_acceptance_claimed'])
 def test_04_native_defined_fields_live_provider_fences_and_controls(self):
  q=native.qualify(ROOT,self.output,source.SELECTED,source.HEADERS,oracle);self.assertEqual((q['cases_per_profile'],q['effective_controls_each']),(352,10));self.assertEqual(q['profiles'],['O0','O2','O3']);self.assertTrue(q['UBSan']);self.assertTrue(q['uninitialized_padding_not_read'])
 def test_05_actual_owner_Make_neighbors_and_strict_whole_image(self):
  function,owner,_,_=source.SPECS[0]
  for before,after in(('before-'+owner+'.o','after-'+owner+'.o'),('before-padded-'+owner+'.o','qualified-'+owner+'.o')):
   self.assertEqual(source.same_functions(self.output/before,self.output/after,(function,)),40);self.assertEqual(source.normalized_pools(self.output/before),source.normalized_pools(self.output/after))
  self.assertEqual((self.output/('qualified-'+owner+'.o')).read_bytes(),(self.output/('make-shadow-'+owner+'/src/game/'+owner+'.c.o')).read_bytes());self.assertEqual(len(json.loads((self.output/('Make-commands-'+owner+'.json')).read_text())),5)
  q=source.audit(ROOT,self.output,self.installed);self.assertEqual((q['functions'],q['other_bodies_fixed'],q['strict_exclusions'],q['closed_metadata_groups']),(6052,6051,0,0));self.assertTrue(q['all_function_addresses_fixed'])
  self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
  before=self.values['conker/build/conker.us.elf'];rom=self.values['conker/conker.us.bin'];actual=(self.output/'private-joint-linked.elf').read_bytes()
  for at in(0x100,len(actual)-1,source.elf_slot_offset(actual,source.SPECS[0][2],852)+24,*[v[0]for v in source.METADATA_GROUPS]):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),rom)
  with self.assertRaises(ValueError):source.predict(actual,rom)
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
