"""Actor coordinate effect dispatch: full callback words, live coordinates, float ABI and named metadata."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_actor_coordinate_effect_dispatch_match as source
from tools.tests import game_actor_coordinate_effect_dispatch_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=Path(__file__).resolve().parents[2]
class ActorCoordinateEffectDispatchTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def assemble(self,p):subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'original-func_150D8A34.o'))
  bad=source.SELECTED.replace('+ 4.0f','+ 3.0f');self.assertNotEqual(bad,source.SELECTED);control,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+bad,'wrong-height');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(control))
  self.receipt['fresh_C']=dict(words=54,raw_C_byte_exact=True,guards=0,insertions=0,omissions=0,frame=64,bindings=7,source_control=True)
 def test_02_guest_float_ABI_live_coordinates_and_dispatcher(self):
  oracle.o=self.out;result=oracle.run_suite();self.assertEqual(result,json.loads((self.out/'private-guest-v7.json').read_text()));self.receipt['guest']=result
 def test_03_native32_UBSan_and_nine_controls(self):
  oracle.o=self.fresh
  try:result=oracle.run_native(source.HEADERS+source.SELECTED)
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v8.json').read_text()));self.assertEqual(result['cases'],1166);self.assertEqual(result['negative_controls'],9);self.receipt['native']=result
 def test_04_frame_callback_homes_and_alignment(self):
  raw,bindings=source.payload(self.out/'selected-final.o');w=struct.unpack('>54I',raw);self.assertEqual(w[:4],(0x27BDFFC0,0xAFBF002C,0xAFA50044,0xAFA60048));self.assertEqual(w[11],0xAFA70040);self.assertEqual(w[-4:],(0x8FBF002C,0x27BD0040,0x03E00008,0));self.assertEqual(self.values['conker/conker.us.bin'][source.ROM+216:source.ROM+220],bytes(4));self.assertFalse(source.NEW_GUARDS)
  self.receipt['frame']=dict(bytes=64,RA_offset=44,vector_offset=52,vector_bytes=12,outgoing_home_extent=36,incoming_homes=[0,4,8],owner_home_conditional=True,unused_argument_home_retained=True,reachable_words=54,slot_words=55,alignment_words=1)
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
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'original-func_150D8A34.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),8);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER,rodata_symbol=source.RODATA_SYMBOL));self.assertEqual(self.assemble(p).read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual((self.out/'make-shadow/src/game/generated_105760.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.receipt['owner']=dict(neighbors=8,actual_Make_commands=3,diagnostics=0)
 def test_07_literal_image_and_named_metadata_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  positions={p:(n,f,s)for p,n,f,s in source.symbol_rows(before)}
  for first,names,order in source.METADATA_GROUPS:
   offsets.update(range(first,first+16*len(names)));start=positions[first][2];offsets.update(range(start,start+sum(len(n)+1 for n in names)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=188,code_bytes=171,extent_bytes=1,metadata_bytes=16)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
