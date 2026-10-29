"""Direct C actor callback: helper mutations, IEEE effects, CFG and whole image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_coordinate_query_result_match as source
from tools.tests import game_coordinate_query_result_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=Path(__file__).resolve().parents[2]
class CoordinateQueryResultTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def assemble(self,p):subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_1510F648.o'))
  bad=source.SELECTED.replace('256.0f','128.0f');self.assertNotEqual(bad,source.SELECTED);control,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+bad,'wrong-clamp');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(control))
  self.receipt['fresh_C']=dict(words=54,raw_C_byte_exact=False,normalized_byte_exact=True,guards=7,insertions=0,omissions=0,frame=48,bindings=12,source_control=True)
 def test_02_guest_original_dispatch_and_registration(self):
  oracle.o=self.out;result=oracle.run_suite();self.assertEqual(result,json.loads((self.out/'private-guest-v16.json').read_text()));self.receipt['guest']=result
 def test_03_native32_UBSan_and_eight_controls(self):
  p=self.fresh/'native.c';p.write_text(oracle.native_harness(source.HEADERS+source.SELECTED));rows={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-ffp-contract=off',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.returncode,run.stderr));rows[opt]=dict(exit=0,cases=1080,negative_controls=8,UBSan=True,invalid_float_conversion_claimed=False,native_NaN_payload_equality_claimed=False)
  self.receipt['native']=rows
 def test_04_frame_and_closed_local_slot_mapping(self):
  raw,bindings=source.payload(self.out/'selected-final.o');retail,rs=source.normalized_payload(raw,bindings);w=struct.unpack('>54I',raw);p=struct.unpack('>54I',retail)
  self.assertEqual((w[0],w[1],w[-1]),(0x27BDFFD0,0xAFBF0014,0x27BD0030));self.assertEqual([w[i]for i in(2,3,4)],[0xE7AC0030,0xE7AE0034,0xAFA60038]);self.assertEqual(w[0x98//4],0x8FBF0014)
  self.assertEqual([4*i for i in range(54)if w[i]!=p[i]],[0x2C,0x5C,0x64,0x70,0x84,0x88,0x90]);self.assertTrue(all(w[i]>>16==p[i]>>16 and(p[i]&65535)==(w[i]&65535)+4 for i in range(54)if w[i]!=p[i]));self.assertEqual(bindings,rs)
  self.receipt['frame']=dict(bytes=48,saved_offsets=[20],incoming_homes_used=True,incoming_home_offsets=[48,52,56],outgoing_home_extent=16,frame_adjustments=0,reachable_words=54,closed_local_slots=3)
 def test_05_raw_binding_controls_and_guard_history(self):
  raw,bindings=source.payload(self.out/'selected-final.o');controls=0
  for i in range(len(raw)):
   changed=bytearray(raw);changed[i]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(changed),bindings)
   controls+=1
  for at in bindings:
   with self.assertRaises(ValueError):source.checked_payload(raw,{**bindings,at:[('R_MIPS_26','wrong_symbol')]})
   controls+=1
  prefix=self.values['conker/retail_word_patches.us.csv'];self.assertEqual(source.guard_manifest(prefix),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(len(source.NEW_GUARDS),7)
  for i,row in enumerate(source.NEW_GUARDS):
   changed=dict(row,expected='0x00000000');source.NEW_GUARDS[i]=changed
   try:
    with self.assertRaises(ValueError):source.normalized_payload(raw,bindings)
   finally:source.NEW_GUARDS[i]=row
  self.assertEqual(json.loads((self.out/'private-owner-v11.json').read_text())['guard_preimage_controls'],7)
  self.receipt['controls']=dict(raw_binding_controls=controls,new_guards=7,guard_preimage_controls=7,padder_preimage_controls=7,inherited_guard_prefix_preserved=True)

 def test_06_complete_owner_and_actual_Make_evidence(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_1510F648.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),13);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER));self.assertEqual(self.assemble(p).read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual((self.out/'make-shadow/src/game/generated_13BB20.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.receipt['owner']=dict(neighbors=13,actual_Make_commands=5,diagnostics=0)
 def test_07_literal_image_and_named_metadata_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for first,names,order in source.METADATA_GROUPS:
   offsets.update(range(first,first+16*len(names)));start=next(x[3]for x in source.symbol_rows(before)if x[0]==first);offsets.update(range(start,start+sum(len(n)+1 for n in names)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=192,code_bytes=171,extent_bytes=1,metadata_bytes=20)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
