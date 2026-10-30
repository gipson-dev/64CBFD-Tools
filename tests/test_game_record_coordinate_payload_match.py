"""Selector coordinate packet: ABI, literal owner/image, semantic and callback checks."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_record_coordinate_payload_match as source
from tools.tests import game_record_coordinate_payload_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class RecordCoordinatePayloadTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def assemble(self,p):subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'original-func_1500A7E8.o'))
  bad=source.SELECTED.replace('command - 0x50','0');self.assertNotEqual(bad,source.SELECTED);control,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+bad,'wrong-selector');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(control))
  self.receipt['fresh_C']=dict(words=56,raw_C_byte_exact=True,guards=0,insertions=0,omissions=0,frame=80,bindings=5,source_control=True)
 def test_02_guest_callbacks_helpers_and_controls(self):
  oracle.o=self.out;g=oracle.run_suite();i=oracle.integration_suite();c=oracle.compiled_controls(source.HEADERS+source.SELECTED)
  for name,value in(('guest',g),('integration',i),('controls',c)):self.assertEqual(value,json.loads((self.out/('private-'+name+'-v13.json')).read_text()))
  self.assertEqual((i['lookup_words'],i['lookup_covered_words']),(28,28));self.assertEqual((i['factory_words'],i['factory_covered_words']),(32,32));self.assertEqual(c['count'],14);self.receipt.update(guest=g,integration=i,compiled_controls=c)
 def test_03_native32_UBSan_and_fourteen_controls(self):
  oracle.o=self.fresh
  try:result=oracle.run_native(source.HEADERS+source.SELECTED)
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v13.json').read_text()));self.assertEqual(result['cases'],147456);self.assertEqual(result['negative_controls'],14);self.receipt['native']=result
 def test_04_frame_packet_and_source_ABI(self):
  raw,bindings=source.payload(self.out/'selected-final.o');w=struct.unpack('>56I',raw);self.assertEqual(w[:4],(0x27BDFFB0,0xAFBF001C,0xAFA40050,0x27A20024));self.assertEqual(w[-4:],(0x8FBF001C,0x27BD0050,0x03E00008,0));self.assertEqual(w[14],0xAFA20038);self.assertEqual(w[50],0x0c000000);self.assertFalse(source.NEW_GUARDS)
  self.assertIn('void func_1500A7E8(struct226 *actor, s32 command)',source.SELECTED);self.assertLess(source.SELECTED.index('struct225 *effect;'),source.SELECTED.index('EffectPointIds36680 ids'));self.assertLess(source.SELECTED.index('payload.unk14 ='),source.SELECTED.index('header.unk0 ='))
  self.receipt['frame']=dict(bytes=80,RA_offset=28,actor_home=80,selector_offset=36,selector_bytes=6,payload_offset=48,payload_bytes=24,record_offset=56,header_offset=72,header_bytes=6,body_words=56,reachable_words=56,alignment_words=0)
 def test_05_raw_binding_controls_and_guard_history(self):
  raw,bindings=source.payload(self.out/'selected-final.o');controls=0
  for i in range(len(raw)):
   changed=bytearray(raw);changed[i]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(changed),bindings)
   controls+=1
  for at in bindings:
   with self.assertRaises(ValueError):source.checked_payload(raw,{**bindings,at:[('R_MIPS_26','wrong_symbol')]})
   controls+=1
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),self.values['conker/retail_word_patches.us.csv']);self.receipt['controls']=dict(raw_binding_controls=controls,new_guards=0,guard_manifest_unchanged=True)
 def test_06_complete_owner_and_actual_Make_evidence(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');self.assertEqual(source.check_owner_diagnostics(diag),6);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'original-func_1500A7E8.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),81);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.LAYOUT,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv',rodata_symbol=source.RODATA_SYMBOL));self.assertEqual(self.assemble(p).read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual((self.out/'make-shadow/src/game_36680.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.receipt['owner']=dict(neighbors=81,actual_Make_commands=5,inherited_diagnostics=6,new_diagnostics=0)
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),173);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=173,code_bytes=172,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
