"""Direct rotated-origin C: stack lifetimes, helper interfaces and full image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_rotated_origin_match as source
from tools.tests import game_rotated_origin_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class RotatedOriginTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_direct_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);raw,rs=source.checked_payload(*source.payload(obj));self.assertEqual((raw,rs),source.payload(self.out/'original-func_150CEF60.o'))
  for at in range(224):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
  for data,bindings,kw in ((raw[:-4],rs,{}),(raw+b'\0'*4,rs,{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,rs,dict(owner='foreign')),(raw,rs,dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.receipt['fresh_C']=dict(words=56,bindings=9,guards=0,direct_C_exact=True,fingerprint_rejections=229)
 def test_02_guest_callers_and_compiled_controls(self):
  oracle.o=self.out
  for name,fn in (('guest',oracle.guest_suite),('caller',oracle.caller_suite),('controls',oracle.compiled_controls),('helpers',oracle.provider_suite)):
   value=fn();self.assertEqual(value,json.loads((self.out/('private-'+name+'-v14.json')).read_text()));self.receipt[name]=value
 def test_03_native32_UBSan_and_sixteen_controls(self):
  (self.fresh/'selected-semantic-input.c').write_bytes((self.out/'selected-semantic-input.c').read_bytes());oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v14.json').read_text()));self.receipt['native']=result
 def test_04_retail_frame_and_argument_homes(self):
  raw,rs=source.payload(self.out/'selected-final.o');w=struct.unpack('>56I',raw);self.assertEqual(w[:3],(0x27BDFFC0,0xAFBF0014,0xAFA40040));self.assertEqual((w[10],w[11],w[13],w[23]),(0xE7AC0038,0xC7AC0038,0xE7A0001C,0xC7AE001C));self.assertEqual(w[-4:],(0x8FBF0014,0x27BD0040,0x03E00008,0));self.assertEqual(rs,source.BINDINGS)
  opening='    f32 second;\n    f32 radians;\n    f32 originX, originY, pointX, pointY, dx, dy;\n    f32 first;'
  replacement='    f32 radians, first, second;\n    f32 originX, originY, pointX, pointY, dx, dy;';self.assertIn(opening,source.SELECTED)
  obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED.replace(opening,replacement),'wrong-frame');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(obj))
  self.receipt['frame']=dict(bytes=64,RA_offset=20,incoming_unused_home=64,radians_home=56,first_result_home=28,saved_S_registers=0,body_words=56,alignment_words=0,ABI='void(s32)',equivalent_wrong_frame_source_rejected=True)
 def test_05_zero_guards_and_inherited_manifest(self):
  self.assertEqual(source.NEW_GUARDS,[]);self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),self.values['conker/retail_word_patches.us.csv']);self.assertEqual((self.out/'proposed-guards.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv']);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected-final.o')),source.payload(self.out/'selected-final.o'));self.receipt['guards']=dict(new_rows=0,inherited_CSV_bytes_unchanged=True,raw_compiler_words_exact=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),2);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game/generated_FC410.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_FC410.c.o.compact'),3);self.receipt['owner']=dict(neighbors=2,actual_Make_commands=3,diagnostics=0,profile='O2/g3')
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),217);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=217,code_bytes=184,extent_bytes=1,metadata_bytes=32)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
