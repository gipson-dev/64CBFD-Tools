"""Guard closure, real owner/Make, full guest ABI, dispatch and native controls."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_carried_actor_initializer_match as source
from tools.tests import game_carried_actor_initializer_oracle as oracle
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string,parse_object
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class CarriedActorInitializerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  cls.object,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected')
  if diag:raise AssertionError(diag)
  cls.raw,cls.bindings=source.checked_payload(*source.payload(cls.object));cls.runtime=oracle.qualify(ROOT,cls.output,source)
 def test_full_body_binding_pin_and_four_guard_fail_closed_checks(self):
  self.assertEqual(len(self.raw),212);self.assertEqual(len(source.NEW_GUARDS),4)
  bad=bytearray(self.raw);bad[0]^=1
  with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  import sys,tools.pad_generated_object as pad
  sys.modules.setdefault('pad_generated_object',pad)
  from tools.pad_c_object import emit_padded_assembly
  owner_object=self.output/'after-owner.o';original=owner_object.read_bytes();h=ELF_HEADER.unpack_from(original);headers=[SECTION_HEADER.unpack_from(original,h[6]+i*h[11])for i in range(h[12])];strings=original[headers[h[13]][4]:headers[h[13]][4]+headers[h[13]][5]]
  text=next(row for row in headers if read_c_string(strings,row[0])=='.text');start=parse_object(owner_object)[1][source.FUNCTION]['value']
  for offset,expected,replacement,reloc in source.NEW_GUARDS:
   data=bytearray(original);data[text[4]+start+offset]^=1;p=self.output/('stale-guard-%X.o'%offset);p.write_bytes(data)
   with self.assertRaisesRegex(ValueError,'stale word patch'):emit_padded_assembly(p,ROOT/source.LAYOUT,filename=source.OWNER,word_patches_path=self.output/'proposed-guards.csv')
  lines=(self.output/'proposed-guards.csv').read_text().splitlines();key='game_981E0,func_1507266C,0x4C,'
  line=next(v for v in lines if v.startswith(key));badline=line.replace('R_MIPS_LO16:D_800D1580','R_MIPS_HI16:D_800D1580',1);badguards=self.output/'stale-binding-guards.csv';badguards.write_text('\n'.join(badline if v==line else v for v in lines)+'\n')
  with self.assertRaises(ValueError):emit_padded_assembly(owner_object,ROOT/source.LAYOUT,filename=source.OWNER,word_patches_path=badguards)
 def test_owner_padding_actual_make_and_diagnostics(self):
  source.verify_prepared(self.output);self.assertEqual(source.same_functions(self.output/'before-owner.o',self.output/'after-owner.o',(source.FUNCTION,)),327)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'make-shadow/src/game_981E0.c.o').read_bytes(),(self.output/'qualified-padded.o').read_bytes())
  q=json.loads((self.output/'preparation.json').read_text());self.assertEqual(q['diagnostics'],dict(before=36,after=36,removed=0));self.assertEqual(q['changed_bytes'],0)
 def test_gate_command_snapshot_live_aliases_and_access_prefixes(self):
  q=self.runtime['guest'];self.assertEqual((q['cases'],q['executions'],q['rebases']),(4992,19968,3));self.assertTrue(q['all_53_words_executed']);self.assertTrue(q['guarded_machine_states_and_traces_equal']);self.assertTrue(q['raw_C_public_memory_calls_and_traces_equal']);self.assertTrue(q['owner_command_current_and_mode_aliases'])
  f=self.runtime['faults'];self.assertGreater(f['prefixes'],20);self.assertEqual(f['executions'],f['prefixes']*3);self.assertTrue(f['all_machine_states_and_traces_equal'])
 def test_original_notification_and_indirect_dispatch(self):
  q=self.runtime['connected'];self.assertEqual((q['cases'],q['executions'],q['complete_original_notification_words']),(216,864,18));self.assertGreater(q['nested_paths'],0)
  q=self.runtime['callers'];self.assertEqual((q['callback_slot'],q['cases'],q['executions']),(96,24,384));self.assertEqual(q['return_poisons'],4);self.assertTrue(q['return_ignored']);self.assertFalse(q['full_dispatcher_reachability_claimed'])
 def test_native_profiles_and_eight_effective_controls(self):
  self.assertEqual(len(self.runtime['native']),3)
  for q in self.runtime['native']:
   self.assertEqual(q['cases'],1704);self.assertTrue(q['UBSan']);self.assertTrue(q['background_canaries_preserved']);self.assertTrue(q['all_eight_controls_effective']);self.assertEqual(len(q['controls']),8)
 def test_literal_entire_image_inventory_and_current_inputs(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(actual,before)
  for at in (0x100,source.elf_slot_offset(actual,source.ENTRY,source.SIZE)+4):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.check_inputs(ROOT,self.output,self.installed)
  if self.installed:source.audit(ROOT,self.output)
