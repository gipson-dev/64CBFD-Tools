"""Actor event callback ABI, switch ownership, original callers and literal ELF gates."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_actor_category_callback_match as source
from tools.experiments.game_actor_transform_position_match import check_owner_diagnostics
from tools.tests import game_actor_category_callback_oracle as oracle
from tools.tests import game_actor_category_callback_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class ActorCategoryCallbackTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));assert (cls.raw,cls.bindings)==source.payload(cls.output/'selected-final.o')
  cls.guest=oracle.qualify(ROOT,cls.output);cls.helper=oracle.helper(ROOT,cls.output);cls.callers=oracle.callers(ROOT,cls.output);cls.native=native.qualify(ROOT,cls.output,source.SELECTED)

 def test_direct_words_bindings_and_corruption_controls(self):
  self.assertEqual((len(self.raw),len(self.bindings)),(212,4));self.assertFalse(source.NEW_GUARDS)
  self.assertEqual(source.payload(self.output/'qualified-padded.o'),source.payload(self.output/'original-func_1513DF9C.o'))
  for at in (0,12,44,60,68,176,184,208):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  owner=source.recovered_owner(self.values[source.SOURCE].decode())
  self.assertEqual(owner,(self.output/'proposed-owner.c').read_text())
  with self.assertRaises(ValueError):source.recovered_owner(owner)
  make=source.recovered_makefile(self.values['conker/Makefile'].decode())
  self.assertEqual(make,(self.output/'proposed-Makefile').read_text())
  with self.assertRaises(ValueError):source.recovered_makefile(make)

 def test_owner_neighbors_switch_pool_diagnostics_and_actual_make(self):
  for a,b in (('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),58)
  self.assertEqual(source.normalized_pools(self.output/'before-owner.o'),{'.rodata':None,'.data':None})
  pools=source.normalized_pools(self.output/'after-owner.o')
  self.assertEqual(pools,{'.rodata':(bytes(64),tuple((i*4,source.FUNCTION,off)for i,off in enumerate(oracle.OFFSETS))),'.data':None})
  self.assertEqual(source.normalized_pools(self.output/'qualified-padded.o'),source.normalized_pools(self.output/'before-padded.o'));self.assertEqual(source.normalized_pools(self.output/'qualified-padded.o'),{'.rodata':None,'.data':(b'',())})
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game_169510.c.o').read_bytes())
  commands=json.loads((self.output/'Make-commands.json').read_text());self.assertEqual(len(commands),5)
  self.assertTrue(any('--rodata-symbol' in cmd and 'jtbl_800A5188_game' in cmd for cmd in commands))
  self.assertEqual(check_owner_diagnostics((self.output/'before-owner-diagnostics.txt').read_text(),(self.output/'after-owner-diagnostics.txt').read_text()),dict(before=43,after=43,removed=0))
  self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])

 def test_guest_all_indices_real_helpers_and_three_original_callers(self):
  q=self.guest;self.assertEqual((q['cases'],q['executions'],q['covered_words']),(32256,64512,52));self.assertEqual(q['unreachable_offsets'],[44]);self.assertEqual(q['access_prefix_pairs'],25);self.assertEqual(q['independent_link_layouts'],3);self.assertTrue(q['literal_full_model_state_equal']);self.assertEqual(q['sparse_flag_clear_executions'],2)
  q=self.helper;self.assertEqual((q['cases'],q['executions']),(1600,3200));self.assertTrue(all(q['retained_slots_equal_original'].values()))
  for row in q['original_helper_coverage'].values():self.assertEqual(row['words'],row['executed']);self.assertEqual(row['unexecuted'],[])
  self.assertTrue(q['lower_common_five_slot_ABI']);self.assertTrue(q['lower_common_function_stubbed']);self.assertFalse(q['all_complex_callbacks_claim'])
  q=self.callers;self.assertEqual((q['cases'],q['executions'],q['descriptor_registrations']),(2268,4536,3));self.assertEqual(q['descriptor_indices'],[27,72,85]);self.assertEqual(q['return_liveness_instruction_counts'],{'0x15169160':42,'0x15169340':52,'0x15169514':52});self.assertTrue(q['callback_result_not_consumed']);self.assertTrue(q['void_interface']);self.assertFalse(q['full_parent_functions_claim'])
  rom=self.values['conker/conker.us.bin'];needle=struct.pack('>I',source.ENTRY);found=[];at=0
  while True:
   at=rom.find(needle,at)
   if at<0:break
   if at%4==0:found.append(at)
   at+=1
  self.assertEqual(found,[0x230534,0x230E58,0x2310FC])
  self.assertEqual(tuple(struct.unpack('>13I',(self.output/'original-switch-table.bin').read_bytes())),tuple(source.ENTRY+v for v in oracle.OFFSETS))

 def test_native_complete_public_state_and_eight_effective_controls(self):
  self.assertEqual(len(self.native),3)
  for q in self.native:
   self.assertEqual((q['cases'],q['executions'],len(q['controls'])),(7680,69120,8));self.assertTrue(q['all_eight_controls_effective']);self.assertTrue(q['UBSan']);self.assertTrue(q['all_384_actor_and_64_context_bytes']);self.assertTrue(q['void_actor_word_byte_interface'])

 def test_literal_entire_image_metadata_extent_map_and_rejection_controls(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before),len(actual))
  self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
  q=json.loads((self.output/'private-image-qualification.json').read_text());self.assertEqual((q['functions'],q['other_bodies_fixed']),(6052,6051));self.assertTrue(q['all_function_addresses_fixed']);self.assertTrue(q['entire_named_definition_multiset_verified']);self.assertEqual(q['strict_exclusions'],0)
  rows={n:(at,f,st)for at,n,f,st in source.symbol_rows(actual)};self.assertEqual(rows[source.FUNCTION][1][1:3],(source.ENTRY,212))
  for at in (0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,212)+4,rows['func_151A6B3C'][0]+8,rows['D_8009E698'][2]):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  corrupt=bytearray(before);corrupt[0x100]^=1
  with self.assertRaises(ValueError):source.predict(bytes(corrupt),truth)
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
