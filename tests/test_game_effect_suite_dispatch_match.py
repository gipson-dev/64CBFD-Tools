"""Effect suite dispatch: guarded owner, guest/native semantics and strict image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_effect_suite_dispatch_match as source
from tools.tests import game_effect_suite_dispatch_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class EffectSuiteDispatchTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_151C9DE8.o'))
  raw,rs=source.payload(obj)
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for data,bindings,kw in((raw[:-4],{},{}),(raw+b'\0'*4,{},{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,{},dict(owner='foreign')),(raw,{},dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=59,retail_words=59,guards=0,insertions=0,omissions=0,raw_C_exact=True,normalization_rejections=241)
 def test_02_guest_original_callers_and_retail_data(self):
  oracle.o=self.out;result=oracle.run_suite();self.assertEqual(result,json.loads((self.out/'private-semantics-v10.json').read_text()));self.receipt['guest_suite']=result
  controls=oracle.compiled_controls(source.HEADERS+source.SELECTED);self.assertEqual(controls,json.loads((self.out/'private-controls-v13.json').read_text()));self.receipt['compiled_controls']=controls
 def test_03_native32_UBSan_and_thirteen_controls(self):
  oracle.o=self.fresh
  try:result=oracle.run_native(source.HEADERS+source.SELECTED)
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v13.json').read_text()));self.receipt['native']=result
 def test_04_retail_frame_profile_and_closed_relocation_schedule(self):
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(raw),236);self.assertEqual(bindings,source.BINDINGS);w=struct.unpack('>59I',raw)
  self.assertEqual(w[:11],(0x27BDFFD0,0xAFB20028,0xAFB10024,0xAFB00020,0x00808025,0x30F100FF,0x30B200FF,0xAFBF002C,0xAFA50034,0xAFA60038,0xAFA7003C));self.assertEqual(w[-6:],(0x8FBF002C,0x8FB00020,0x8FB10024,0x8FB20028,0x03E00008,0x27BD0030))
  self.assertEqual([w[i]for i in(14,33,39,43)],[0x83A7003B,0x83A6003B,0x8FA60040,0x83A7003B]);self.assertIn('void func_151C9DE8(void *owner, u8 slot, s8 kind, u8 selector, s32 value)',source.SELECTED)
  self.assertIn('func_151CCF08(owner, slot & 0xFF, kind, selector & 0xFF)',source.SELECTED);self.assertEqual(source.compile_owner.__module__,'tools.experiments.game_remaining_donor_candidates');self.assertEqual(source.compile_owner.__defaults__,(('-O2','-g3'),))
  proof=source.schedule_proof(raw,bindings,*source.payload(self.out/('original-'+source.FUNCTION+'.o')));self.assertTrue(proof['direct_C_match']);self.receipt['direct_proof']=proof
  self.receipt['frame']=dict(bytes=48,RA_offset=44,S0_owner_offset=32,S1_selector_offset=36,S2_slot_offset=40,signed_kind_home_byte=59,fifth_word_home_offset=64,body_words=59,reachable_words=59,alignment_words=0,return_type='void',parameters=['void *owner','u8 slot','s8 kind','u8 selector','s32 value'],bindings=10,profile='O2/g3')
 def test_05_actual_guard_preimages_and_closed_schedule(self):
  before=self.values['conker/retail_word_patches.us.csv'];self.assertEqual((self.out/'proposed-guards.csv').read_bytes(),before);self.assertEqual(source.guard_manifest(before),before);self.assertEqual(source.NEW_GUARDS,[])
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(bindings),10);count=0
  for at in bindings:
   bad=dict(bindings);bad[at]=[(bindings[at][0][0],'foreign')]
   with self.assertRaises(ValueError):source.checked_payload(raw,bad)
   count+=1
  rom=self.values['conker/conker.us.bin'];jal=(0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');literal=source.ENTRY.to_bytes(4,'big')
  self.assertEqual([i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal],[0x52858,0x1F718C]);self.assertEqual([i for i in range(0,len(rom)-3,4)if rom[i:i+4]==literal],[])
  self.receipt['guards']=dict(guards=0,insertions=0,omissions=0,guard_manifest_unchanged=True,raw_binding_rejections=count,aligned_JAL_ROM=['0x52858','0x1F718C'],aligned_literal_pointer_ROM=[])

 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),45);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertNotIn('-Wo,-loopunroll,0',json.loads((self.out/'Make-commands.json').read_text())[1]);self.assertEqual((self.out/'make-shadow/src/game/generated_1F4650.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_1F4650.c.o.compact'),46);self.receipt['owner']=dict(neighbors=45,actual_Make_commands=5,inherited_diagnostics=0,profile='O2/g3',all_other_owner_definitions_and_pools_preserved=True)
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16),*range(0x2AD7A4,0x2AD7C4),*range(0x2F1854,0x2F186D)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),186);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=186,code_bytes=185,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
