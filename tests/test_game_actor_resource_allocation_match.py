"""Actor resources: live count, literal frame/CFG, original callers and full image."""
from pathlib import Path
import csv,io,json,os,struct,subprocess,unittest
from tools.experiments import game_actor_resource_allocation_match as source
from tools.tests import game_actor_resource_allocation_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=Path(__file__).resolve().parents[2]
class ActorResourceAllocationTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def assemble(self,p):subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_150832AC.o'))
  bad=source.SELECTED.replace('? 5 : 3','? 7 : 3');self.assertNotEqual(bad,source.SELECTED);control,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+bad,'rejected-fallback');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.normalized_payload(*source.payload(control))
  self.receipt['fresh_C']=dict(compiler_words=53,normalized_words=54,frame=48,guards=18,bindings=4,insertions=1,omissions=0,void_interface=True,source_control=True)
 def test_02_guest_and_original_caller_windows(self):
  oracle.o=self.out;result=oracle.run_suite();self.assertEqual(result,json.loads((self.out/'private-qualified-guest-v13.json').read_text()));self.receipt['guest']=result
 def test_03_native32_UBSan_and_six_controls(self):
  p=self.fresh/'native.c';p.write_text(oracle.native_harness(source.HEADERS+source.SELECTED));rows={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.returncode,run.stderr));rows[opt]=dict(exit=0,cases=5184,negative_controls=6,UBSan=True)
  self.receipt['native']=rows
 def test_04_frame_and_redundant_branch_certificate(self):
  raw,bindings=source.payload(self.out/'selected-final.o');normalized,rels=source.normalized_payload(raw,bindings);words=struct.unpack('>53I',raw);saves=[];loads=[]
  for w in words:
   if w>>21&31==29 and w>>26 in(35,43):
    (saves if w>>26==43 else loads).append((w>>16&31,w&65535))
  self.assertEqual(sorted(saves),[(16,24),(17,28),(18,32),(19,36),(20,40),(31,44)]);self.assertEqual(set(loads),set(saves));self.assertEqual((words[0],words[-1]),(0x27BDFFD0,0x27BD0030));self.assertEqual(struct.unpack_from('>2I',normalized,0x58),(0x10000001,0x24130003));self.assertEqual(words[0x48//4],0x24130003)
  insertions=[x for x in source.NEW_GUARDS if x['insert_after']];self.assertEqual(len(insertions),1);self.assertEqual(insertions[0]['offset'],'0x058');self.assertEqual(rels,source.ORIGINAL_BINDINGS)
  self.receipt['frame']=dict(bytes=48,saved_offsets=[24,28,32,36,40,44],incoming_homes_used=False,outgoing_home_extent=16,frame_adjustments=0,insertions=1,omissions=0,extra_control_is_redundant_branch=True)
 def test_05_raw_binding_and_guard_controls(self):
  raw,bindings=source.payload(self.out/'selected-final.o');controls=0
  for i in range(len(raw)):
   changed=bytearray(raw);changed[i]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(changed),bindings)
   controls+=1
  for at in bindings:
   with self.assertRaises(ValueError):source.checked_payload(raw,{**bindings,at:[('R_MIPS_26','wrong_symbol')]})
   controls+=1
  rows=list(csv.DictReader(io.StringIO((self.out/'proposed-guards.csv').read_text())));guard_controls=0
  for i,row in enumerate(source.NEW_GUARDS):
   modified=[dict(x,expected=hex(int(x['expected'],0)^1))if x['function']==source.FUNCTION and x['filename']==source.OWNER and x['offset']==row['offset']else x for x in rows];stream=io.StringIO();writer=csv.DictWriter(stream,list(rows[0]));writer.writeheader();writer.writerows(modified);p=self.fresh/('preimage-'+str(i)+'.csv');p.write_text(stream.getvalue())
   with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=p,filename=source.OWNER,rodata_symbol=source.RODATA_SYMBOL)
   guard_controls+=1
  self.receipt['controls']=dict(raw_binding_controls=controls,guard_preimage_controls=guard_controls)
 def test_06_complete_owner_and_actual_Make_evidence(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_150832AC.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),30);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER,rodata_symbol=source.RODATA_SYMBOL));self.assertEqual(self.assemble(p).read_bytes(),(self.out/'qualified-padded.o').read_bytes());commands=json.loads((self.out/'Make-commands.json').read_text());self.assertEqual(len(commands),5);self.assertEqual([Path(x[0]).name for x in commands],['python3','cc','python3','python3','mips-linux-gnu-as']);self.assertEqual((self.out/'make-shadow/src/game/generated_AEB40.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.receipt['owner']=dict(neighbors=30,actual_Make_commands=5,diagnostics=0,rodata_symbol=source.RODATA_SYMBOL)
 def test_07_literal_image_and_named_metadata_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();rom=self.values['conker/conker.us.bin'];truth=rom[source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=161,code_bytes=160,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
