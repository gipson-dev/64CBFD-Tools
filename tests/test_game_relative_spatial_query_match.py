"""Relative spatial query C: guarded allocation, wrap arithmetic, aliases and full image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_relative_spatial_query_match as source
from tools.tests import game_relative_spatial_query_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class RelativeSpatialQueryTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_semantic_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);raw,rs=source.checked_payload(*source.payload(obj));self.assertEqual(source.normalized_payload(raw,rs),source.payload(self.out/'original-func_1510F720.o'))
  for at in range(224):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
  for data,bindings,kw in ((raw[:-4],rs,{}),(raw+b'\0'*4,rs,{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,rs,dict(owner='foreign')),(raw,rs,dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.receipt['fresh_C']=dict(words=56,normalized_words=56,bindings=2,guards=21,direct_C_exact=False,fingerprint_rejections=229)
 def test_02_guest_callers_and_compiled_controls(self):
  oracle.o=self.out;expected=json.loads((self.out/'private-integration-v13.json').read_text())
  for name,fn,want in [('guest',oracle.guest_suite,json.loads((self.out/'private-guest-v11.json').read_text())),('caller',oracle.caller_suite,expected['caller']),('controls',oracle.compiled_controls,expected['controls'])]:
   value=fn();self.assertEqual(value,want);self.receipt[name]=value
 def test_03_native32_UBSan_and_seventeen_controls(self):
  (self.fresh/'selected-semantic-input.c').write_bytes((self.out/'selected-semantic-input.c').read_bytes());oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-integration-v13.json').read_text())['native']);self.receipt['native']=result
 def test_04_frame_live_roles_and_unchanged_instruction_shapes(self):
  raw,rs=source.payload(self.out/'selected-final.o');w=struct.unpack('>56I',raw);truth,trs=source.payload(self.out/'original-func_1510F720.o');tw=struct.unpack('>56I',truth)
  self.assertEqual(w[:4],(0x27BDFFF0,0xAFB2000C,0xAFB10008,0xAFB00004));self.assertEqual(w[-5:],(0x8FB00004,0x8FB10008,0x8FB2000C,0x03E00008,0x27BD0010));self.assertEqual(rs,trs);self.assertEqual(sum(a!=b for a,b in zip(w,tw)),21)
  def diagnostic_shape(word):return word&(~(0x03FFF800 if word>>26==0 else 0x03E00000 if word>>26==1 else 0 if word>>26 in(2,3)else 0x03FF0000)&0xFFFFFFFF)
  self.assertEqual(list(map(diagnostic_shape,w)),list(map(diagnostic_shape,tw)));self.assertFalse(any(word>>26==3 or word>>26==0 and word&63==9 for word in w))
  old='        absX = dx < 0 ? (s32)(0u - (u32)dx) : dx;';new='        if (dx < 0) dx = (s32)(0u - (u32)dx);\n        absX = dx;';self.assertIn(old,source.SELECTED)
  obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED.replace(old,new),'inplace-absolute-control');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(obj))
  self.receipt['frame']=dict(bytes=16,saved_slots=[4,8,12],saved=['s0','s1','s2'],RA_saved=False,body_words=56,reachable_words=53,raw_S0_role='query x',normalized_S0_role='query radius',opcodes_immediates_and_branch_displacements_fixed=True,diagnostic_masks_not_used_to_rewrite_code=True,equivalent_inplace_absolute_rejected=True)
 def test_05_twenty_one_guards_and_preimage_controls(self):
  import csv,io
  self.assertEqual(len(source.NEW_GUARDS),21);self.assertFalse(any(x['insert_after']for x in source.NEW_GUARDS));self.assertTrue(all(x['omit']=='false'for x in source.NEW_GUARDS));self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected-final.o')),source.payload(self.out/'original-func_1510F720.o'))
  columns=next(csv.reader(io.StringIO(self.values['conker/retail_word_patches.us.csv'].decode())));count=0
  for index in range(21):
   for field in('expected','expected_relocations'):
    rows=[dict(x)for x in source.NEW_GUARDS];rows[index][field]='0x%08X'%(int(rows[index][field],0)^1)if field=='expected'else 'R_MIPS_LO16:foreign';stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=columns,lineterminator='\n').writerows(rows);p=self.fresh/('bad-guards-%d-%s.csv'%(index,field));p.write_bytes(self.values['conker/retail_word_patches.us.csv']+stream.getvalue().encode())
    with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=p)
    count+=1
  self.receipt['guards']=dict(new_rows=21,insertions=0,omissions=0,expected_word_and_binding_controls=count,raw_compiler_words_exact=False,inherited_rows_preserved=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),13);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual((self.out/'make-shadow/src/game/generated_13BB20.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_13BB20.c.o.compact'),14);self.receipt['owner']=dict(neighbors=13,actual_Make_commands=5,diagnostics=0,profile='O2/g3')
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),166);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=166,code_bytes=165,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
