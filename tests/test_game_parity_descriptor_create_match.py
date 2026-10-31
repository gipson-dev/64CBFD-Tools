"""Parity descriptor creation: direct C, ordered floating point and complete image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_parity_descriptor_create_match as source
from tools.tests import game_parity_descriptor_create_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class ParityDescriptorCreateTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_151A90C0.o'))
  raw,rs=source.payload(obj)
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for data,bindings,kw in((raw[:-4],{},{}),(raw+b'\0'*4,{},{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,{},dict(owner='foreign')),(raw,{},dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=59,guards=0,insertions=0,omissions=0,raw_C_exact=True,normalization_rejections=241)
 def test_02_guest_original_dispatcher_connected_helpers(self):
  oracle.o=self.out;expected=json.loads((self.out/'private-semantics-v13.json').read_text())
  for name in('caller_suite','guest_suite','connected_suite'):
   result=getattr(oracle,name)();self.assertEqual(result,expected[name]);self.receipt[name]=result
 def test_03_native32_UBSan_and_fifteen_controls(self):
  oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-semantics-v13.json').read_text())['native_suite']);self.receipt['native']=result
 def test_04_retail_frame_and_request_ABI(self):
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(raw),236);self.assertEqual(bindings,source.BINDINGS);self.assertEqual(sum(len(v)for v in bindings.values()),10);w=struct.unpack('>59I',raw)
  self.assertEqual(w[:5],(0x27BDFFA8,0x44801000,0xAFBF001C,0xAFA5005C,0x8FAF005C));self.assertEqual(w[-4:],(0x8FBF001C,0x27BD0058,0x03E00008,0))
  self.assertIn('void func_151A90C0(u8 *owner, s32 selector)',source.SELECTED);self.assertIn('u8 tag[1];',source.SELECTED);self.assertIn('f32 zero[5];',source.HEADERS)
  self.receipt['frame']=dict(bytes=88,RA_offset=28,incoming_selector_home=92,tag_offset=40,request_offset=48,request_bytes=40,defined_request_bytes=36,body_words=59,reachable_words=59,alignment_words=0,return_type='void',allocator_pointer_return_and_callback_table_types_word_neutral=True,shared_headers_unchanged=True)
 def test_05_direct_match_and_unchanged_guards(self):
  self.assertFalse(source.NEW_GUARDS);self.assertEqual(source.payload(self.out/'selected-final.o'),source.payload(self.out/'original-func_151A90C0.o'));self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),self.values['conker/retail_word_patches.us.csv']);self.assertEqual((self.out/'proposed-guards.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv']);self.receipt['guards']=dict(guards=0,insertions=0,omissions=0,inherited_manifest_identical=True,direct_C_exact=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),22);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game/generated_1D4E00.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_1D4E00.c.o.compact'),23);self.receipt['owner']=dict(neighbors=22,actual_Make_commands=3,inherited_diagnostics=0,profile='O2/g3',all_other_owner_definitions_and_pools_preserved=True)
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  symbols={at:(name,fields,string)for at,name,fields,string in source.symbol_rows(before)}
  for first,names,order in source.METADATA_GROUPS:
   self.assertEqual(tuple(symbols[first+16*i][0]for i in range(len(names))),names);offsets.update(range(first,first+16*len(names)));start=symbols[first][2];offsets.update(range(start,start+sum(len(n)+1 for n in names)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),311);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=311,code_bytes=179,extent_bytes=1,metadata_bytes=131)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
