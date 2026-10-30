"""Resource bitmap: ordinary C owner and checked independent schedule, guest/native ABI and image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_resource_bitmap_match as source
from tools.tests import game_resource_bitmap_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class ResourceBitmapTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_15016588.o'))
  raw,rs=source.payload(obj)
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for data,bindings,kw in((raw[:-4],{},{}),(raw+b'\0'*4,{},{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,{},dict(owner='foreign')),(raw,{},dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=55,guards=2,insertions=0,omissions=0,raw_C_exact=False,normalization_rejections=225)
 def test_02_guest_original_helper_callers_and_controls(self):
  oracle.o=self.out;expected=json.loads((self.out/'private-semantics-v10.json').read_text());controls=json.loads((self.out/'private-native-v11.json').read_text())['compiled_controls']
  for name in('guest_suite','caller_suite','consumer_suite'):
   result=getattr(oracle,name)();self.assertEqual(result,expected[name]);self.receipt[name]=result
  result=oracle.compiled_controls();self.assertEqual(result,controls);self.receipt['compiled_controls']=result
 def test_03_native32_UBSan_and_fifteen_controls(self):
  oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v11.json').read_text())['native_suite']);self.receipt['native']=result
 def test_04_retail_frame_and_assembly_consumer_ABI(self):
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(raw),220);self.assertEqual(bindings,source.BINDINGS);w=struct.unpack('>55I',raw)
  self.assertEqual(w[0],0x27BDFFB0);self.assertEqual(w[17],0x26B50000);self.assertEqual(w[16],0x00008025);self.assertEqual(w[20],0x8FB20044);self.assertEqual(w[24],0x24120001);self.assertEqual(w[-2:],(0x03E00008,0x27BD0050))
  self.assertIn('index = 0;',source.SELECTED);self.assertIn('if ((index & 7) == 0)',source.SELECTED);self.assertIn('mask = 1;',source.SELECTED);self.assertIn('u32 func_1502B020(u32 *, u32, ...);',source.HEADERS)
  self.assertIn('void func_15016588(void);',self.values['conker/src/game/entrypoint.c'].decode());self.assertIn('u32 func_1502B020(u32 *size, u32 depth, ...)',self.values['conker/src/game_57FA0.c'].decode())
  self.receipt['frame']=dict(bytes=80,RA_offset=60,saved_registers=list(range(16,23)),body_words=55,slot_words=58,alignment_words=3,size_offset=64,mask_home=68,first_mask_read_dominated_by_index0_reset=True,variadic_provider_signature_compatible=True,entrypoint_void_signature_compatible=True,shared_headers_unchanged=True)
 def test_05_closed_schedule_and_actual_padder_controls(self):
  oracle.o=self.out;result=oracle.guard_suite();self.assertEqual(result,json.loads((self.out/'private-semantics-v10.json').read_text())['guard_suite']);self.receipt['guards']=result
  self.assertEqual(len(source.NEW_GUARDS),2);self.assertTrue((self.out/'proposed-guards.csv').read_bytes().startswith(self.values['conker/retail_word_patches.us.csv']))
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),1);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game_439B0.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game_439B0.c.o.compact'),2);self.receipt['owner']=dict(neighbors=1,actual_Make_commands=3,diagnostics=0,profile='O2/g3',ordinary_C_padder=True,all_other_owner_definitions_and_pools_preserved=True)
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  symbols={x[0]:x for x in source.symbol_rows(before)}
  for first,names,order in source.METADATA_GROUPS:
   offsets.update(range(first,first+16*len(names)));start=symbols[first][3];offsets.update(range(start,start+sum(len(n)+1 for n in names)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),178);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=178,code_bytes=169,extent_bytes=1,metadata_bytes=8)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
