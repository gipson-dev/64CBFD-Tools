"""Owner lifetime descriptor: direct C, typed mixed arguments, packet and full image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_owner_duration_descriptor_match as source
from tools.tests import game_owner_duration_descriptor_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class OwnerDurationDescriptorTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_direct_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);raw,rs=source.checked_payload(*source.payload(obj));self.assertEqual((raw,rs),source.payload(self.out/'original-func_151AE7B0.o'))
  for at in range(224):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
  for data,bindings,kw in ((raw[:-4],rs,{}),(raw+b'\0'*4,rs,{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,rs,dict(owner='foreign')),(raw,rs,dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.receipt['fresh_C']=dict(words=56,bindings=4,guards=0,direct_C_exact=True,fingerprint_rejections=229)
 def test_02_guest_callers_helpers_and_compiled_controls(self):
  oracle.o=self.out;expected=json.loads((self.out/'private-integration-v9.json').read_text())
  for name,fn,want in [('guest',oracle.guest_suite,json.loads((self.out/'private-guest-v7.json').read_text())),('caller',oracle.caller_suite,expected['caller']),('controls',oracle.compiled_controls,expected['controls']),('providers',oracle.provider_suite,expected['providers'])]:
   value=fn();self.assertEqual(value,want);self.receipt[name]=value
 def test_03_native32_UBSan_and_eighteen_controls(self):
  (self.fresh/'selected-semantic-input.c').write_bytes((self.out/'selected-semantic-input.c').read_bytes());oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-integration-v9.json').read_text())['native']);self.receipt['native']=result
 def test_04_retail_frame_homes_and_descriptor_layout(self):
  raw,rs=source.payload(self.out/'selected-final.o');w=struct.unpack('>56I',raw);self.assertEqual(w[:7],(0x27BDFFB0,0xAFA50054,0x00802825,0xAFBF0014,0xAFA40050,0xAFA60058,0xAFA7005C));self.assertIn(0x87A2005A,w);self.assertIn(0x93A6005F,w);self.assertIn(0x8FA70060,w);self.assertIn(0x27A4001C,w);self.assertEqual(w[-4:],(0x8FBF0014,0x27BD0050,0x03E00008,0));self.assertEqual(rs,source.BINDINGS)
  old='    if (duration != 0) {\n        descriptor.duration = duration;\n        descriptor.flags = 6;\n    } else {\n        descriptor.duration = 300;\n    }';new='    descriptor.duration = duration != 0 ? duration : 300;\n    if (duration != 0) descriptor.flags = 6;';self.assertIn(old,source.SELECTED)
  obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED.replace(old,new),'conditional-duration-control');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(obj))
  self.receipt['frame']=dict(bytes=80,RA_offset=20,descriptor_offset=28,incoming_homes=[80,84,88,92],fifth_word=96,body_words=56,alignment_words=0,ABI='void*(u8*,f32,s16,u8,s32)',equivalent_conditional_duration_rejected=True)
 def test_05_zero_guards_and_inherited_manifest(self):
  self.assertEqual(source.NEW_GUARDS,[]);self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),self.values['conker/retail_word_patches.us.csv']);self.assertEqual((self.out/'proposed-guards.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv']);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected-final.o')),source.payload(self.out/'selected-final.o'));self.receipt['guards']=dict(new_rows=0,inherited_CSV_bytes_unchanged=True,raw_compiler_words_exact=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),32);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual((self.out/'make-shadow/src/game/generated_1D92F0.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_1D92F0.c.o.compact'),33);self.receipt['owner']=dict(neighbors=32,actual_Make_commands=5,diagnostics=0,profile='O2/g3')
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),168);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=168,code_bytes=167,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
