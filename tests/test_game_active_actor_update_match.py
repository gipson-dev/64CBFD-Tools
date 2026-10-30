"""Active actor update: slot traversal, live callback index, ABI and full image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_active_actor_update_match as source
from tools.tests import game_active_actor_update_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class ActiveActorUpdateTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_semantic_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);raw,rs=source.checked_payload(*source.payload(obj));self.assertEqual(source.normalized_payload(raw,rs),source.payload(self.out/'original-func_1502378C.o'))
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
  for data,bindings,kw in ((raw[:-4],rs,{}),(raw+b'\0'*4,rs,{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,rs,dict(owner='foreign')),(raw,rs,dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.receipt['fresh_C']=dict(words=54,normalized_words=54,bindings=14,guards=2,direct_C_exact=False,profile='O2/g3/no-unroll')
 def test_02_guest_helpers_callers_and_controls(self):
  oracle.o=self.out;expected=json.loads((self.out/'private-semantics-v11.json').read_text())
  for name,fn in [('guest_suite',oracle.guest_suite),('caller_suite',oracle.caller_suite),('compiled_controls',oracle.compiled_controls)]:
   result=fn();self.assertEqual(result,expected[name]);self.receipt[name]=result
 def test_03_native32_UBSan_and_thirteen_controls(self):
  (self.fresh/'selected-semantic-input.c').write_bytes((self.out/'selected-semantic-input.c').read_bytes());oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v12.json').read_text()));self.receipt['native']=result
 def test_04_frame_schedule_and_alignment(self):
  raw,rs=source.payload(self.out/'selected-final.o');w=struct.unpack('>54I',raw);truth,trs=source.payload(self.out/'original-func_1502378C.o');tw=struct.unpack('>54I',truth)
  self.assertEqual(w[:7],(0x27BDFFD0,0xAFBF002C,0xAFB40028,0xAFB30024,0xAFB20020,0xAFB1001C,0xAFB00018));self.assertEqual(w[-7:],(0x8FB00018,0x8FB1001C,0x8FB20020,0x8FB30024,0x8FB40028,0x03E00008,0x27BD0030));self.assertEqual(rs,trs);self.assertEqual(len(rs),14)
  self.assertEqual(w[:19]+w[21:],tw[:19]+tw[21:]);self.assertEqual(w[19:21],(0x24120019,0x24140001));self.assertEqual(tw[19:21],w[19:21][::-1]);self.assertEqual(self.values['conker/conker.us.bin'][source.ROM+source.BODY:source.ROM+source.SIZE],bytes(12))
  self.receipt['frame']=dict(bytes=48,saved_slots=[24,28,32,36,40],saved=['s0','s1','s2','s3','s4'],RA_saved=True,RA_offset=44,body_words=54,alignment_words=3,independent_initialization_words=[19,20],ABI='void(void)')
 def test_05_two_schedule_guards_and_preimage_controls(self):
  import csv,io
  self.assertEqual(len(source.NEW_GUARDS),2);self.assertFalse(any(x['insert_after']for x in source.NEW_GUARDS));self.assertTrue(all(x['omit']=='false'for x in source.NEW_GUARDS));self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected-final.o')),source.payload(self.out/'original-func_1502378C.o'))
  columns=next(csv.reader(io.StringIO(self.values['conker/retail_word_patches.us.csv'].decode())));count=0
  for index in range(2):
   for field in('expected','expected_relocations'):
    rows=[dict(x)for x in source.NEW_GUARDS];rows[index][field]='0x%08X'%(int(rows[index][field],0)^1)if field=='expected'else 'R_MIPS_LO16:foreign';stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=columns,lineterminator='\n').writerows(rows);p=self.fresh/('bad-guards-%d-%s.csv'%(index,field));p.write_bytes(self.values['conker/retail_word_patches.us.csv']+stream.getvalue().encode())
    with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=p)
    count+=1
  self.receipt['guards']=dict(new_rows=2,insertions=0,omissions=0,expected_word_and_binding_controls=count,raw_compiler_words_exact=False,inherited_rows_preserved=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),56);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game/generated_49D30.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_49D30.c.o.compact'),57);self.receipt['owner']=dict(neighbors=56,actual_Make_commands=3,diagnostics=0,profile='O2/g3/no-unroll')
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),171);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=171,code_bytes=170,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
