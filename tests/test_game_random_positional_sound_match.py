"""Direct sound selection C, live provider timing, original ABI and full image."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_random_positional_sound_match as source
from tools.tests import game_random_positional_sound_oracle as oracle
from tools.tests import game_random_positional_sound_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class RandomPositionalSoundTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));assert (cls.raw,cls.bindings)==source.payload(cls.output/'original-func_151618BC.o')
  cls.guest=oracle.qualify(ROOT,cls.output,obj);cls.helpers=oracle.helpers(ROOT,cls.output,obj);cls.callers=oracle.callers(ROOT,cls.output,obj);cls.native=native.qualify(ROOT,cls.output,source.SELECTED,source.HEADERS)
 def test_direct_words_sequencing_and_corruption_controls(self):
  self.assertEqual((len(self.raw),len(self.bindings)),(228,4));self.assertEqual(source.NEW_GUARDS,[]);self.assertEqual(struct.unpack_from('>I',self.raw)[0],0x27BDFFA0)
  self.assertEqual(source.payload(self.output/'qualified-padded.o'),(self.raw,self.bindings))
  self.assertLess(source.SELECTED.index('sounds ='),source.SELECTED.index('selected ='));self.assertLess(source.SELECTED.index('selected ='),source.SELECTED.index('func_10010F88('))
  for at in (0,12,0x1C,0x54,0x60,0x84,0xC0,224):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  owner=source.recovered_owner(self.values[source.SOURCE].decode());self.assertEqual(owner,(self.output/'proposed-owner.c').read_text())
  with self.assertRaises(ValueError):source.recovered_owner(owner)
 def test_owner_neighbors_pools_actual_make_and_exact_diagnostic_repair(self):
  for a,b in (('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):
   self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),77);self.assertEqual(source.normalized_pools(self.output/a),source.normalized_pools(self.output/b))
  before=self.values[source.SOURCE].decode();self.assertEqual(before.count('#pragma GLOBAL_ASM'),2);self.assertEqual(source.recovered_owner(before).count('#pragma GLOBAL_ASM'),2)
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game_18D770.c.o').read_bytes());self.assertEqual(len(json.loads((self.output/'Make-commands.json').read_text())),5)
  a=(self.output/'before-owner-diagnostics.txt').read_text();b=(self.output/'after-owner-diagnostics.txt').read_text();self.assertEqual(source.check_owner_diagnostics(a,b),dict(before=45,after=44,removed=1))
  with self.assertRaises(ValueError):source.check_owner_diagnostics(a,a)
  with self.assertRaises(ValueError):source.check_owner_diagnostics(a,b+'\ncfe: Warning 712: unrelated.c, line 1: extra warning\n bad();\n')
  self.assertEqual((ROOT/'conker/Makefile').read_bytes(),self.values['conker/Makefile']);self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
 def test_guest_wrapper_and_both_original_caller_windows(self):
  q=self.guest;self.assertEqual((q['cases'],q['executions'],q['layouts'],q['covered_words'],q['access_prefix_pairs']),(2496,4992,3,57,129))
  for n in ('complete_bounded_machine_and_access_state_equal','table_position_alias','copy_before_rng_and_live_position','all_seven_live_argument_homes','finite_representable_float_domain'):self.assertTrue(q[n])
  self.assertFalse(q['portable_fault_claim'])
  q=self.helpers;self.assertEqual((q['cases'],q['executions'],q['original_wrapper_words']),(278,556,29));self.assertTrue(q['all_wrapper_words_executed']);self.assertTrue(q['retained_wrapper_equals_original']);self.assertTrue(q['lower_provider_stubbed']);self.assertTrue(q['signed_halfword_coordinate_consumption'])
  q=self.callers;self.assertEqual(q['original_callers'],2);self.assertFalse(q['full_parent_claim']);self.assertTrue(q['actual_outgoing_stack_stores']);self.assertTrue(q['return_not_consumed_in_windows'])
  self.assertEqual([(v['words'],v['cases'],v['executions'])for v in q['windows']],[(9,76,152),(5,76,152)]);self.assertTrue(all(v['all_window_words_executed']for v in q['windows']))
  rom=self.values['conker/conker.us.bin'];found=[];jumps=[];pointers=[]
  for at in range(0,len(rom)-3,4):
   w=struct.unpack_from('>I',rom,at)[0]
   if w>>26 in(2,3)and((w&0x3FFFFFF)<<2)==(source.ENTRY&0xFFFFFFF):(found if w>>26==3 else jumps).append(at)
   if w==source.ENTRY:pointers.append(at)
  self.assertEqual(found,[0x18DA44,0x18DEF0]);self.assertEqual(jumps,[]);self.assertEqual(pointers,[])
 def test_native_explicit_order_typed_audio_and_eight_effective_controls(self):
  self.assertEqual(len(self.native),3)
  for q in self.native:
   self.assertEqual((q['cases'],q['baseline_executions'],len(q['controls'])),(208,208,8))
   for n in ('eight_controls_effective','UBSan','all_public_table_and_position_words_checked','typed_audio_boundary_checked','finite_s32_float_domain','guest_home_mutations_excluded'):self.assertTrue(q[n])
  screens=json.loads((self.output/'order-screen-v11.json').read_text());self.assertEqual([(v['words'],v['frame'],v['differences'])for v in screens],[(57,96,2),(57,96,0),(57,96,2),(57,96,0)])
 def test_literal_entire_image_extent_map_and_rejection_controls(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before),len(actual));self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
  self.assertEqual(source.sha(actual),'d84330cbf2a3b42de99a5866420c428b00e42a6735f43a6601c76e4235255996')
  q=json.loads((self.output/'private-owner-image-v12.json').read_text());self.assertEqual((q['functions'],q['other_bodies_fixed']),(6052,6051));self.assertTrue(q['all_function_addresses_fixed']);self.assertTrue(q['entire_named_definition_multiset_verified']);self.assertEqual(q['strict_exclusions'],0)
  row=next(v for v in source.symbol_rows(actual)if v[1]==source.FUNCTION);self.assertEqual(row[2][1:3],(source.ENTRY,228))
  for at in (0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,228)+0x60,row[0]+8):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  bad=bytearray(before);bad[0x100]^=1
  with self.assertRaises(ValueError):source.predict(bytes(bad),truth)
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
