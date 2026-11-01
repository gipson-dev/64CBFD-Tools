"""Direct path coordinate C, alias controls and complete linked-image audit."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_path_node_position_match as source
from tools.tests import game_path_node_position_oracle as oracle
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class PathNodePositionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag,diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_direct_complete_payload_and_bindings(self):
  self.assertEqual(len(self.raw),224);self.assertEqual(len(self.bindings),8);self.assertFalse(source.NEW_GUARDS)
  self.assertEqual((self.raw,self.bindings),source.payload(self.output/'original-func_15077DBC.o'))
  for at in(0,20,48,100,160,220):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner(self.values[source.SOURCE].decode()))
 def test_owner_neighbors_pools_actual_make_and_unchanged_guards(self):
  self.assertEqual(source.same_functions(self.output/'before-owner.o',self.output/'after-owner.o',(source.FUNCTION,)),210)
  self.assertEqual(source.same_functions(self.output/'before-padded.o',self.output/'qualified-padded.o',(source.FUNCTION,)),210)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game_A28B0.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=14,after=14,removed=0));self.assertEqual(q['actual_Make_commands'],5)
 def test_guest_signed_coordinates_reloads_rebases_and_fault_prefixes(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['rebases'],q['alias_layouts']),(10752,43008,3,7));self.assertTrue(q['all_256_commands']);self.assertTrue(q['all_56_words_executed']);self.assertTrue(q['four_programs_full_state_equal'])
  q=self.runtime['faults'];self.assertEqual((q['prefixes'],q['executions']),(70,280));self.assertTrue(q['complete_states_equal'])
 def test_original_dispatch_caller_and_effective_cache_controls(self):
  q=self.runtime['callers'];self.assertEqual((q['cases'],q['executions'],q['original_window_words'],q['reachable_words']),(120,480,29,28));self.assertEqual(q['return_poisons'],4);self.assertTrue(q['packet_advance_5_or_1']);self.assertTrue(q['void_return_ignored']);self.assertFalse(q['full_dispatcher_emulation'])
  self.assertEqual([x['control']for x in self.runtime['alias_negative_controls']],['cached-actor','cached-table','cached-node']);self.assertTrue(all(x['effective']for x in self.runtime['alias_negative_controls']))
  q=json.loads((self.output/'caller-census.json').read_text());self.assertEqual(q['row'],153);self.assertEqual(q['aligned_ROM_pointer_literals'],[0x22B454]);self.assertFalse(q['aligned_ROM_JALs']);self.assertFalse(q['aligned_ROM_Js'])
 def test_native_profiles_full_canaries_and_seven_controls(self):
  self.assertEqual([q['profile']for q in self.runtime['native']],['-O0','-O2','-O3'])
  for q in self.runtime['native']:
   self.assertEqual(q['cases'],2048);self.assertTrue(q['UBSan']);self.assertTrue(q['full_actor_canaries']);self.assertTrue(q['path_data_unchanged']);self.assertTrue(q['all_seven_controls_effective']);self.assertTrue(q['pointer_aliases_guest_only'])
 def test_literal_full_image_all_definitions_and_live_inputs(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+224];actual=(self.output/'first-linked.elf').read_bytes()
  source.check_image(before,actual,truth);self.assertEqual(len(actual),len(before))
  symbol=next(row for row in source.symbol_rows(actual)if row[1]==source.FUNCTION)
  for at in(0x100,source.elf_slot_offset(actual,source.ENTRY,224)+4,symbol[0]+8,len(actual)-1):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:
   q=source.audit(ROOT,self.output);self.assertEqual(q['functions'],6055);self.assertEqual(q['other_bodies_fixed'],6054);self.assertTrue(q['all_addresses_fixed'])
