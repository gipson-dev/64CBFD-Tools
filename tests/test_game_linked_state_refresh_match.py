"""Linked-state refresh, closed spill pair, original dispatcher and whole-image gates."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_linked_state_refresh_match as source
from tools.experiments.game_actor_transform_position_match import check_owner_diagnostics
from tools.tests import game_linked_state_refresh_oracle as oracle
from tools.tests import game_linked_state_refresh_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class LinkedStateRefreshTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));assert (cls.raw,cls.bindings)==source.payload(cls.output/'selected-final.o')
  cls.guest=oracle.qualify(ROOT,cls.output);cls.callers=oracle.callers(ROOT,cls.output);cls.native=native.qualify(ROOT,cls.output,source.SELECTED)

 def test_words_closed_private_spill_pair_and_corruption_controls(self):
  self.assertEqual((len(self.raw),len(self.bindings)),(220,2));self.assertEqual(source.NEW_GUARDS,[(0x68,0xAFA80024,0xAFA80028),(0x8C,0x8FA80024,0x8FA80028)])
  original,bindings=source.payload(self.output/'original-func_151A084C.o')
  self.assertEqual((source.normalized_payload(self.raw),self.bindings),(original,bindings));self.assertEqual(source.payload(self.output/'qualified-padded.o'),(original,bindings))
  self.assertEqual(sum(a!=b for a,b in zip(struct.unpack('>55I',self.raw),struct.unpack('>55I',original))),2)
  for at in (0,12,0x68,0x70,0x8C,0xA0,0xAC,216):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad))
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  owner=source.recovered_owner(self.values[source.SOURCE].decode());self.assertEqual(owner,(self.output/'proposed-owner.c').read_text())
  with self.assertRaises(ValueError):source.recovered_owner(owner)
  guards=source.recovered_guards(self.values['conker/retail_word_patches.us.csv']);self.assertEqual(guards,(self.output/'proposed-guards.csv').read_bytes())
  with self.assertRaises(ValueError):source.recovered_guards(guards)

 def test_owner_neighbors_pools_six_global_asm_bodies_and_actual_make(self):
  for a,b in (('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):
   self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),38);self.assertEqual(source.normalized_pools(self.output/a),source.normalized_pools(self.output/b))
  before=self.values[source.SOURCE].decode();after=source.recovered_owner(before);self.assertEqual(before.count('#pragma GLOBAL_ASM'),6);self.assertEqual(after.count('#pragma GLOBAL_ASM'),6)
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game/generated_1CC440.c.o').read_bytes());self.assertEqual(len(json.loads((self.output/'Make-commands.json').read_text())),5)
  self.assertEqual(check_owner_diagnostics((self.output/'before-owner-diagnostics.txt').read_text(),(self.output/'after-owner-diagnostics.txt').read_text()),dict(before=0,after=0,removed=0))
  self.assertEqual((ROOT/'conker/Makefile').read_bytes(),self.values['conker/Makefile'])

 def test_guest_live_mode_cached_output_live_cleanup_and_full_original_dispatcher(self):
  q=self.guest;self.assertEqual((q['cases'],q['executions'],q['covered_words']),(16128,48384,54));self.assertEqual(q['unreachable_offsets'],[160]);self.assertEqual(q['access_prefix_pairs'],85);self.assertEqual(q['independent_link_layouts'],3)
  self.assertTrue(q['raw_C_public_state_and_calls_equal']);self.assertTrue(q['normalized_complete_model_state_equal']);self.assertTrue(q['entry_mode_output_alias']);self.assertEqual(q['sparse_executions'],6)
  self.assertTrue(q['cleanup_retained_equal_original']);self.assertEqual((q['cleanup_connected_executions'],q['cleanup_words_executed']),(634,10));self.assertTrue(q['refresh_helper_stubbed']);self.assertFalse(q['portable_C_fault_claim'])
  q=self.callers;self.assertEqual((q['cases'],q['executions'],q['original_parent_words'],q['parent_words_executed']),(2688,5376,45,45));self.assertTrue(q['full_original_parent_connected']);self.assertTrue(q['real_cleanup_connected']);self.assertTrue(q['callback_return_unused']);self.assertTrue(q['signed_timer_wrapping_and_live_reload']);self.assertEqual(q['root_interface'],'void(struct260 *)');self.assertEqual(q['index'],11)
  rom=self.values['conker/conker.us.bin'];found=[];at=0;needle=struct.pack('>I',source.ENTRY)
  while True:
   at=rom.find(needle,at)
   if at<0:break
   if at%4==0:found.append(at)
   at+=1
  self.assertEqual(found,[0x22EFD4])

 def test_native_complete_public_memory_and_eight_effective_controls(self):
  self.assertEqual(len(self.native),3)
  for q in self.native:
   self.assertEqual((q['cases'],q['executions'],len(q['controls'])),(2816,25344,8));self.assertTrue(q['eight_controls_effective']);self.assertTrue(q['UBSan']);self.assertTrue(q['all_1472_public_bytes_checked']);self.assertTrue(q['real_cleanup_C_body_used']);self.assertTrue(q['output_mode_alias'])

 def test_literal_entire_image_extent_map_and_rejection_controls(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before),len(actual));self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
  q=json.loads((self.output/'private-owner-image-v12.json').read_text());self.assertEqual((q['functions'],q['other_bodies_fixed']),(6052,6051));self.assertTrue(q['all_function_addresses_fixed']);self.assertTrue(q['entire_named_definition_multiset_verified']);self.assertEqual(q['strict_exclusions'],0)
  rows={n:(at,f,st)for at,n,f,st in source.symbol_rows(actual)};self.assertEqual(rows[source.FUNCTION][1][1:3],(source.ENTRY,220))
  for at in (0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,220)+0x68,rows[source.FUNCTION][0]+8):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  bad=bytearray(before);bad[0x100]^=1
  with self.assertRaises(ValueError):source.predict(bytes(bad),truth)
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
