"""Source ABI, closed guards, owner/Make, helpers, native and literal image gates."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_node_chain_release_match as source
from tools.tests import game_node_chain_release_oracle as oracle
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string,parse_object
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class NodeChainReleaseTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  cls.object,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected')
  if diag:raise AssertionError(diag)
  cls.raw,cls.bindings=source.checked_payload(*source.payload(cls.object));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_raw_pin_and_three_fail_closed_backedge_guards(self):
  self.assertEqual(len(self.raw),196);self.assertEqual(len(source.NEW_GUARDS),3)
  bad=bytearray(self.raw);bad[0]^=1
  with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  import sys,tools.pad_generated_object as pad
  sys.modules.setdefault('pad_generated_object',pad)
  from tools.pad_c_object import emit_padded_assembly
  owner=self.output/'after-owner.o';data=owner.read_bytes();h=ELF_HEADER.unpack_from(data);headers=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11])for i in range(h[12])];strings=data[headers[h[13]][4]:headers[h[13]][4]+headers[h[13]][5]]
  text=next(row for row in headers if read_c_string(strings,row[0])=='.text');start=parse_object(owner)[1][source.FUNCTION]['value']
  for offset,expected,replacement,reloc in source.NEW_GUARDS:
   bad=bytearray(data);bad[text[4]+start+offset]^=1;p=self.output/('stale-guard-%X.o'%offset);p.write_bytes(bad)
   with self.assertRaisesRegex(ValueError,'stale word patch'):emit_padded_assembly(p,ROOT/source.LAYOUT,filename=source.OWNER,word_patches_path=self.output/'proposed-guards.csv')
 def test_owner_actual_make_and_exact_warning_removal(self):
  self.assertEqual(source.same_functions(self.output/'before-owner.o',self.output/'after-owner.o',(source.FUNCTION,)),18)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game_1FFF60.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=14,after=12,removed_pointer_integer_argument_warnings=2));self.assertEqual(q['changed_bytes'],193)
 def test_guest_live_links_callback_tables_and_faults(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['rebases']),(1120,4480,3));self.assertTrue(q['all_49_words_executed']);self.assertTrue(q['guarded_full_state_and_trace_equal']);self.assertTrue(q['raw_C_public_memory_calls_and_traces_equal']);self.assertTrue(q['all_owner_selector_bytes'])
  self.assertEqual(self.runtime['faults']['prefixes'],66)
 def test_original_wrappers_and_generic_release(self):
  q=self.runtime['callers'];self.assertEqual((q['cases'],q['executions'],q['complete_original_wrappers']),(36,576,2));self.assertTrue(q['void_return_ignored'])
  q=self.runtime['connected'];self.assertEqual((q['cases'],q['executions'],q['complete_original_generic_release_words']),(96,384,28));self.assertTrue(q['all_28_helper_words_executed'])
 def test_native_profiles_and_effective_controls(self):
  self.assertEqual(len(self.runtime['native']),3)
  for q in self.runtime['native']:self.assertEqual(q['cases'],1536);self.assertTrue(q['UBSan']);self.assertTrue(q['canaries']);self.assertTrue(q['all_eight_controls_effective']);self.assertEqual(len(q['controls']),8)
 def test_literal_whole_image_inventory_and_current_inputs(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),193)
  for at in(0x100,source.elf_slot_offset(actual,source.ENTRY,source.SIZE)+4):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:source.audit(ROOT,self.output)
