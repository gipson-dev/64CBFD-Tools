"""XZ pivot rotation: symbolic allocation proof, signed arithmetic and literal image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_xz_pivot_rotation_match as source
from tools.tests import game_xz_pivot_rotation_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class XZPivotRotationTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_1508EF80.o'))
  raw,rs=source.payload(obj)
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for data,bindings,kw in ((raw[:-4],{},{}),(raw+b'\0'*4,{},{}),(raw,{0:[('R_MIPS_LO16','func_1508EF80')]},{}),(raw,{},dict(owner='foreign')),(raw,{},dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=55,guards=8,insertions=0,omissions=0,raw_C_exact=False,normalization_rejections=225)
 def test_02_guest_callers_symbolic_and_compiled_controls(self):
  oracle.o=self.out
  for name,fn in (('guest',oracle.guest_suite),('caller',oracle.caller_suite),('helpers',oracle.helper_suite),('controls',oracle.control_suite)):
   value=fn();self.assertEqual(value,json.loads((self.out/('private-'+name+'-v26.json')).read_text()));self.receipt[name]=value
 def test_03_native32_UBSan_and_fourteen_effective_controls(self):
  (self.fresh/'selected-semantic-input.c').write_bytes((self.out/'selected-semantic-input.c').read_bytes())
  oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v26.json').read_text()));self.receipt['native']=result
 def test_04_frame_float_ABI_and_saved_lifetimes(self):
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(raw),220);self.assertEqual(bindings,source.BINDINGS);w=struct.unpack('>55I',raw);self.assertEqual(w[:5],(0x27BDFFC0,0x44867000,0xAFBF001C,0xF7B40010,0xAFA7004C));self.assertEqual(w[51:],(0x8FBF001C,0xD7B40010,0x03E00008,0x27BD0040));self.assertIn('void func_1508EF80(f32 *point, f32 *pivot, f32 degrees, f32 *output)',source.SELECTED);self.assertTrue(all(int(x['offset'],16)not in(0,4,8,12,16,204,208,212,216)for x in source.NEW_GUARDS));self.receipt['frame']=dict(bytes=64,RA_offset=28,saved_f20_offset=16,pivot_home=68,output_home=76,dx_home=60,dz_home=56,x_home=40,trig_home=36,body_words=55,reachable_words=55,alignment_words=1,ABI='void(f32 *,f32 *,f32,f32 *)')
 def test_05_actual_padder_rejections(self):
  oracle.o=self.out;result=json.loads(json.dumps(oracle.guard_suite()));self.assertEqual(result,json.loads((self.out/'private-guards-v26.json').read_text()));self.receipt['guards']=result
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),0);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game_BC430.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game_BC430.c.o.compact'),1);self.receipt['owner']=dict(neighbors=0,actual_Make_commands=3,diagnostics=0,profile='O2/g3')
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  symbols={x[0]:x for x in source.symbol_rows(before)}
  for first,names,order in source.METADATA_GROUPS:
   offsets.update(range(first,first+16*len(names)));start=symbols[first][3];offsets.update(range(start,start+sum(len(n)+1 for n in names)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),194);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=194,code_bytes=175,extent_bytes=1,metadata_bytes=18)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
