"""Effect-slot release C: exact normalized words, nested iterators and full image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_effect_slot_release_match as source
from tools.tests import game_effect_slot_release_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class EffectSlotReleaseTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_semantic_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);raw,rs=source.checked_payload(*source.payload(obj));self.assertEqual(source.normalized_payload(raw,rs),source.payload(self.out/'original-func_150E35DC.o'))
  for at in range(220):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
  for data,bindings,kw in ((raw[:-4],rs,{}),(raw+b'\0'*4,rs,{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,rs,dict(owner='foreign')),(raw,rs,dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.receipt['fresh_C']=dict(words=55,normalized_words=56,bindings=11,guards=5,direct_C_exact=False,fingerprint_rejections=225)
 def test_02_guest_callers_helpers_and_compiled_controls(self):
  oracle.o=self.out
  expected=json.loads((self.out/'private-integration-v18.json').read_text())
  for name,fn,want in [('guest',oracle.guest_suite,json.loads((self.out/'private-guest-v16.json').read_text())),('caller',oracle.caller_suite,expected['caller']),('controls',oracle.compiled_controls,expected['controls']),('providers',oracle.provider_suite,expected['providers'])]:
   value=fn();self.assertEqual(value,want);self.receipt[name]=value
 def test_03_native32_UBSan_and_twelve_controls(self):
  (self.fresh/'selected-semantic-input.c').write_bytes((self.out/'selected-semantic-input.c').read_bytes());oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v17.json').read_text()));self.receipt['native']=result
 def test_04_retail_frame_saved_roles_and_rotation(self):
  raw,rs=source.payload(self.out/'selected-final.o');w=struct.unpack('>55I',raw);self.assertEqual(w[0],0x27BDFFD0);self.assertEqual(w[3],0xAFBF002C)
  for reg,offset in zip(range(16,21),(24,28,32,36,40)):
   self.assertIn(0xAF000000|(29<<21)|(reg<<16)|offset,w);self.assertIn(0x8C000000|(29<<21)|(reg<<16)|offset,w)
  self.assertEqual((w[45],w[46]),(0x1654FFE2,0xA26F0000));self.assertIn('void func_150E35DC(s32 handle)',source.SELECTED)
  obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED.replace('(u32)row != (u32)&D_800DD190','row != (u8 *)&D_800DD190'),'merged-end-pointer');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(obj))
  self.receipt['frame']=dict(bytes=48,RA_offset=44,saved=['s0','s1','s2','s3','s4'],raw_words=55,normalized_words=56,alignment_words=0,ABI='void(s32)',equivalent_merged_end_pointer_rejected=True)
 def test_05_five_guards_insertion_and_preimage_controls(self):
  import csv,io
  self.assertEqual(len(source.NEW_GUARDS),5);self.assertEqual(sum(bool(x['insert_after'])for x in source.NEW_GUARDS),1);self.assertTrue(all(x['omit']=='false'for x in source.NEW_GUARDS));self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected-final.o')),source.payload(self.out/'original-func_150E35DC.o'))
  fields=next(csv.reader(io.StringIO(self.values['conker/retail_word_patches.us.csv'].decode())));controls=0
  for index in range(5):
   for key in ('expected','expected_relocations'):
    rows=[dict(x)for x in source.NEW_GUARDS];rows[index][key]='0x%08X'%(int(rows[index][key],0)^1)if key=='expected'else 'R_MIPS_LO16:foreign'
    stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=fields,lineterminator='\n').writerows(rows);p=self.fresh/('bad-guards-%d-%s.csv'%(index,key));p.write_bytes(self.values['conker/retail_word_patches.us.csv']+stream.getvalue().encode())
    with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=p)
    controls+=1
  self.receipt['guards']=dict(new_rows=5,insertions=1,omissions=0,expected_word_and_binding_controls=controls,raw_compiler_words_exact=False,inherited_rows_preserved=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),12);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game/generated_1104D0.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_1104D0.c.o.compact'),13);self.receipt['owner']=dict(neighbors=12,actual_Make_commands=3,diagnostics=0,profile='O2/g3')
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),176);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=176,code_bytes=175,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
