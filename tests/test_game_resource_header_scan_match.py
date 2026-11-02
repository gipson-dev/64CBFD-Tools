"""Complete metadata scan, derived roles/schedules and literal ELF accounting."""
from pathlib import Path
from collections import Counter
import json,os,struct,unittest
from tools.experiments import game_resource_header_scan_match as source
from tools.tests import game_resource_header_scan_oracle as oracle
from tools.tests import game_resource_header_scan_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class ResourceHeaderScanTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));cls.guest=oracle.qualify(ROOT,cls.output);cls.callers=oracle.callers(ROOT,cls.output);cls.native=native.qualify(ROOT,cls.output,source.SELECTED)
 def test_derived_register_roles_schedule_and_guard_corruption_controls(self):
  self.assertEqual(len(self.raw),248);self.assertEqual(len(source.NEW_GUARDS),19);self.assertEqual(struct.unpack_from('>I',self.raw)[0],0x27BDFFD0)
  original,bindings=source.payload(self.output/'original-func_15003570.o');self.assertEqual(source.normalized_payload(self.raw,self.bindings),(original,bindings));self.assertEqual(source.payload(self.output/'qualified-padded.o'),(original,bindings))
  q=json.loads((self.output/'private-layout-v10.json').read_text());self.assertTrue(q['no_inserted_or_deleted_instructions']);self.assertEqual(q['closed_saved_role_cycle'],[18,19]);self.assertEqual(q['independent_swaps'],[[0x4C,0x54],[0xB0,0xB4],[0xBC,0xC0]])
  self.assertEqual(sum(a!=b for a,b in zip(struct.unpack('>62I',self.raw),struct.unpack('>62I',original))),18)
  for at in (0,12,0x38,0x40,0x4C,0x54,0x84,0x98,0xB0,0xB4,0xBC,0xC0,0xC8,244):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.normalized_payload(self.raw,{})
  guards=source.recovered_guards(self.values['conker/retail_word_patches.us.csv']);self.assertEqual(guards,(self.output/'proposed-guards.csv').read_bytes());self.assertEqual(guards.count(b',func_15003570,'),19)
  with self.assertRaises(ValueError):source.recovered_guards(guards)
  owner=source.recovered_owner(self.values[source.SOURCE].decode());self.assertEqual(owner,(self.output/'proposed-owner.c').read_text())
  with self.assertRaises(ValueError):source.recovered_owner(owner)
 def test_eight_neighbors_pools_and_actual_plain_owner_make(self):
  for a,b in (('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):
   self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),8);self.assertEqual(source.normalized_pools(self.output/a),source.normalized_pools(self.output/b))
  self.assertEqual(self.values[source.SOURCE].decode().count('#pragma GLOBAL_ASM'),0)
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game_305D0.c.o').read_bytes());self.assertEqual(len(json.loads((self.output/'Make-commands.json').read_text())),3)
  self.assertEqual(source.check_owner_diagnostics((self.output/'before-owner-diagnostics.txt').read_text(),(self.output/'after-owner-diagnostics.txt').read_text()),dict(before=0,after=0,removed=0))
  self.assertEqual((ROOT/'conker/Makefile').read_bytes(),self.values['conker/Makefile'])
 def test_full_guest_scans_aliases_live_dma_null_prefix_and_real_startup_window(self):
  q=self.guest;self.assertEqual((q['full_scan_cases'],q['full_scan_executions'],q['records_per_scan'],q['covered_words']),(6,18,7762,62));self.assertEqual(q['access_prefix_pairs'],38);self.assertEqual(q['null_allocation_prefix_executions'],3);self.assertEqual(q['independent_group_layouts'],3)
  for n in ('normalized_complete_state_and_trace_equal','raw_final_state_equal','buffer_aliases_length_and_extent','live_DMA_mutations','no_graceful_null_failure_claim','allocator_DMA_free_implementations_stubbed'):self.assertTrue(q[n])
  q=self.callers;self.assertEqual((q['cases'],q['executions'],q['window_words']),(2,6,5));self.assertEqual(q['aligned_JAL_ROM'],[0x34D58]);self.assertTrue(q['all_window_words_executed']);self.assertTrue(q['retained_startup_124_words_equal_original']);self.assertFalse(q['full_startup_execution_claim']);self.assertTrue(q['root_return_not_consumed_in_window']);self.assertTrue(q['real_following_flag_store']);self.assertTrue(q['next_helper_stubbed'])
 def test_native_complete_tables_nine_effective_controls_and_null_call_prefix(self):
  self.assertEqual(len(self.native),3)
  for q in self.native:
   self.assertEqual((q['complete_scans'],q['records_per_scan'],q['entry_checks'],len(q['controls'])),(2,7762,15524,9))
   for n in ('null_first_DMA_prefix','nine_controls_effective','UBSan','table_and_buffer_fences_checked','live_length_after_DMA','hardware_providers_mocked'):self.assertTrue(q[n])
 def test_literal_entire_image_closed_metadata_order_and_rejection_controls(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before),len(actual));self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map']);source.verify_group(before)
  self.assertEqual(source.sha(actual),'f95f2f13f43d030328e6432e0240099f9abae1a5a5133719f649dd7cad72cf2c')
  q=json.loads((self.output/'private-owner-image-v15.json').read_text());self.assertEqual((q['functions'],q['other_bodies_fixed']),(6052,6051));self.assertTrue(q['all_function_addresses_fixed']);self.assertTrue(q['entire_named_definition_multiset_verified']);self.assertEqual(q['strict_exclusions'],0)
  rows={n:(at,f)for at,n,f,_ in source.symbol_rows(actual)};self.assertEqual(rows[source.FUNCTION][1][1:3],(source.ENTRY,248))
  # The serializer permutes precisely two adjacent complete records and their
  # adjacent strings; no symbol definitions or section geometry are excluded.
  unpermuted=bytearray(before);at=source.elf_slot_offset(before,source.ENTRY,248);unpermuted[at:at+248]=truth;struct.pack_into('>I',unpermuted,rows[source.FUNCTION][0]+8,248)
  self.assertEqual(source.serialize_metadata(unpermuted),actual)
  self.assertEqual(Counter((n,*f[1:])for _,n,f,_ in source.symbol_rows(unpermuted)),Counter((n,*f[1:])for _,n,f,_ in source.symbol_rows(actual)))
  with self.assertRaises(AssertionError):source.serialize_metadata(actual)
  for at in (0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,248)+0x84,rows[source.FUNCTION][0]+8,rows['D_8009E694'][0]+4):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  bad=bytearray(before);bad[0x100]^=1
  with self.assertRaises(ValueError):source.predict(bytes(bad),truth)
  bad=bytearray(before);row=next(v for v in source.symbol_rows(before)if v[1]=='D_800BC444');struct.pack_into('>I',bad,row[0]+4,row[2][1]+2)
  with self.assertRaises(ValueError):source.verify_group(bytes(bad))
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
