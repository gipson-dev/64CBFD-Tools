"""Settings packet write: guarded owner, guest/native semantics and strict image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_settings_packet_write_match as source
from tools.tests import game_settings_packet_write_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class SettingsPacketWriteTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_15007558.o'))
  raw,rs=source.payload(obj)
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for data,bindings,kw in((raw[:-4],{},{}),(raw+b'\0'*4,{},{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,{},dict(owner='foreign')),(raw,{},dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=59,retail_words=59,guards=3,insertions=0,omissions=0,raw_C_exact=False,normalization_rejections=241)
 def test_02_guest_original_callers_and_retail_data(self):
  oracle.o=self.out;expected=json.loads((self.out/'private-semantics-v13.json').read_text())
  for name in('caller_suite','guest_suite'):
   result=getattr(oracle,name)();self.assertEqual(result,expected[name]);self.receipt[name]=result
 def test_03_native32_UBSan_and_seven_controls(self):
  oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-semantics-v13.json').read_text())['native_suite']);self.receipt['native']=result
  oracle.o=self.fresh
  try:affected=oracle.dependency_native_suite()
  finally:oracle.o=self.out
  self.assertEqual(affected,json.loads((self.out/'private-semantics-v13.json').read_text())['dependency_native_suite']);self.receipt['dependency_native']=affected
 def test_04_record_frame_status_and_void_ABI(self):
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(raw),236);self.assertEqual(bindings,source.BINDINGS);w=struct.unpack('>59I',raw)
  self.assertEqual(w[0],0x27BDFFE0);self.assertEqual(w[-4:],(0x8FBF0014,0x27BD0020,0x03E00008,0))
  self.assertIn(0xAFA20018,w);self.assertIn('void func_15007558(void)',source.SELECTED)
  self.receipt['frame']=dict(bytes=32,compiler_words=59,body_words=59,reachable_words=59,alignment_words=0,return_type='void',volatile_status_stack_offset=24,raw_bindings=15,normalized_bindings=15,record_bytes=32,payload_bytes=28)
 def test_05_actual_guard_preimages_and_closed_schedule(self):
  import csv,io,itertools
  manifest=(self.out/'proposed-guards.csv').read_bytes();self.assertEqual(manifest,source.guard_manifest(self.values['conker/retail_word_patches.us.csv']));self.assertTrue(manifest.startswith(self.values['conker/retail_word_patches.us.csv']))
  reader=csv.DictReader(io.StringIO(manifest.decode()));fields=reader.fieldnames;rows=list(reader);indices=[i for i,row in enumerate(rows)if row['function']==source.FUNCTION];self.assertEqual(len(indices),3);count=0
  for i,field in itertools.product(indices,('expected','expected_relocations')):
   changed=[dict(row)for row in rows];changed[i][field]='0xFFFFFFFF'if field=='expected'else'R_MIPS_26:foreign';path=self.fresh/'bad-guards.csv'
   with path.open('w',newline='')as stream:writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(changed)
   with self.assertRaisesRegex(ValueError,'stale word patch|stale relocations'):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=path)
   count+=1
  self.assertEqual(sum(bool(row['insert_after'])for row in source.NEW_GUARDS),0)
  self.receipt['guards']=dict(guards=3,insertions=0,omissions=0,actual_padder_preimage_rejections=count,inherited_prefix_identical=True,closed_address_materialization_and_counter_schedule=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),17);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game_33990.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game_33990.c.o.compact'),18);self.receipt['owner']=dict(neighbors=17,actual_Make_commands=3,inherited_diagnostics=0,profile='O2/g3',all_other_owner_definitions_and_pools_preserved=True)
  dep=source.recovered_settings_owner(self.values[source.DEPENDENCY].decode());obj,diag=source.compile_owner(ROOT,self.fresh,dep,'fresh-settings-owner')
  self.assertEqual(source.same_functions(self.out/'before-settings-owner.o',obj),60);self.assertEqual(source.normalized_pools(self.out/'before-settings-owner.o'),source.normalized_pools(obj))
  self.assertEqual((self.out/'make-shadow/src/game/generated_20AE20.c.o').read_bytes(),self.values[source.DEPENDENCY_OBJECT])
  self.assertEqual(len(json.loads((self.out/'settings-Make-commands.json').read_text())),3)
  self.assertEqual(source.recovered_header(self.values[source.HEADER]),(self.out/'proposed-variables.h').read_bytes())
  self.receipt['dependency']=dict(functions=60,padded_object_identical=True,actual_Make_commands=3,record_bytes=32,settings_bytes=28,reset_bytes=23)

 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),211);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=211,code_bytes=196,extent_bytes=1,metadata_bytes=14)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
