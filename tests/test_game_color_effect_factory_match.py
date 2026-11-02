"""Color-effect packet factory direct bytes, guest/native ABI, caller and strict image."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_color_effect_factory_match as source
from tools.tests import game_color_effect_factory_oracle as oracle
from tools.tests import game_color_effect_factory_integration as integration
from tools.tests import game_color_effect_factory_native as native

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class ColorEffectFactoryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD
  source.verify_prepared(cls.output)
  cls.installed=os.environ.get('CBFD_COLOR_EFFECT_FACTORY_INSTALLED')=='1'
  cls.values=source.check_inputs(ROOT,cls.output,cls.installed)

 def test_01_direct_payload_bindings_private_extent_and_independent_links(self):
  obj,diag=source.compile_owner(ROOT,self.output,source.HEADERS+source.SELECTED,'public-fresh-'+source.FUNCTION)
  self.assertFalse(diag)
  raw,refs=source.checked_payload(*source.payload(obj,source.FUNCTION))
  original,bindings=source.payload(self.output/('original-'+source.FUNCTION+'.o'),source.FUNCTION)
  self.assertEqual((raw,refs),(original,bindings))
  self.assertEqual(struct.unpack_from('>I',raw)[0],0x27BDFF70)
  self.assertEqual(source.recovered_owner(self.values['conker/src/game/'+source.OWNER+'.c'].decode()),(self.output/('proposed-'+source.OWNER+'.c')).read_text())
  with self.assertRaises(ValueError):source.checked_payload(raw[:-4],refs)
  with self.assertRaises(ValueError):source.checked_payload(raw,{})
  q=json.loads((self.output/'private-layout-v4.json').read_text())
  self.assertEqual((q['words'],q['frame'],q['guards'],len(q['layouts'])),(146,144,0,3))
  self.assertEqual((q['packet_visible_bytes'],q['private_packet_extent_bytes'],q['tail_bytes_untouched']),(52,56,True))
  for i in range(3):
   entry=q['layouts'][i]['entry'];a=(self.output/('layout-%d-original.elf'%i)).read_bytes();b=(self.output/('layout-%d-C.elf'%i)).read_bytes()
   aa=source.elf_slot_offset(a,entry,source.SIZE);bb=source.elf_slot_offset(b,entry,source.SIZE)
   self.assertEqual(a[aa:aa+source.SIZE],b[bb:bb+source.SIZE])

 def test_02_guest_semantics_full_state_and_access_prefixes(self):
  q=oracle.qualify(ROOT,self.output)
  self.assertEqual((q['cases'],q['executions'],q['covered_nontrap_words'],q['unreachable_divisor_traps']),(256,512,142,4))
  self.assertEqual((q['semantic_layouts'],q['independent_GNU_links'],q['access_prefix_pairs']),(1,3,129))
  self.assertTrue(q['original_and_C_full_state_calls_packets_and_traces_equal'])
  self.assertTrue(q['live_input_after_first_RNG_and_after_submit'])

 def test_03_sole_original_caller_window_and_o32_ABI(self):
  q=integration.qualify(ROOT,self.output)
  self.assertEqual((q['original_callers'],q['parent_words'],q['bounded_original_window_words'],q['cases']),(1,221,4,256))
  self.assertEqual(q['aligned_ROM_JALs'],['0xfafa4'])
  self.assertTrue(q['JAL_delay_sets_input_pointer'])
  self.assertTrue(q['return_not_consumed_before_parent_return'])
  self.assertFalse(q['full_parent_execution_claimed'])

 def test_04_native_layout_live_reads_and_effective_controls(self):
  q=native.qualify(ROOT,self.output,source.SELECTED,source.HEADERS)
  self.assertEqual((q['cases_per_profile'],q['effective_controls_each']),(256,11))
  self.assertEqual(q['profiles'],['O0','O2','O3'])
  self.assertEqual((q['input_size'],q['packet_visible_bytes'],q['packet_private_extent']),(76,52,56))
  self.assertTrue(q['UBSan'])
  self.assertTrue(q['all256_mode_bytes'])
  self.assertTrue(q['live_input_after_first_RNG_and_submit'])

 def test_05_actual_Make_neighbors_protected_data_and_strict_image(self):
  for before,after in (('before-'+source.OWNER+'.o','after-'+source.OWNER+'.o'),('before-padded-'+source.OWNER+'.o','qualified-'+source.OWNER+'.o')):
   self.assertEqual(source.same_functions(self.output/before,self.output/after,(source.FUNCTION,)),40)
   self.assertEqual(source.normalized_pools(self.output/before),source.normalized_pools(self.output/after))
  self.assertEqual((self.output/('qualified-'+source.OWNER+'.o')).read_bytes(),(self.output/('make-shadow-'+source.OWNER+'/src/game/'+source.OWNER+'.c.o')).read_bytes())
  self.assertEqual(len(json.loads((self.output/('Make-commands-'+source.OWNER+'.json')).read_text())),5)
  q=source.audit(ROOT,self.output,self.installed)
  self.assertEqual((q['functions'],q['other_bodies_fixed'],q['strict_exclusions'],q['closed_metadata_groups']),(6052,6051,0,1))
  self.assertTrue(q['all_function_addresses_fixed'])
  self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
  before=self.values['conker/build/conker.us.elf'];rom=(ROOT/'conker/conker.us.bin').read_bytes();actual=((ROOT/'conker/build/conker.us.elf')if self.installed else(self.output/'private-joint-linked.elf')).read_bytes()
  for at in (0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,source.SIZE)+24,source.METADATA_GROUPS[0][0]):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),rom)
