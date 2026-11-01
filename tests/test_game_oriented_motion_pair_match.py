"""Direct oriented-motion pair, corrected pointer ABI and complete image gates."""
from pathlib import Path
import json,os,sys,unittest
from tools.experiments import game_oriented_motion_pair_match as source
from tools.tests import game_oriented_motion_pair_oracle as oracle
import tools.pad_generated_object as pad
sys.modules.setdefault('pad_generated_object',pad)
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class OrientedMotionPairTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  cls.object,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED+'\n'+source.CALLER_SELECTED,'public-fresh-selected')
  if diag:raise AssertionError(diag)
  cls.raw,cls.bindings=source.checked_payload(*source.payload(cls.object));cls.caller,cls.caller_bindings=source.checked_caller_payload(*source.function_payload(cls.object,source.CALLER));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_direct_pair_and_fail_closed_payloads(self):
  self.assertEqual((len(self.raw),len(self.caller)),(208,140));self.assertEqual(source.NEW_GUARDS,[])
  for raw,bindings,check in((self.raw,self.bindings,source.checked_payload),(self.caller,self.caller_bindings,source.checked_caller_payload)):
   bad=bytearray(raw);bad[0]^=1
   with self.assertRaises(ValueError):check(bytes(bad),bindings)
   with self.assertRaises(ValueError):check(raw,{})
  before=self.values[source.SOURCE].decode()
  with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner(before))
 def test_complete_owner_actual_make_and_legacy_guard_rejection(self):
  self.assertEqual(source.same_functions(self.output/'before-owner.o',self.output/'after-owner.o',(source.FUNCTION,source.CALLER)),82)
  self.assertEqual(source.same_functions(self.output/'before-padded.o',self.output/'qualified-padded.o',(source.FUNCTION,)),83)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game/generated_142560.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=0,after=0,removed=0));self.assertEqual(q['changed_bytes'],214);self.assertEqual(q['actual_Make_commands'],5)
  before=self.values['conker/retail_word_patches.us.csv'];old=self.output/'public-old-guards.csv';old.write_bytes(before)
  with self.assertRaisesRegex(ValueError,'stale word patch'):pad.emit_padded_assembly(self.output/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=old)
  self.assertEqual(before.splitlines().__len__()-source.proposed_guards(before).splitlines().__len__(),1)
  with self.assertRaises(ValueError):source.proposed_guards(source.proposed_guards(before))
 def test_guest_alias_reload_snapshot_and_fault_prefixes(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['rebases']),(3072,12288,3));self.assertTrue(q['all_52_root_and_35_caller_words_executed']);self.assertTrue(q['all_four_programs_full_state_and_trace_equal']);self.assertEqual(q['alias_layouts'],4);self.assertTrue(q['wrapper_precall_snapshot_and_live_type_gate'])
  q=self.runtime['faults'];self.assertEqual((q['prefixes'],q['executions']),(116,464));self.assertTrue(q['all_machine_states_equal'])
 def test_original_caller_trig_and_pointer_census(self):
  q=self.runtime['connected'];self.assertEqual((q['cases'],q['executions'],q['original_trig_span_words'],q['original_trig_words_executed']),(1024,4096,76,73));self.assertTrue(q['retail_code_and_12_coefficient_words_pinned']);self.assertTrue(q['full_FCSR_and_NaN_payloads_not_modeled'])
  q=json.loads((self.output/'caller-census.json').read_text());self.assertEqual(q[source.FUNCTION]['aligned_ROM_JALs'],[0x1433AC]);self.assertEqual(q[source.CALLER]['aligned_ROM_pointer_literals'],[0x22D790]);self.assertEqual(q['callback_byte_offset'],0x40)
 def test_native_profiles_canaries_and_effective_controls(self):
  self.assertEqual([q['profile'] for q in self.runtime['native']],['-O0','-O2','-O3'])
  for q in self.runtime['native']:self.assertEqual(q['cases'],1024);self.assertTrue(q['UBSan']);self.assertTrue(q['canaries']);self.assertTrue(q['all_eight_controls_effective']);self.assertEqual(len(q['controls']),8)
 def test_literal_entire_image_and_current_inputs(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),214)
  for at in(0x100,source.elf_slot_offset(actual,source.ENTRY,source.SIZE)+4,0x2CE6D9):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:source.audit(ROOT,self.output)
