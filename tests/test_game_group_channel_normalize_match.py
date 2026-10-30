"""Group channel normalization: live callbacks, five guards, owner and image gates."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_group_channel_normalize_match as source
from tools.tests import game_group_channel_normalize_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class GroupChannelNormalizeTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def assemble(self,p):subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_1501E73C.o'))
  bad=source.SELECTED.replace('*(u16 *)record == 2','*(u16 *)record == 3');self.assertNotEqual(bad,source.SELECTED);control,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+bad,'wrong-type');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(control))
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=56,raw_C_byte_exact=False,guards=5,insertions=0,omissions=0,frame=40,bindings=6,source_control=True)
 def test_02_guest_original_helpers_callers_and_controls(self):
  oracle.o=self.out;results=dict(guest=oracle.run_suite(),helpers=oracle.helper_suite(),caller=oracle.caller_suite(),compiled_controls=oracle.compiled_controls(source.HEADERS+source.SELECTED))
  for name,value in results.items():self.assertEqual(value,json.loads((self.out/('private-'+('controls'if name=='compiled_controls'else name)+'-v23.json')).read_text()))
  self.receipt.update(results)
 def test_03_native32_UBSan_and_thirteen_controls(self):
  oracle.o=self.fresh
  try:result=oracle.run_native(source.HEADERS+source.SELECTED)
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v23.json').read_text()));self.assertEqual(result['cases'],328192);self.assertEqual(result['negative_controls'],13);self.receipt['native']=result
 def test_04_frame_and_void_group_ABI(self):
  raw,bindings=source.payload(self.out/'selected-final.o');w=struct.unpack('>56I',raw);self.assertEqual(w[:6],(0x27BDFFD8,0xAFBF0024,0xAFB30020,0xAFB2001C,0xAFB10018,0xAFB00014));self.assertEqual(w[-7:],(0x8FBF0024,0x8FB00014,0x8FB10018,0x8FB2001C,0x8FB30020,0x03E00008,0x27BD0028));self.assertEqual(len(source.NEW_GUARDS),5)
  self.assertIn('void func_1501E73C(s32 group)',source.SELECTED);self.assertIn('goto advance',source.SELECTED);self.assertIn('offset < D_800C363A[group] * 8',source.SELECTED);self.assertNotIn('expired',source.SELECTED)
  self.receipt['frame']=dict(bytes=40,RA_offset=36,S0_offset=20,S1_offset=24,S2_offset=28,S3_offset=32,body_words=56,reachable_words=56,alignment_words=0,ABI='void(s32)')
 def test_05_guard_rejections_scope_and_closed_schedule(self):
  oracle.o=self.out;result=oracle.guard_suite();self.assertEqual(result,json.loads((self.out/'private-guards-v23.json').read_text()));self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected-final.o')),source.payload(self.out/'original-func_1501E73C.o'));self.receipt['guards']=result
 def test_06_complete_owner_and_actual_Make_evidence(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),56);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));self.assertEqual(self.assemble(p).read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game/generated_49D30.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_49D30.c.o.compact'),57);self.receipt['owner']=dict(neighbors=56,actual_Make_commands=3,diagnostics=0,no_unroll_profile=True)
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),166);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=166,code_bytes=165,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
