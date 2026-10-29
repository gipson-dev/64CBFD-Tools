"""Randomized owner packet C, caller, owner and complete-image gates."""
from pathlib import Path
from dataclasses import replace
import itertools,json,os,shutil,struct,subprocess,unittest
from tools.experiments import game_owner_random_packet_match as source
from tools.tests import game_owner_random_packet_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
class OwnerRandomPacketTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>52I',cls.rom,source.ROM));oracle.o=cls.fresh
  cls.raw=oracle.linked(cls.out/'selected.o',source.ENTRY,'selected');cls.words=oracle.linked(cls.out/'qualified-padded.o',source.ENTRY,'padded');assert cls.raw==cls.words==cls.truth
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'original-func_151D0058.o'));self.receipt['fresh_C']=dict(words=52,guards=0,bindings=3)
 def test_02_guest_packet_effects_and_raw_argument_widths(self):
  count=0
  for rand,outcome,mutation,phase,k in itertools.product((0,55,56,255,0x80000000,0xFFFFFFFF),(0,1),range(4),(0,8),range(4)):
   c=oracle.Case(random=rand,outcome=outcome,mutation=mutation,phase=phase,seed=k,variant=(0,255,0x87654321,0xFFFFFFFF)[k],priority=(0,255,0x1234ABFF,0xFFFFFFFF)[k],context=(0,1,0x87654321,0xFFFFFFFF)[k],first=(0x3F800000,0xBF800000,0x80000000,0x3F000001)[k],second=(0x40000000,0x3F800000,0,0x3F800003)[k])
   initial=oracle.fixture(c);want,calls,payload=oracle.reference(initial,c);pair=[]
   for words in (self.truth,self.raw):
    m=oracle.Oracle(words,initial,c).run();self.assertEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls));self.assertEqual(m.packets,[payload]if outcome else[]);pair.append(m)
   self.assertEqual((pair[0].r,pair[0].f,pair[0].memory,pair[0].events,pair[0].trace),(pair[1].r,pair[1].f,pair[1].memory,pair[1].events,pair[1].trace));count+=1
  self.receipt['guest']=dict(cases=count,complete_padding=True,providers_bounded=True)
 def test_03_complete_original_caller(self):
  ENTRY=source.ENTRY
  class Caller(oracle.Oracle):
   def record_call(self,t):
    if t==ENTRY:
     a=tuple(self.arguments(4));assert a==oracle.args(self.case);self.calls.append((t,a));self.events.append(('CALL',t,a));return
    return super().record_call(t)
  count=0;caller=struct.unpack_from('>16I',self.rom,0x9EAD8);self.assertEqual(caller[10],0x0D474016)
  for command,outcome,mutation in itertools.product((0,1,0x54,0x55,0x56,0x154,0x80000000,0xFFFFFFFF),(0,1),range(4)):
   c=oracle.Case(variant=(command-0x55)&255,priority=255,context=1,outcome=outcome,mutation=mutation);initial=oracle.fixture(c);oracle.put(initial,0x800D154C,oracle.OWNER);want,calls,payload=oracle.reference(initial,replace(c,phase=-24));connected=dict(zip(range(ENTRY,ENTRY+208,4),self.raw));m=Caller(caller,initial,c,entry=0x15071628,connected=connected);m.r[4]=command;m.before=m.r[:];m.run();self.assertEqual(oracle.public(m.memory),oracle.public(want));self.assertEqual(m.calls,[(ENTRY,oracle.args(c))]+calls);count+=1
  self.receipt['caller']=dict(words=16,cases=count,complete_original=True)
 def test_04_native32_and_five_negative_controls(self):
  p=self.fresh/'native.c';p.write_text(oracle.native_harness());logs={}
  for opt in ('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.returncode,run.stderr));logs[opt]=dict(exit=0,cases=768,negative_controls=5,UBSan=True)
  self.receipt['native']=logs
 def test_05_all_access_fault_prefixes(self):
  c=oracle.Case();initial=oracle.fixture(c);full=oracle.Oracle(self.truth,initial,c).run();count=0
  for cut in range(full.all_accesses):
   pair=[]
   for words in (self.truth,self.raw):
    m=oracle.Oracle(words,initial,c);m.cut=cut
    with self.assertRaises(faults.AccessBoundary):m.run()
    pair.append(m)
   self.assertEqual((pair[0].r,pair[0].f,pair[0].memory,pair[0].events,pair[0].trace),(pair[1].r,pair[1].f,pair[1].memory,pair[1].events,pair[1].trace));count+=1
  self.receipt['faults']=dict(prefix_pairs=count)
 def test_06_GNU_layouts_and_raw_guard_controls(self):
  old=(oracle.RANDOM,oracle.FACTORY,oracle.COPY,oracle.syms);count=0
  try:
   for k,(entry,addresses)in enumerate(((0x15001000,(0x10001000,0x17008000,0x1600FFF0)),(0x1F008000,(0x1A008000,0x1800FFF0,0x10008000)),(0x1000FFF0,(0x12000040,0x1400FFF0,0x1F008000)))):
    symbols=dict(zip(('func_150ADA20','func_15149130','memcpy'),addresses));oracle.RANDOM,oracle.FACTORY,oracle.COPY=addresses;oracle.syms=symbols
    a=oracle.linked(self.out/'original-func_151D0058.o',entry,'original-layout'+str(k),symbols);b=oracle.linked(self.out/'selected.o',entry,'selected-layout'+str(k),symbols);self.assertEqual(a,b)
    for outcome,mutation in itertools.product((0,1),range(4)):
     c=oracle.Case(outcome=outcome,mutation=mutation);initial=oracle.fixture(c);want,calls,payload=oracle.reference(initial,c);m=oracle.Oracle(b,initial,c,entry=entry).run();self.assertEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls));count+=1
  finally:oracle.RANDOM,oracle.FACTORY,oracle.COPY,oracle.syms=old
  raw,rs=source.payload(self.out/'selected.o');controls=0
  for i in range(len(raw)):
   bad=bytearray(raw);bad[i]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   controls+=1
  for at in rs:
   bad={**rs,at:[('R_MIPS_26','wrong_provider')]}
   with self.assertRaises(ValueError):source.checked_payload(raw,bad)
   controls+=1
  self.receipt['layouts']=dict(layouts=3,cases=count,raw_and_binding_controls=controls)
 def test_07_full_owner_padding_caller_and_actual_Make_receipts(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.payload(obj),source.payload(self.out/'selected.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),51);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj))
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes())
  q=json.loads((self.out/'caller-declaration-proof.json').read_text());self.assertTrue(q['all_object_bytes_unchanged']);self.assertEqual(len(q['actual_Make_commands']),5);self.assertEqual((self.out/'caller-make-shadow/src/game_981E0.c.o').read_bytes(),self.values[source.OTHER_OBJECT]);self.assertEqual(source.recovered_caller(self.values[source.OTHER_SOURCE].decode()).encode(),(self.out/'proposed-caller.c').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.receipt['owner']=dict(neighbors=51,caller_functions=q['same_compact_functions'],caller_entire_object_fixed=True,actual_Make_commands=8)
 def test_08_strict_whole_image_and_negative_controls(self):
  source.check_inputs(ROOT,self.out,self.installed);before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();literal=self.rom[source.ROM:source.ROM+208];source.check_image(before,actual,literal);at=source.elf_slot_offset(before,source.ENTRY,208);count=0
  for offset in set((0,4,52,len(actual)-1,*range(at,at+208))):
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),literal)
   count+=1
  self.receipt['image']=dict(strict=True,exclusions=0,controls=count,changed_bytes=161)
