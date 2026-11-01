"""Direct command dispatch, generated/retail table identity and complete image gates."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_menu_command_dispatch_match as source
from tools.tests import game_menu_command_dispatch_oracle as oracle
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class MenuCommandDispatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  cls.object,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected')
  if diag:raise AssertionError(diag)
  cls.raw,cls.bindings=source.checked_payload(*source.payload(cls.object));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_direct_body_and_complete_jump_table_with_corruption_controls(self):
  self.assertEqual(len(self.raw),208);self.assertEqual(source.NEW_GUARDS,[])
  bad=bytearray(self.raw);bad[0]^=1
  with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  old,new=self.output/'before-owner.o',self.output/'after-owner.o';q=source.check_owner_pools(old,new);self.assertEqual(q['entries'],10)
  data=new.read_bytes();h=ELF_HEADER.unpack_from(data);sections=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11])for i in range(h[12])];strings=data[sections[h[13]][4]:sections[h[13]][4]+sections[h[13]][5]];pool=next(v for v in sections if read_c_string(strings,v[0])=='.rodata')
  for entry in range(10):
   bad=bytearray(data);bad[pool[4]+4*entry+3]^=1;p=self.output/('bad-jump-table-%d.o'%entry);p.write_bytes(bad)
   with self.assertRaises(ValueError):source.check_owner_pools(old,p)
  before=self.values['conker/Makefile'].decode()
  with self.assertRaises(ValueError):source.proposed_makefile(source.proposed_makefile(before))
  with self.assertRaises(ValueError):source.proposed_makefile(before.replace('OPT_FLAGS := -O2 -g3 -Wo,-loopunroll,0','OPT_FLAGS := -O1'))
 def test_owner_actual_make_and_zero_warnings(self):
  self.assertEqual(source.same_functions(self.output/'before-owner.o',self.output/'after-owner.o',(source.FUNCTION,)),20)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game/generated_E4070.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=0,after=0,removed=0));self.assertEqual(q['changed_bytes'],130);self.assertEqual(q['actual_Make_commands'],3)
 def test_all_selectors_state_changes_and_fault_prefixes(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['rebases']),(8192,32768,3));self.assertTrue(q['all_52_words_executed']);self.assertTrue(q['all_four_programs_full_state_and_trace_equal']);self.assertTrue(q['helper_state_mutation_does_not_redispatch'])
  q=self.runtime['faults'];self.assertEqual((q['prefixes'],q['executions']),(19,76))
 def test_original_helpers_and_frame_caller(self):
  q=self.runtime['connected'];self.assertEqual((q['cases'],q['executions']),(48,192));self.assertEqual(q['original_helper_words'],[17,12,12]);self.assertTrue(q['all_41_helper_words_executed'])
  q=self.runtime['callers'];self.assertEqual((q['cases'],q['executions'],q['complete_original_caller_words']),(64,1024,43));self.assertEqual(q['frame_callback_slot'],5);self.assertTrue(q['void_result_ignored'])
 def test_native_profiles_and_effective_controls(self):
  self.assertEqual(len(self.runtime['native']),3)
  for q in self.runtime['native']:self.assertEqual(q['cases'],4096);self.assertTrue(q['UBSan']);self.assertTrue(q['canaries']);self.assertTrue(q['all_eight_controls_effective']);self.assertEqual(len(q['controls']),8)
 def test_literal_image_current_inputs_and_preserved_guard_manifest(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),130)
  self.assertEqual(source.proposed_guards(self.values['conker/retail_word_patches.us.csv']),self.values['conker/retail_word_patches.us.csv'])
  for at in(0x100,source.elf_slot_offset(actual,source.ENTRY,source.SIZE)+4):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:source.audit(ROOT,self.output)
