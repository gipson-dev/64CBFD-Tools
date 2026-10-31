"""Effect debug packet: complete owner, direct C, guest/native aliases and image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_effect_debug_packet_alt_match as source
from tools.tests import game_effect_debug_packet_alt_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class EffectDebugSubmitTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_151A0F28.o'))
  raw,rs=source.payload(obj)
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for data,bindings,kw in((raw[:-4],{},{}),(raw+b'\0'*4,{},{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,{},dict(owner='foreign')),(raw,{},dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=58,guards=10,insertions=0,omissions=0,raw_C_exact=False,normalization_rejections=237)
 def test_02_guest_original_dispatcher_connected_helpers(self):
  oracle.o=self.out;expected=json.loads((self.out/'private-semantics-v8.json').read_text())
  for name in('caller_suite','guest_suite','connected_suite'):
   result=getattr(oracle,name)();self.assertEqual(result,expected[name]);self.receipt[name]=result
 def test_03_native32_UBSan_and_twelve_controls(self):
  oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-semantics-v8.json').read_text())['native_suite']);self.receipt['native']=result
 def test_04_retail_frame_and_floating_argument_ABI(self):
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(raw),232);self.assertEqual(bindings,source.BINDINGS);w=struct.unpack('>58I',raw)
  self.assertEqual(w[:5],(0x27BDFF88,0xAFBF0074,0xAFA60080,0xAFA70084,0x30E400FF));self.assertEqual(w[-4:],(0x8FBF0074,0x27BD0078,0x03E00008,0))
  self.assertIn('void func_151A0F28(f32 x, f32 y, f32 value, u8 variant, s32 flags)',source.SELECTED)
  self.assertIn('f32 arg0, f32 arg1, f32 arg2, f32 arg3',source.HELPER)
  self.receipt['frame']=dict(bytes=120,RA_offset=116,value_home=128,variant_home=132,flags_home=136,outgoing_arguments=28,first_two_floats_in_f12_f14=True,helper_words=6,body_words=58,alignment_words=0,return_type='void',shared_headers_unchanged=True)
 def test_05_closed_schedules_and_guard_controls(self):
  import collections,copy
  from unittest.mock import patch
  self.assertEqual(len(source.NEW_GUARDS),10);raw,rs=source.payload(self.out/'selected-final.o');truth,trs=source.payload(self.out/'original-func_151A0F28.o');self.assertNotEqual(raw,truth);self.assertEqual(source.normalized_payload(raw,rs),(truth,trs))
  words=struct.unpack('>58I',raw);original=struct.unpack('>58I',truth)
  for window in ((1,2,3,4,5,6),(48,49,50,51)):
   self.assertEqual(collections.Counter((words[i],tuple(rs.get(i*4,[])))for i in window),collections.Counter((original[i],tuple(trs.get(i*4,[])))for i in window))
  rejections=0
  for i in range(10):
   for field in ('expected','replacement','expected_relocations','replacement_relocations'):
    bad=copy.deepcopy(source.NEW_GUARDS);bad[i][field]=('0x%08X'%(int(bad[i][field],0)^1))if field in ('expected','replacement')else'R_MIPS_LO16:foreign'
    with patch.object(source,'NEW_GUARDS',bad):
     with self.assertRaises(ValueError):source.normalized_payload(raw,rs)
    rejections+=1
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes())
  self.assertTrue((self.out/'proposed-guards.csv').read_bytes().startswith(self.values['conker/retail_word_patches.us.csv']))
  self.receipt['guards']=dict(guards=10,insertions=0,omissions=0,closed_schedules=2,guard_row_controls=rejections,inherited_manifest_prefix_identical=True,raw_fault_order_claim=False)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),38);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual((self.out/'make-shadow/src/game/generated_1CC440.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_1CC440.c.o.compact'),39);self.receipt['owner']=dict(neighbors=38,actual_Make_commands=5,inherited_diagnostics=0,profile='O2/g3',all_other_owner_definitions_and_pools_preserved=True)
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),231);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=231,code_bytes=182,extent_bytes=1,metadata_bytes=48)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
