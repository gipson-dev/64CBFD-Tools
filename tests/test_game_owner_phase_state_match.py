"""Owner phase state: guarded owner, guest/native semantics and strict image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_owner_phase_state_match as source
from tools.tests import game_owner_phase_state_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class OwnerPhaseStateTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.checked_payload(*source.payload(obj))),source.payload(self.out/'original-func_15108C38.o'))
  raw,rs=source.payload(obj)
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for data,bindings,kw in((raw[:-4],{},{}),(raw+b'\0'*4,{},{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,{},dict(owner='foreign')),(raw,{},dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['fresh_C']=dict(words=59,retail_words=59,guards=1,insertions=0,omissions=0,raw_C_exact=False,normalization_rejections=241)
 def test_02_guest_original_callers_and_retail_data(self):
  oracle.o=self.out;result=oracle.run_suite();self.assertEqual(result,json.loads((self.out/'private-semantics-v8.json').read_text()));self.receipt['guest_suite']=result
  controls=oracle.compiled_controls(source.HEADERS+source.SELECTED);self.assertEqual(controls,json.loads((self.out/'private-controls-v13.json').read_text()));self.receipt['compiled_controls']=controls
 def test_03_native32_UBSan_and_effective_controls(self):
  oracle.o=self.fresh
  try:result=oracle.run_native(source.HEADERS+source.SELECTED)
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v13.json').read_text()));self.receipt['native']=result
 def test_04_retail_frame_profile_and_closed_relocation_schedule(self):
  raw,bindings=source.payload(self.out/'selected-final.o');self.assertEqual(len(raw),236);self.assertEqual(bindings,source.BINDINGS);w=struct.unpack('>59I',raw)
  self.assertEqual([w[i]for i in(0,1,4,5,6)],[0x27BDFFE0,0xAFB10018,0x00808825,0xAFBF001C,0xAFB00014]);self.assertEqual(w[-5:],(0x8FBF001C,0x8FB00014,0x8FB10018,0x03E00008,0x27BD0020))
  self.assertIn('s32 func_15108C38(u8 *owner)',source.SELECTED);self.assertIn('*((u8 *)state + 0x20) != 0',source.SELECTED);self.assertIn('return 1;',source.SELECTED)
  self.assertEqual(source.compile_owner.__module__,'tools.experiments.game_remaining_donor_candidates');self.assertEqual(source.compile_owner.__defaults__,(('-O2','-g3'),))
  proof=source.schedule_proof(raw,bindings,*source.payload(self.out/('original-'+source.FUNCTION+'.o')));self.assertTrue(proof['commutative_ADDU']);self.assertTrue(proof['all_other_words_identical']);self.receipt['schedule_proof']=proof
  self.receipt['frame']=dict(bytes=32,RA_offset=28,S0_state_offset=20,S1_owner_offset=24,body_words=59,reachable_words=59,alignment_words=0,return_type='s32',return_value=1,parameters=['u8 *owner'],bindings=16,profile='O2/g3')
 def test_05_actual_guard_preimages_and_closed_schedule(self):
  import csv,io,itertools
  manifest=(self.out/'proposed-guards.csv').read_bytes();self.assertEqual(manifest,source.guard_manifest(self.values['conker/retail_word_patches.us.csv']));self.assertTrue(manifest.startswith(self.values['conker/retail_word_patches.us.csv']))
  reader=csv.DictReader(io.StringIO(manifest.decode()));fields=reader.fieldnames;rows=list(reader);indices=[i for i,row in enumerate(rows)if row['function']==source.FUNCTION];self.assertEqual(len(indices),1);count=0
  for i,field in itertools.product(indices,('expected','expected_relocations')):
   changed=[dict(row)for row in rows];changed[i][field]='0xFFFFFFFF'if field=='expected'else'R_MIPS_26:foreign';path=self.fresh/'bad-guards.csv'
   with path.open('w',newline='')as stream:writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(changed)
   with self.assertRaisesRegex(ValueError,'stale word patch|stale relocations'):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=path)
   count+=1
  self.assertEqual(sum(bool(row['insert_after'])for row in source.NEW_GUARDS),0)
  rom=self.values['conker/conker.us.bin'];jal=(0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');literal=source.ENTRY.to_bytes(4,'big')
  self.assertEqual([i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal],[]);self.assertEqual([i for i in range(0,len(rom)-3,4)if rom[i:i+4]==literal],[0x22E6DC])
  self.receipt['guards']=dict(guards=1,insertions=0,omissions=0,actual_padder_preimage_rejections=count,inherited_prefix_identical=True,one_commutative_ADDU=True,aligned_JAL_ROM=[],aligned_literal_pointer_ROM=['0x22E6DC'])

 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),10);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertNotIn('-Wo,-loopunroll,0',json.loads((self.out/'Make-commands.json').read_text())[0]);self.assertEqual((self.out/'make-shadow/src/game/generated_135D00.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_135D00.c.o.compact'),11);self.receipt['owner']=dict(neighbors=10,actual_Make_commands=3,inherited_diagnostics=0,profile='O2/g3',all_other_owner_definitions_and_pools_preserved=True)
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16),*[i for i,(a,b)in enumerate(zip(before,actual))if a!=b]))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),296);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=296,code_bytes=195,extent_bytes=1,metadata_bytes=100)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
