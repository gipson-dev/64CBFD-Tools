"""Save checksum reader: original transfer/default helpers, weighted bytes and literal image."""
from pathlib import Path
import json,os,re,struct,subprocess,unittest
from tools.experiments import game_attached_effect_payload_match as source
from tools.tests import game_attached_effect_payload_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class AttachedEffectPayloadTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_150ECA68.o'))
  raw,rs=source.payload(obj)
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for data,bindings,kw in ((raw[:-4],{},{}),(raw+b'\0'*4,{},{}),(raw,{0:[('R_MIPS_LO16','func_150ECA68')]},{}),(raw,{},dict(owner='foreign')),(raw,{},dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=57,guards=0,insertions=0,omissions=0,raw_C_exact=True,normalization_rejections=233)
 def test_02_guest_original_helpers_callers_and_controls(self):
  oracle.o=self.out;expected=json.loads((self.out/'private-semantics-v7.json').read_text())
  for name,fn in [('guest_suite',oracle.guest_suite),('caller_suite',oracle.caller_suite),('compiled_controls',oracle.compiled_controls)]:
   result=fn();self.assertEqual(result,expected[name]);self.receipt[name]=result
 def test_03_native32_UBSan_and_thirteen_controls(self):
  (self.fresh/'selected-semantic-input.c').write_bytes((self.out/'selected-semantic-input.c').read_bytes());oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v11.json').read_text()));self.receipt['native']=result
 def test_04_retail_frame_void_ABI_and_complete_body(self):
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(raw),228);self.assertEqual(bindings,source.BINDINGS);w=struct.unpack('>57I',raw)
  self.assertEqual(w[:4],(0x27BDFFB8,0xAFA5004C,0xAFA60050,0xAFA70054));self.assertEqual(w[10],0xAFBF002C);self.assertEqual(w[-4:],(0x8FBF002C,0x27BD0048,0x03E00008,0))
  self.assertIn('s16 duration, u8 selector, s32 category',source.SELECTED)
  signature='struct260 *func_15149130(s16 arg0, s8 arg1, s8 arg2, s8 arg3, u8 arg4, u8 arg5, struct37 *arg6, u8 arg7, s32 arg8)'
  self.assertIn(signature,(ROOT/'conker/src/game/done/game_1765E0.c').read_text());self.assertIn('struct260 *func_15149130(s16, s8, s8, s8, u8, u8, struct37 *, u8, s32);',source.HEADERS)
  self.receipt['frame']=dict(bytes=72,RA_offset=44,body_words=57,alignment_words=0,payload_offset=60,payload_bytes=12,padding_offsets=[70,71],ABI='void(u8 *,u8,u8,u8,u8,u8,s16,u8,s32)',helper_definition_signature_compatible=True)
 def test_05_no_new_guards_and_original_call_census(self):
  self.assertEqual(source.NEW_GUARDS,[]);self.assertEqual((self.out/'proposed-guards.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
  rom=self.values['conker/conker.us.bin'];jal=(0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');literal=source.ENTRY.to_bytes(4,'big')
  calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==literal]
  self.assertEqual(calls,[0x11A108]);self.assertEqual(pointers,[]);self.receipt['census']=dict(aligned_JAL_ROM=['0x11A108'],aligned_literal_pointers=0,guards=0,inherited_manifest_unchanged=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),6);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game/generated_1199D0.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_1199D0.c.o.compact'),7);self.receipt['owner']=dict(neighbors=6,actual_Make_commands=3,diagnostics=0,profile='O2/g3')
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
