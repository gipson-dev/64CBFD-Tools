"""Packed scale command, relocation schedule and complete overflow-removal audit."""
from pathlib import Path
import json,os,sys,unittest
from tools.experiments import game_packed_scale_command_match as source
from tools.tests import game_packed_scale_command_oracle as oracle
import tools.pad_generated_object as generated_pad
sys.modules.setdefault('pad_generated_object',generated_pad)
from tools import pad_c_object as pad
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class PackedScaleCommandTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected')
  if diag:raise AssertionError(diag)
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_closed_instruction_and_relocation_permutation(self):
  self.assertEqual(len(self.raw),184);self.assertEqual(source.derive_guards(self.raw,self.bindings),source.NEW_GUARDS);self.assertEqual(len(source.NEW_GUARDS),25)
  original=source.payload(self.output/'original-func_15076D3C.o')
  self.assertEqual((source.normalized_payload(self.raw,self.bindings),source.normalized_bindings(self.bindings)),original)
  for at in(0,8,92,96,104,180):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.derive_guards(self.raw,{})
  before=self.values['conker/retail_word_patches.us.csv'];after=source.proposed_guards(before);self.assertTrue(after.startswith(before));self.assertEqual(len(after.splitlines())-len(before.splitlines()),25)
  with self.assertRaises(ValueError):source.proposed_guards(after)
  bad=after.replace(b'0x008,0x24420000',b'0x008,0x24420001');self.assertNotEqual(bad,after);p=self.output/'public-bad-guards.csv';p.write_bytes(bad)
  with self.assertRaisesRegex(ValueError,'stale word patch'):pad.emit_padded_assembly(self.output/'after-owner.o',ROOT/source.LAYOUT,filename=source.OWNER,word_patches_path=p)
 def test_complete_owner_actual_make_and_pools(self):
  self.assertEqual(source.same_functions(self.output/'before-owner.o',self.output/'after-owner.o',(source.FUNCTION,)),210)
  self.assertEqual(source.same_functions(self.output/'before-padded.o',self.output/'qualified-padded.o',(source.FUNCTION,)),210)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game_A28B0.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=14,after=14,removed=0));self.assertEqual(q['actual_Make_commands'],5);self.assertTrue(q['strict_whole_image_prediction'])
 def test_signed_bytes_aliases_rebases_and_access_prefixes(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['rebases']),(10752,53760,3));self.assertTrue(q['all_46_words_executed']);self.assertTrue(q['all_256_values_in_each_packed_byte']);self.assertEqual(q['global_alias_layouts'],7)
  self.assertTrue(q['four_exact_programs_full_state_equal']);self.assertTrue(q['unguarded_C_public_memory_and_preserved_ABI_equal'])
  q=self.runtime['faults'];self.assertEqual((q['prefixes'],q['executions']),(60,240));self.assertTrue(q['exact_programs_full_state_equal']);self.assertTrue(q['unguarded_C_fault_order_not_claimed'])
 def test_original_helper_script_dispatch_and_retargeted_entries(self):
  q=self.runtime['connected'];self.assertEqual((q['cases'],q['executions'],q['complete_original_scale_helper_words']),(1024,5120,77));self.assertTrue(q['all_77_helper_words_executed']);self.assertEqual(q['nested_paths'],512)
  q=self.runtime['callers'];self.assertEqual((q['cases'],q['executions'],q['original_window_words']),(480,2400,29));self.assertTrue(q['all_28_reachable_window_words_executed']);self.assertTrue(q['packet_bytes_and_advance_5_or_1_verified']);self.assertTrue(q['void_result_ignored'])
  q=self.runtime['retargeted_trampolines'];self.assertEqual((q['cases'],q['executions'],q['retargeted_entries']),(16,32,2));self.assertTrue(q['all_registers_and_memory_unchanged'])
  q=json.loads((self.output/'caller-census.json').read_text());self.assertEqual(q['aligned_ROM_pointer_literals'],[0x22B348]);self.assertEqual(q['row'],86);self.assertFalse(q['aligned_ROM_JALs']);self.assertFalse(q['aligned_ROM_Js'])
 def test_native_profiles_canaries_and_effective_controls(self):
  self.assertEqual([q['profile']for q in self.runtime['native']],['-O0','-O2','-O3'])
  for q in self.runtime['native']:
   self.assertEqual(q['cases'],2048);self.assertTrue(q['UBSan']);self.assertTrue(q['canaries']);self.assertTrue(q['all_eight_controls_effective']);self.assertTrue(q['factor_alias_native_qualified']);self.assertTrue(q['current_actor_pointer_aliases_guest_only'])
 def test_literal_entire_image_and_complete_executable_closure(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before)-len(actual),224)
  q=source.closure_audit(self.output/'before-conker_build_conker.us.elf',self.output/'first-linked.elf');self.assertEqual((q['functions_before'],q['functions'],q['canonical_function_addresses_fixed'],q['other_bodies_fixed']),(6056,6055,6045,6052));self.assertEqual(len(q['private_bodies_moved']),4);self.assertEqual(q['retargeted_trampolines'],['func_150781F4','func_150A7D00'])
  rows={name:(at,f,string)for at,name,f,string in source.symbol_rows(actual)}
  offsets=[0x100,source.elf_slot_offset(actual,source.ENTRY,184)+4]
  for name in(q['private_bodies_moved']+q['retargeted_trampolines']+['__romPos']):
   at,f,string=rows[name];offsets.extend((at+4,string))
   if name!='__romPos':offsets.append(source.elf_slot_offset(actual,f[1],4))
  for at in offsets:
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner(self.values[source.SOURCE].decode()))
  old_map=(self.output/'before-conker_build_conker.us.map').read_bytes();new_map=(self.output/'installed-conker_build_conker.us.map').read_bytes();source.check_map(old_map,new_map)
  bad=bytearray(new_map);bad[0]^=1
  with self.assertRaises(ValueError):source.check_map(old_map,bytes(bad))
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:source.audit(ROOT,self.output)
