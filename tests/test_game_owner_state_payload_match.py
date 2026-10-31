"""Owner identity and value payload: exact C, helpers, callers and literal image."""
from pathlib import Path
import json,os,re,struct,subprocess,unittest
from tools.experiments import game_owner_state_payload_match as source
from tools.tests import game_owner_state_payload_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class OwnerStatePayloadTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_15109410.o'))
  raw,rs=source.payload(obj)
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for data,bindings,kw in ((raw[:-4],{},{}),(raw+b'\0'*4,{},{}),(raw,{0:[('R_MIPS_LO16','func_15109410')]},{}),(raw,{},dict(owner='foreign')),(raw,{},dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=59,guards=0,insertions=0,omissions=0,raw_C_exact=True,normalization_rejections=241)
 def test_02_guest_original_helpers_callers_and_controls(self):
  oracle.o=self.out;expected=json.loads((self.out/'private-semantics-v9.json').read_text())
  for name,fn in [('guest_suite',oracle.guest_suite),('caller_suite',oracle.caller_suite),('compiled_controls',oracle.compiled_controls)]:
   result=fn();self.assertEqual(result,expected[name]);self.receipt[name]=result
 def test_03_native32_UBSan_and_fifteen_controls(self):
  (self.fresh/'selected-semantic-input.c').write_bytes((self.out/'selected-semantic-input.c').read_bytes());oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v11.json').read_text()));self.receipt['native']=result
 def test_04_retail_frame_pointer_ABI_and_complete_body(self):
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(raw),236);self.assertEqual(bindings,source.BINDINGS);w=struct.unpack('>59I',raw)
  self.assertEqual(w[:4],(0x27BDFFB0,0xAFA50054,0x00057400,0x000E2C03));self.assertEqual(w[4],0xAFBF002C);self.assertEqual(w[-4:],(0x8FBF002C,0x27BD0050,0x03E00008,0))
  self.assertIn('s16 lifetime, s8 first, s8 second, f32 value',source.SELECTED);self.assertIn('u32 extraBytes, u8 selector, s32 category',source.SELECTED)
  signature='struct260 *func_15149130(s16 arg0, s8 arg1, s8 arg2, s8 arg3, u8 arg4, u8 arg5, struct37 *arg6, u8 arg7, s32 arg8)'
  self.assertIn(signature,(ROOT/'conker/src/game/done/game_1765E0.c').read_text());self.assertIn('struct260 *func_15149130(s16, s8, s8, s8, u8, u8, struct37 *, u8, s32);',source.HEADERS)
  self.receipt['frame']=dict(bytes=80,RA_offset=44,body_words=59,alignment_words=0,payload_offset=56,payload_bytes=20,padding_offsets=[61,62,63,74,75],saved_result_offset=76,ABI='void *(u8 *,s16,s8,s8,f32,u32,u8,s32)',helper_definition_signature_compatible=True)
 def test_05_no_new_guards_and_original_call_census(self):
  self.assertEqual(source.NEW_GUARDS,[]);self.assertEqual((self.out/'proposed-guards.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
  rom=self.values['conker/conker.us.bin'];jal=(0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');literal=source.ENTRY.to_bytes(4,'big')
  calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==literal]
  self.assertEqual(calls,[0x54A60,0x54A9C]);self.assertEqual(pointers,[]);self.receipt['census']=dict(aligned_JAL_ROM=['0x54A60','0x54A9C'],aligned_literal_pointers=0,guards=0,inherited_manifest_unchanged=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),9);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game/generated_1368C0.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_1368C0.c.o.compact'),10);self.receipt['owner']=dict(neighbors=9,actual_Make_commands=3,diagnostics=0,profile='O2/g3',neighbor='func_1510A344',neighbor_change='none')
  before=self.values[source.SOURCE].decode();after=source.recovered_owner(before)
  for neighbor in ('func_15109ED4','func_1510A344'):
   a,b=source.function_span(before,neighbor);x,y=source.function_span(after,neighbor);self.assertEqual(before[a:b],after[x:y])

 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  symbols={x[0]:x for x in source.symbol_rows(before)}
  for first,names,order in source.METADATA_GROUPS:
   offsets.update(range(first,first+16*len(names)));start=symbols[first][3];offsets.update(range(start,start+sum(len(n)+1 for n in names)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),174);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=174,code_bytes=173,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
