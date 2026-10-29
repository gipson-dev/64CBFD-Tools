"""Direct C actor callback: helper mutations, IEEE effects, CFG and whole image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_random_position_effect_match as source
from tools.tests import game_random_position_effect_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=Path(__file__).resolve().parents[2]
class RandomPositionEffectTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def assemble(self,p):subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'original-func_151C56A4.o'))
  bad=source.SELECTED.replace('% 3U + 3','% 3U + 4');self.assertNotEqual(bad,source.SELECTED);control,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+bad,'wrong-clamp');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(control))
  self.receipt['fresh_C']=dict(words=54,raw_C_byte_exact=True,guards=0,insertions=0,omissions=0,frame=80,bindings=3,source_control=True)
 def test_02_guest_original_dispatch_and_registration(self):
  oracle.o=self.out;result=oracle.run_suite();self.assertEqual(result,json.loads((self.out/'private-guest-v5.json').read_text()));self.receipt['guest']=result
 def test_03_native32_UBSan_and_seven_controls(self):
  p=self.fresh/'native.c';p.write_text(oracle.native_harness(source.HEADERS+source.SELECTED));rows={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-ffp-contract=off',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.returncode,run.stderr));rows[opt]=dict(exit=0,cases=3136,negative_controls=8,UBSan=True,invalid_float_conversions_claimed=False)
  self.receipt['native']=rows
 def test_04_original_frame_and_incoming_homes(self):
  raw,bindings=source.payload(self.out/'selected-final.o');words=struct.unpack('>54I',raw)
  self.assertEqual((words[0],words[0xCC//4]),(0x27BDFFB0,0x27BD0050));self.assertEqual(words[1],0xAFBF0034);self.assertEqual(words[0xC8//4],0x8FBF0034)
  stores={(w>>16&31,w&65535)for w in words if w>>26==43 and w>>21&31==29};self.assertTrue({(31,52),(4,80),(5,84),(6,88)}<=stores)
  loads={(w>>26,w>>16&31,w&65535)for w in words if w>>26 in(35,36)and w>>21&31==29};self.assertEqual(loads,{(35,31,52),(35,4,80),(36,25,87),(35,8,88)});self.assertFalse(source.NEW_GUARDS)
  self.receipt['frame']=dict(bytes=80,saved_offsets=[52],incoming_homes_used=True,incoming_home_offsets=[80,84,88],outgoing_home_extent=44,frame_adjustments=0,reachable_words=54)
 def test_05_raw_binding_controls_and_guard_history(self):
  raw,bindings=source.payload(self.out/'selected-final.o');controls=0
  for i in range(len(raw)):
   changed=bytearray(raw);changed[i]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(changed),bindings)
   controls+=1
  for at in bindings:
   with self.assertRaises(ValueError):source.checked_payload(raw,{**bindings,at:[('R_MIPS_26','wrong_symbol')]})
   controls+=1
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),self.values['conker/retail_word_patches.us.csv']);self.receipt['controls']=dict(raw_binding_controls=controls,new_guards=0,guard_manifest_unchanged=True)
 def test_06_complete_owner_and_actual_Make_evidence(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'original-func_151C56A4.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),7);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER));self.assertEqual(self.assemble(p).read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual((self.out/'make-shadow/src/game/generated_1F2730.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.receipt['owner']=dict(neighbors=7,actual_Make_commands=5,diagnostics=0)
 def test_07_literal_image_and_named_metadata_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=156,code_bytes=155,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
