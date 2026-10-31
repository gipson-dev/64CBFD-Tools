"""Dependency activation: full owner, guarded C, callback access order and image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_conditional_byte_blend_match as source
from tools.tests import game_conditional_byte_blend_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class ConditionalByteBlendTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_151CB510.o'))
  raw,rs=source.payload(obj)
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for data,bindings,kw in((raw[:-4],{},{}),(raw+b'\0'*4,{},{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,{},dict(owner='foreign')),(raw,{},dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=59,guards=7,insertions=0,omissions=0,raw_C_exact=False,normalization_rejections=241)
 def test_02_guest_original_dispatcher_connected_helpers(self):
  oracle.o=self.out;expected=json.loads((self.out/'private-semantics-v18.json').read_text())
  for name in('caller_suite','guest_suite'):
   result=getattr(oracle,name)();self.assertEqual(result,expected[name]);self.receipt[name]=result
 def test_03_native32_UBSan_and_fifteen_controls(self):
  oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-semantics-v18.json').read_text())['native_suite']);self.receipt['native']=result
 def test_04_leaf_FP_control_and_pointer_return_ABI(self):
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(raw),236);self.assertEqual(bindings,source.BINDINGS);w=struct.unpack('>59I',raw)
  self.assertEqual(w[0],0x8C820070);self.assertEqual(w[-5:],(0x44C9F800,0xA08A002E,0x00601025,0x03E00008,0));self.assertEqual((w[24],w[25],w[27],w[36],w[38]),(0x4449F800,0x44CAF800,0x460084A4,0x44CAF800,0x460094A4))
  self.assertIn('ConditionalBlendState *func_151CB510(ConditionalByteBlend *record)',source.SELECTED);self.assertIn('return blend;',source.SELECTED)
  self.receipt['frame']=dict(bytes=0,leaf=True,body_words=59,reachable_words=57,alignment_words=0,bindings=2,blend_offset=112,current_offset=116,target_offset=120,output_offset=46,FCSR_saved_after_arithmetic=True,return_type='ConditionalBlendState *',return_address_offset=112,shared_headers_unchanged=True)
 def test_05_closed_cursor_allocation_and_guard_controls(self):
  import copy,csv,io
  from unittest.mock import patch
  self.assertEqual(len(source.NEW_GUARDS),7);raw,rs=source.payload(self.out/'selected-final.o');truth,trs=source.payload(self.out/'original-func_151CB510.o');self.assertEqual(source.normalized_payload(raw,rs),(truth,trs));words=struct.unpack('>59I',raw);original=struct.unpack('>59I',truth);self.assertEqual([i for i,(a,b)in enumerate(zip(words,original))if a!=b],[7,12,14,15,23,26,56]);rejections=0
  for i,row in enumerate(source.NEW_GUARDS):
   at=int(row['offset'],0)//4
   if at in(7,14):self.assertEqual(words[at]^original[at],0x10000);self.assertEqual((words[at]>>16&31,original[at]>>16&31),(3,2))
   elif at in(12,15,23,26):self.assertEqual(words[at]^original[at],0x200000);self.assertEqual((words[at]>>21&31,original[at]>>21&31),(3,2))
   else:self.assertEqual((at,words[at],original[at]),(56,0x00601025,0))
   self.assertEqual((row['expected_relocations'],row['replacement_relocations']),('-','-'))
   for field in('expected','replacement','expected_relocations','replacement_relocations'):
    bad=copy.deepcopy(source.NEW_GUARDS);bad[i][field]=('0x%08X'%(int(bad[i][field],0)^1))if field in('expected','replacement')else'R_MIPS_LO16:foreign'
    with patch.object(source,'NEW_GUARDS',bad):
     with self.assertRaises(ValueError):source.normalized_payload(raw,rs)
    rejections+=1
   bad=copy.deepcopy(source.NEW_GUARDS);bad[i]['expected']='0x%08X'%(int(bad[i]['expected'],0)^1);stream=io.StringIO(newline='');fields=next(csv.reader(io.StringIO(self.values['conker/retail_word_patches.us.csv'].decode())));csv.DictWriter(stream,fields,lineterminator='\n').writerows(bad);p=self.fresh/('bad-preimage-'+str(i)+'.csv');p.write_bytes(self.values['conker/retail_word_patches.us.csv']+stream.getvalue().encode())
   with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=p)
   rejections+=1
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['guards']=dict(guards=7,insertions=0,omissions=0,closed_v1_to_v0_allocation_and_redundant_move_only=True,guard_row_controls=rejections,actual_padder_preimage_rejections=7,inherited_prefix_identical=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),45);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual((self.out/'make-shadow/src/game/generated_1F4650.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_1F4650.c.o.compact'),46);self.receipt['owner']=dict(neighbors=45,actual_Make_commands=5,inherited_diagnostics=0,profile='O2/g3',all_other_owner_definitions_and_pools_preserved=True)
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  symbols={at:(name,fields,string)for at,name,fields,string in source.symbol_rows(before)}
  for first,names,order in source.METADATA_GROUPS:
   self.assertEqual(tuple(symbols[first+16*i][0]for i in range(len(names))),names);offsets.update(range(first,first+16*len(names)));start=symbols[first][2];offsets.update(range(start,start+sum(len(n)+1 for n in names)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),168);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=168,code_bytes=157,extent_bytes=1,metadata_bytes=10)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
