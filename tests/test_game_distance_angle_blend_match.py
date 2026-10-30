"""Distance angle blend: direct C owner, guest/native ABI and image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_distance_angle_blend_match as source
from tools.tests import game_distance_angle_blend_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class DistanceAngleBlendTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_1512C068.o'))
  raw,rs=source.payload(obj)
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for data,bindings,kw in((raw[:-4],{},{}),(raw+b'\0'*4,{},{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,{},dict(owner='foreign')),(raw,{},dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=58,guards=0,insertions=0,omissions=0,raw_C_exact=True,normalization_rejections=237)
 def test_02_guest_original_helper_callers_and_controls(self):
  oracle.o=self.out;expected=json.loads((self.out/'private-semantics-v9.json').read_text());controls=json.loads((self.out/'private-native-v10.json').read_text())['compiled_controls']
  for name in('guest_suite','caller_suite'):
   result=getattr(oracle,name)();self.assertEqual(result,expected[name]);self.receipt[name]=result
  result=oracle.compiled_controls();self.assertEqual(result,controls);self.receipt['compiled_controls']=result
 def test_03_native32_UBSan_and_fifteen_controls(self):
  oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v10.json').read_text())['native_suite']);self.receipt['native']=result
 def test_04_retail_frame_and_assembly_consumer_ABI(self):
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(raw),232);self.assertEqual(bindings,source.BINDINGS);w=struct.unpack('>58I',raw)
  self.assertEqual(w[:2],(0x27BDFFE8,0xAFBF0014));self.assertEqual(w[-4:],(0x8FBF0014,0x27BD0018,0x03E00008,0));self.assertEqual(w[14],w[9]);self.assertEqual(w[14],0x44817000)
  self.assertIn('s32 func_15123A54(struct108 *);',source.HEADERS);self.assertIn('s32 func_15123A54()',self.values['conker/src/game_14FF90.c'].decode())
  self.receipt['frame']=dict(bytes=24,RA_offset=20,body_words=58,reachable_words=57,alignment_words=0,unreachable_duplicate_word=14,actor_home=24,orientation_return_ignored=True,current_provider_return_declaration_compatible=True,shared_headers_unchanged=True)
 def test_05_closed_schedule_and_actual_padder_controls(self):
  self.assertEqual(source.NEW_GUARDS,[]);self.assertEqual((self.out/'proposed-guards.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
  rom=self.values['conker/conker.us.bin'];jal=(0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');literal=source.ENTRY.to_bytes(4,'big')
  calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==literal]
  self.assertEqual(calls,[0x150484,0x1504B0]);self.assertEqual(pointers,[]);self.receipt['guards']=dict(guards=0,insertions=0,omissions=0,inherited_manifest_unchanged=True,aligned_ROM_JALs=['0x150484','0x1504B0'],aligned_literal_pointers=0)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),14);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game/generated_157840.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_157840.c.o.compact'),15);self.receipt['owner']=dict(neighbors=14,actual_Make_commands=3,diagnostics=0,profile='O2/g3',all_other_owner_definitions_and_pools_preserved=True)
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),177);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=177,code_bytes=176,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
