"""Closed angular-loop guards, semantic oracle, original callers and strict image."""
from pathlib import Path
import json,os,sys,struct,unittest
from tools.experiments import game_angular_velocity_approach_match as source
from tools.tests import game_angular_velocity_approach_oracle as oracle
import tools.pad_generated_object as pad
sys.modules.setdefault('pad_generated_object',pad)
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class AngularVelocityApproachTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  cls.object,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected')
  if diag:raise AssertionError(diag)
  cls.raw,cls.bindings=source.checked_payload(*source.payload(cls.object));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_closed_transformation_and_fail_closed_guards(self):
  self.assertEqual(len(self.raw),296);self.assertEqual(source.derive_guards(self.raw,self.bindings),source.NEW_GUARDS);self.assertEqual(len(source.NEW_GUARDS),14)
  for at in(0,0x34,0x48,0x118):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.derive_guards(self.raw,{})
  before=self.values['conker/retail_word_patches.us.csv'];after=source.proposed_guards(before);self.assertTrue(after.startswith(before));self.assertEqual(len(after.splitlines())-len(before.splitlines()),14)
  with self.assertRaises(ValueError):source.proposed_guards(after)
  bad=after.replace(b'0x034,0x00801825',b'0x034,0x00801824');self.assertNotEqual(bad,after);path=self.output/'public-bad-guards.csv';path.write_bytes(bad)
  with self.assertRaisesRegex(ValueError,'stale word patch'):pad.emit_padded_assembly(self.output/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=path)
 def test_owner_actual_make_and_pools(self):
  self.assertEqual(source.same_functions(self.output/'before-owner.o',self.output/'after-owner.o',(source.FUNCTION,)),83)
  self.assertEqual(source.same_functions(self.output/'before-padded.o',self.output/'qualified-padded.o',(source.FUNCTION,)),83)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game/generated_142560.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=0,after=0,removed=0));self.assertEqual(q['changed_bytes'],187);self.assertEqual(q['actual_Make_commands'],5)
 def test_guest_finite_extremes_global_aliases_and_fault_prefixes(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['rebases']),(4608,23040,3));self.assertTrue(q['all_72_reachable_words_executed']);self.assertTrue(q['unguarded_C_public_memory_and_saved_registers_equal']);self.assertEqual(q['global_alias_layouts'],3)
  q=self.runtime['faults'];self.assertEqual((q['prefixes'],q['executions']),(109,436));self.assertTrue(q['exact_programs_full_state_equal']);self.assertTrue(q['unguarded_C_fault_order_not_claimed'])
 def test_original_callback_installer_and_both_call_sites(self):
  q=self.runtime['callers'];self.assertEqual((q['cases'],q['executions']),(128,640));self.assertEqual(q['original_window_words'],[7,9]);self.assertTrue(q['both_original_JALR_sites_executed']);self.assertTrue(q['void_result_ignored'])
  q=self.runtime['installer'];self.assertEqual((q['original_words'],q['table_row'],q['callback_field']),(22,75,'0x38'));self.assertTrue(q['all_words_executed'])
  q=json.loads((self.output/'caller-census.json').read_text());self.assertEqual(q['aligned_ROM_pointer_literals'],[0x22DAD4]);self.assertFalse(q['aligned_ROM_JALs']);self.assertFalse(q['aligned_ROM_Js'])
 def test_native_profiles_canaries_and_effective_controls(self):
  self.assertEqual([q['profile'] for q in self.runtime['native']],['-O0','-O2','-O3'])
  for q in self.runtime['native']:self.assertEqual(q['cases'],2048);self.assertTrue(q['UBSan']);self.assertTrue(q['canaries']);self.assertTrue(q['all_eight_controls_effective']);self.assertEqual(len(q['controls']),8)
 def test_literal_entire_image_and_current_inputs(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(sum(a!=b for a,b in zip(before,actual)),187)
  for at in(0x100,source.elf_slot_offset(actual,source.ENTRY,source.SIZE)+4):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner(self.values[source.SOURCE].decode()))
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:source.audit(ROOT,self.output)
