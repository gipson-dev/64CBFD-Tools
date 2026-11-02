"""Owner row cleanup: loop rotation, live repair, ABI and entire-image gates."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_owner_row_cleanup_match as source
from tools.experiments.game_actor_transform_position_match import check_owner_diagnostics
from tools.tests import game_owner_row_cleanup_oracle as oracle
from tools.tests import game_owner_row_cleanup_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class OwnerRowCleanupTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));assert (cls.raw,cls.bindings)==source.payload(cls.output/'selected-final.o')
  cls.guest=oracle.qualify(ROOT,cls.output,obj);cls.helpers=oracle.helper(ROOT,cls.output);cls.callers=oracle.callers(ROOT,cls.output);cls.native=native.qualify(ROOT,cls.output,source.SELECTED)

 def test_closed_loop_rotation_relocations_and_corruption_controls(self):
  self.assertEqual((len(self.raw),len(self.bindings)),(216,9));self.assertEqual(len(source.NEW_GUARDS),8)
  original,bindings=source.payload(self.output/'original-func_1518BBF4.o')
  self.assertEqual(source.normalized_payload(self.raw,self.bindings),(original,bindings));self.assertEqual(source.payload(self.output/'normalized-isolated.o'),(original,bindings));self.assertEqual(source.payload(self.output/'qualified-padded.o'),(original,bindings))
  self.assertEqual(struct.unpack_from('>I',self.raw,0)[0],0x27BDFFD0)
  self.assertEqual(struct.unpack_from('>I',original,0)[0],0x27BDFFD0)
  self.assertEqual([p[0]for p in source.NEW_GUARDS],[0x20,0x28,0x34,0x38,0x3C,0x40,0xB0,0xB4])
  self.assertEqual([p[5]for p in source.NEW_GUARDS if p[5]is not None],[0x822E0000]);self.assertEqual(struct.unpack_from('>I',self.raw,0x44)[0],0x822E0000)
  self.assertEqual([p[2]for p in source.NEW_GUARDS[-2:]],[0xA22E0000,0x5674FFE4]);source.verify_group(self.values['conker/build/conker.us.elf'])
  for at in (0,12,0x20,0x28,0x34,0x44,0x74,0xB0,0xB4,212):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  bad=dict(self.bindings);bad[40]=[('R_MIPS_HI16','D_800DD190')]
  with self.assertRaises(ValueError):source.normalized_payload(self.raw,bad)
  owner=source.recovered_owner(self.values[source.SOURCE].decode());self.assertEqual(owner,(self.output/'proposed-owner.c').read_text())
  with self.assertRaises(ValueError):source.recovered_owner(owner)
  guards=source.recovered_guards(self.values['conker/retail_word_patches.us.csv']);self.assertEqual(guards,(self.output/'proposed-guards.csv').read_bytes());self.assertEqual(guards.count(b',func_1518BBF4,'),8)
  with self.assertRaises(ValueError):source.recovered_guards(guards)

 def test_eight_owner_neighbors_pools_and_actual_make(self):
  for a,b in (('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):
   self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),8);self.assertEqual(source.normalized_pools(self.output/a),source.normalized_pools(self.output/b))
  before=self.values[source.SOURCE].decode();after=source.recovered_owner(before);self.assertEqual(before.count('#pragma GLOBAL_ASM'),0);self.assertEqual(after.count('#pragma GLOBAL_ASM'),0)
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game/generated_1B8F40.c.o').read_bytes());self.assertEqual(len(json.loads((self.output/'Make-commands.json').read_text())),3)
  self.assertEqual(check_owner_diagnostics((self.output/'before-owner-diagnostics.txt').read_text(),(self.output/'after-owner-diagnostics.txt').read_text()),dict(before=0,after=0,removed=0))
  self.assertEqual((ROOT/'conker/Makefile').read_bytes(),self.values['conker/Makefile'])

 def test_guest_live_depth_repair_cycles_original_helpers_and_caller(self):
  q=self.guest;self.assertEqual((q['cases'],q['executions'],q['total_input_cases']),(17292,51876,5824));self.assertEqual((q['cyclic_cases'],q['cyclic_prefix_executions'],q['cyclic_callback_limit']),(60,540,16));self.assertTrue(q['cyclic_reference_state_repeat_verified'])
  self.assertEqual((q['original_words_covered'],q['raw_words_covered']),(51,50));self.assertEqual(q['unreachable_offsets'],[116,120,124,128]);self.assertEqual(q['access_prefix_triplets'],226);self.assertEqual(q['independent_group_link_layouts'],3)
  for name in ('raw_and_normalized_full_bounded_state_and_access_trace_equal','opaque_owner_not_dereferenced','all_256_depth_bytes_empty_rows','signed_depth_alias_boundaries','live_stack_and_depth_mutations','modeled_nested_repair','actual_cleanup_helper_stubbed','extra_static_load_adds_no_dynamic_read'):self.assertTrue(q[name])
  self.assertEqual(q['null_owner_unmapped_public_executions'],3);self.assertFalse(q['raw_fault_PC_or_BD_equivalence_claim'])
  q=self.helpers;self.assertEqual((q['cases'],q['executions'],q['cyclic_cases'],q['cyclic_prefix_executions']),(484,1452,4,12))
  self.assertTrue(all(q['retained_helpers_equal_original'].values()));self.assertEqual(sum(v['words']for v in q['original_helper_coverage'].values()),56)
  for v in q['original_helper_coverage'].values():self.assertEqual(v['words'],v['executed']);self.assertEqual(v['unexecuted'],[])
  self.assertTrue(q['live_outer_pending_pointer_repair']);self.assertTrue(q['lower_release_and_callbacks_stubbed']);self.assertFalse(q['full_engine_claim'])
  q=self.callers;self.assertEqual((q['cases'],q['executions'],q['window_words'],q['aligned_direct_JAL_ROM']),(157,471,4,0xC5A1C));self.assertTrue(q['all_window_words_executed']);self.assertTrue(q['actual_S1_to_A0_delay_slot']);self.assertTrue(q['caller_forces_return_one']);self.assertTrue(q['root_void_return_interface']);self.assertFalse(q['full_parent_function_claim'])

 def test_native_public_memory_controls_and_advisory_disposition(self):
  self.assertEqual(len(self.native),3)
  for q in self.native:
   self.assertEqual((q['cases'],q['executions'],len(q['controls'])),(2892,26028,8))
   for name in ('complete_public_World_bytes','signed_indices_use_valid_interior_array','depth_independent_of_table_endpoint','live_slots_and_depth_checked','modeled_nested_repair','eight_controls_effective','UBSan','advisory_semantic_changes_rejected'):self.assertTrue(q[name])
  q=json.loads((self.output/'advisory-disposition-v14.json').read_text());self.assertEqual((q['advisory_invocations'],q['advisory_completed'],q['adopted_C_suggestions']),(1,1,0));self.assertEqual(q['read_only_effective_tools'],[]);self.assertEqual(q['read_only_effective_MCP'],[]);self.assertTrue(q['normalization_independently_derived']);self.assertTrue(all(p['byte_payload_and_bindings_equal']for p in q['recommendation_2']['pairs']))

 def test_literal_entire_image_extent_map_and_rejection_controls(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before),len(actual));self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
  self.assertEqual(source.sha(actual),'83088793cafaec148da7082549742f2dd2c964ba2049ca56acb368fc8e01e6d1')
  q=json.loads((self.output/'private-owner-image-v15.json').read_text());self.assertEqual((q['functions'],q['other_bodies_fixed']),(6052,6051));self.assertTrue(q['all_function_addresses_fixed']);self.assertTrue(q['entire_named_definition_multiset_verified']);self.assertEqual(q['strict_exclusions'],0)
  rows={n:(at,f,st)for at,n,f,st in source.symbol_rows(actual)};self.assertEqual(rows[source.FUNCTION][1][1:3],(source.ENTRY,220))
  for at in (0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,220)+0xB8,rows[source.FUNCTION][0]+8):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  bad=bytearray(before);bad[0x100]^=1
  with self.assertRaises(ValueError):source.predict(bytes(bad),truth)
  bad=bytearray(before);struct.pack_into('>I',bad,rows['D_800DD190'][0]+4,rows['D_800DD190'][1][1]+4)
  with self.assertRaises(ValueError):source.verify_group(bytes(bad))
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
