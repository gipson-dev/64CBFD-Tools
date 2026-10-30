"""Direct effect-motion C: exact words, ABI, access prefixes and full image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_effect_motion_limit_match as source
from tools.tests import game_effect_motion_limit_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class EffectMotionLimitTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_direct_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);raw,rs=source.checked_payload(*source.payload(obj));self.assertEqual((raw,rs),source.payload(self.out/'original-func_150B36AC.o'))
  for at in range(224):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
  for data,bindings,kw in ((raw[:-4],rs,{}),(raw+b'\0'*4,rs,{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,rs,dict(owner='foreign')),(raw,rs,dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.receipt['fresh_C']=dict(words=56,bindings=0,guards=0,direct_C_exact=True,fingerprint_rejections=229)
 def test_02_guest_callers_and_compiled_controls(self):
  oracle.o=self.out
  for name,fn in (('guest',oracle.guest_suite),('caller',oracle.caller_suite),('controls',oracle.compiled_controls)):
   value=fn();self.assertEqual(value,json.loads((self.out/('private-'+name+'-v13.json')).read_text()));self.receipt[name]=value
 def test_03_native32_UBSan_and_fourteen_controls(self):
  (self.fresh/'selected-semantic-input.c').write_bytes((self.out/'selected-semantic-input.c').read_bytes());oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v13.json').read_text()));self.receipt['native']=result
 def test_04_leaf_homes_and_store_schedule(self):
  raw,rs=source.payload(self.out/'selected-final.o');w=struct.unpack('>56I',raw);self.assertEqual(w[:3],(0xAFA50004,0xAFA60008,0xAFA7000C));self.assertEqual(w[-2:],(0x03E00008,0));self.assertFalse(rs);self.assertIn('f32 offset, void *unused6',source.SELECTED)
  for index in(21,23,25,27):self.assertEqual((w[index]>>26,w[index]>>21&31,w[index]&65535),(43,4,0x60))
  combined=source.SELECTED.replace('= *(u32 *)(record + 0x60) & ~7u;','&= ~0x6Fu;')
  for mask in('8','0x40','0x20'):combined=combined.replace('        *(u32 *)(record + 0x60) = *(u32 *)(record + 0x60) & ~'+mask+'u;\n','')
  obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+combined,'collapsed-store-control');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(obj))
  self.receipt['frame']=dict(bytes=0,homes=[4,8,12],body_words=56,guards=0,fifth_argument_float=True,sixth_pointer_unused=True,four_separate_flag_stores=True,equivalent_shape_control_rejected=True)
 def test_05_zero_guards_and_inherited_manifest(self):
  self.assertEqual(source.NEW_GUARDS,[]);self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),self.values['conker/retail_word_patches.us.csv']);self.assertEqual((self.out/'proposed-guards.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv']);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected-final.o')),source.payload(self.out/'selected-final.o'));self.receipt['guards']=dict(new_rows=0,inherited_CSV_bytes_unchanged=True,raw_compiler_words_exact=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),5);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game/generated_DFBF0.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_DFBF0.c.o.compact'),6);self.receipt['owner']=dict(neighbors=5,actual_Make_commands=3,diagnostics=0,profile='O2/g3')
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),178);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=178,code_bytes=177,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
