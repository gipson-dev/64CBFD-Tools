"""Resource status bit clear: full callback words, live coordinates, float ABI and named metadata."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_resource_status_bit_clear_match as source
from tools.tests import game_resource_status_bit_clear_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=Path(__file__).resolve().parents[2]
class ResourceStatusBitClearTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def assemble(self,p):subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_150A2864.o'))
  bad=source.SELECTED.replace('0xFFF','0x7FF');self.assertNotEqual(bad,source.SELECTED);control,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+bad,'wrong-identity-mask');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(control))
  self.receipt['fresh_C']=dict(words=55,raw_C_byte_exact=False,guards=10,insertions=0,omissions=0,frame=64,bindings=9,source_control=True)
 def test_02_guest_live_resources_counts_and_callers(self):
  oracle.o=self.out;result=oracle.run_suite();self.assertEqual(result,json.loads((self.out/'private-guest-v11.json').read_text()));self.receipt['guest']=result
 def test_03_native32_UBSan_and_nine_controls(self):
  oracle.o=self.fresh
  try:result=oracle.run_native(source.HEADERS+source.SELECTED)
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v11.json').read_text()));self.assertEqual(result['cases'],4960);self.assertEqual(result['negative_controls'],9);self.receipt['native']=result
 def test_04_frame_saved_registers_and_unreachable_word(self):
  raw,bindings=source.payload(self.out/'selected-final.o');w=struct.unpack('>55I',raw);self.assertEqual(w[0],0x27BDFFC0);self.assertEqual(w[-1],0x27BD0040);self.assertEqual(len(source.NEW_GUARDS),10)
  self.receipt['frame']=dict(bytes=64,RA_offset=36,saved_register_offsets=[32,28,24],outgoing_home_extent=16,shift_count_offsets=[40,44],incoming_homes=[],reachable_words=55,slot_words=55,alignment_words=0)
 def test_05_raw_binding_controls_and_guard_history(self):
  raw,bindings=source.payload(self.out/'selected-final.o');controls=0
  for i in range(len(raw)):
   changed=bytearray(raw);changed[i]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(changed),bindings)
   controls+=1
  for at in bindings:
   with self.assertRaises(ValueError):source.checked_payload(raw,{**bindings,at:[('R_MIPS_26','wrong_symbol')]})
   controls+=1
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());guard_controls=0
  import csv,io
  original=list(csv.DictReader(io.StringIO((self.out/'proposed-guards.csv').read_text())));keys=list(original[0])
  for row in source.NEW_GUARDS:
   for field in ('expected','expected_relocations'):
    changed=[dict(x)for x in original];item=next(x for x in changed if x['function']==source.FUNCTION and x['offset']==row['offset']);item[field]='0x%08X'%(int(row[field],0)^1)if field=='expected'else'R_MIPS_26:wrong_symbol';stream=io.StringIO();writer=csv.DictWriter(stream,keys);writer.writeheader();writer.writerows(changed);p=self.fresh/('bad-guard-'+str(guard_controls)+'.csv');p.write_text(stream.getvalue())
    with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=p,filename=source.OWNER,rodata_symbol=source.RODATA_SYMBOL)
    guard_controls+=1
  self.receipt['controls']=dict(raw_binding_controls=controls,new_guards=10,guard_manifest_prefix_preserved=True,guard_preimage_controls=guard_controls)
 def test_06_complete_owner_and_actual_Make_evidence(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_150A2864.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),27);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER,rodata_symbol=source.RODATA_SYMBOL));self.assertEqual(self.assemble(p).read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual((self.out/'make-shadow/src/game/generated_CDE80.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.receipt['owner']=dict(neighbors=27,actual_Make_commands=5,diagnostics=0)
 def test_07_literal_image_and_named_metadata_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  positions={p:(n,f,s)for p,n,f,s in source.symbol_rows(before)}
  for first,names,order in source.METADATA_GROUPS:
   offsets.update(range(first,first+16*len(names)));start=positions[first][2];offsets.update(range(start,start+sum(len(n)+1 for n in names)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=182,code_bytes=181,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
