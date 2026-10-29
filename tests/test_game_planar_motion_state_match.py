"""Planar callback source, register guards, dispatch ABI and literal image gates."""
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_planar_motion_state_match as source
from tools.tests import game_planar_motion_state_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
class PlanarMotionStateTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>53I',cls.rom,source.ROM));oracle.o=cls.fresh
  cls.raw=oracle.linked(cls.out/'selected.o','selected');cls.words=oracle.linked(cls.out/'qualified-padded.o','qualified');assert cls.words==cls.truth
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def assemble(self,p):subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
 def test_01_fresh_C_normalization_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_150C308C.o'));self.receipt['fresh_C']=dict(words=53,guards=2,bindings=9,closed_F0_to_F12_pair=True)
 def test_02_guest_float_boundaries_and_provider_effects(self):
  count=0;visited=set();bits=oracle.bits;vectors=[(bits(0.),bits(0.)),(bits(1500.),bits(500.)),(bits(2000.),bits(0.)),(0x7FC12345,bits(1.)),(0x7F800000,bits(1.))]
  for state,(x,z),difference,mode,phase in itertools.product((-32768,-1,5,6,7,32767),vectors,(bits(0.0),bits(0.4),bits(0.5),0x7FC12345),(0,1,6,15),(0,8)):
   c=oracle.Case(state=state,x=x,z=z,difference=difference,mode=mode,phase=phase);initial=oracle.fixture(c);want,calls=oracle.reference(initial,c);pair=[]
   for words in (self.truth,self.words,self.raw):
    m=oracle.Oracle(words,initial,c).run();self.assertEqual((oracle.public(m.memory),m.calls,m.r[2]),(oracle.public(want),calls,1));pair.append(m)
   self.assertEqual((pair[0].r,pair[0].f,pair[0].memory,pair[0].events,pair[0].trace),(pair[1].r,pair[1].f,pair[1].memory,pair[1].events,pair[1].trace));visited.update(pair[0].visits);count+=1
  unvisited=[hex(pc)for pc in range(source.ENTRY,source.ENTRY+212,4)if pc not in visited];self.assertEqual(unvisited,['0x150c30fc']);self.receipt['guest']=dict(cases=count,executions=count*3,covered_words=len(visited),unvisited=unvisited,raw_public_equivalence=True,normalized_full_state_equivalence=True)
 def test_03_original_indirect_dispatcher_and_registration(self):
  registration=0x80082B20+0x22E7C8-0x2275E0;self.assertEqual(registration,0x80089C18+60*4);self.assertEqual(struct.unpack_from('>I',self.rom,0x22E7C8)[0],source.ENTRY);caller=struct.unpack_from('>41I',self.rom,0x168C48);count=0
  for state,(x,z),mode in itertools.product((5,6,7),[(oracle.bits(0.),oracle.bits(0.)),(oracle.bits(1500.),oracle.bits(500.)),(oracle.bits(2000.),oracle.bits(0.))],(0,15)):
   c=oracle.Case(state=state,x=x,z=z,mode=mode);initial=oracle.fixture(c);oracle.put(initial,registration,source.ENTRY);want,calls=oracle.reference(initial,c);connected=dict(zip(range(source.ENTRY,source.ENTRY+212,4),self.words));m=oracle.Caller(caller,initial,c,entry=0x1513B798,connected=connected).run();self.assertEqual((oracle.public(m.memory),m.calls),(oracle.public(want),[(source.ENTRY,(oracle.ACTOR,))]+calls));count+=1
  self.receipt['caller']=dict(words=41,cases=count,active_callback_route=True,callback_table='D_80089C18',index=60,registration_ROM='0x22E7C8',other_dispatcher_paths_claimed=False)
 def test_04_native32_and_six_negative_controls(self):
  p=self.fresh/'native.c';p.write_text(oracle.native_harness());logs={}
  for opt in ('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);b=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(b.returncode,0,b.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.returncode,run.stderr));logs[opt]=dict(exit=0,cases=600,negative_controls=6,UBSan=True)
  self.receipt['native']=logs
 def test_05_all_access_prefixes_and_sparse_skips(self):
  count=0;sparse=0
  for c in (oracle.Case(state=5),oracle.Case(),oracle.Case(x=oracle.bits(1500.),z=oracle.bits(500.),mode=15)):
   initial=oracle.fixture(c);full=oracle.Oracle(self.truth,initial,c).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in (self.truth,self.words):
     m=oracle.Oracle(words,initial,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual((pair[0].r,pair[0].f,pair[0].memory,pair[0].events,pair[0].trace),(pair[1].r,pair[1].f,pair[1].memory,pair[1].events,pair[1].trace));count+=1
  for c in (oracle.Case(state=5),oracle.Case()):
   initial=oracle.fixture(c)
   if c.state==5:initial={a:b for a,b in initial.items()if oracle.STACK-512<=a<oracle.STACK+512 or oracle.ACTOR-16<=a<oracle.ACTOR+528}
   else:
    for i in range(4):initial.pop(oracle.ACTOR+0x160+i);initial.pop(oracle.syms['D_800A0314']+i)
   want,calls=oracle.reference(initial,c)
   for words in (self.truth,self.words):
    m=oracle.Oracle(words,initial,c).run();self.assertEqual((oracle.public(m.memory),m.calls,m.r[2]),(oracle.public(want),calls,1))
   sparse+=1
  self.receipt['faults']=dict(prefix_pairs=count,sparse_skips=sparse,integer_and_float_call_clobbers=True)
 def test_06_GNU_rebases_and_effective_guard_controls(self):
  previous=(oracle.VECTOR,oracle.ANGLE,oracle.DELTA,oracle.syms);count=0
  try:
   for k,(entry,vector,angle,delta,player,threshold,limit)in enumerate(((0x15001000,0x10001000,0x17008000,0x1600FFF0,0x80007FF0,0x80017FF0,0x80018000),(0x1F008000,0x1A008000,0x1800FFF0,0x10008000,0x80008000,0x80018000,0x8001FFF0),(0x1000FFF0,0x12000040,0x1400FFF0,0x1F008000,0x8000FFF0,0x8001FFF0,0x80028000))):
    oracle.VECTOR,oracle.ANGLE,oracle.DELTA=vector,angle,delta;oracle.syms=dict(func_15144B34=vector,func_150484A0=angle,func_15144C8C=delta,D_80082FA4=player,D_800A0310=threshold,D_800A0314=limit)
    a=oracle.linked(self.out/'original-func_150C308C.o','original-layout'+str(k),entry,oracle.syms);b=oracle.linked(self.out/'qualified-padded.o','qualified-layout'+str(k),entry,oracle.syms);self.assertEqual(a,b)
    for state,mode,x in itertools.product((5,6),(0,15),(0,oracle.bits(2000.))):
     c=oracle.Case(state=state,mode=mode,x=x);initial=oracle.fixture(c);want,calls=oracle.reference(initial,c);m=oracle.Oracle(b,initial,c,entry=entry).run();self.assertEqual((oracle.public(m.memory),m.calls,m.r[2]),(oracle.public(want),calls,1));count+=1
  finally:oracle.VECTOR,oracle.ANGLE,oracle.DELTA,oracle.syms=previous
  raw,rs=source.payload(self.out/'selected.o');controls=0
  for i in range(len(raw)):
   bad=bytearray(raw);bad[i]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   controls+=1
  for at in rs:
   with self.assertRaises(ValueError):source.checked_payload(raw,{**rs,at:[('R_MIPS_26','wrong_symbol')]})
   controls+=1
  bad=bytearray(self.values['conker/retail_word_patches.us.csv']);bad[0]^=1
  with self.assertRaises(ValueError):source.guard_manifest(bytes(bad))
  manifest=(self.out/'proposed-guards.csv').read_text();bad=self.fresh/'bad-expect.csv';bad.write_text(manifest.replace('0x46062000','0x46062001'))
  with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.LAYOUT,source.OWNER,word_patches_path=bad)
  for label,text in [('replacement',manifest.replace('0x46062300','0x46062380')),('omission','\n'.join(line for line in manifest.splitlines()if not(line.startswith('game_EF410,func_150C308C,')and ',0x058,'in line))+'\n')]:
   bad=self.fresh/('bad-'+label+'.csv');bad.write_text(text);p=self.fresh/('bad-'+label+'.s');p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.LAYOUT,source.OWNER,word_patches_path=bad));obj=self.assemble(p);self.assertNotEqual(source.payload(obj),source.payload(self.out/'original-func_150C308C.o'));words=oracle.linked(obj,'bad-linked-'+label);c=oracle.Case(x=oracle.bits(2000.),difference=0);initial=oracle.fixture(c);want,calls=oracle.reference(initial,c);m=oracle.Oracle(words,initial,c).run();self.assertNotEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls))
  self.receipt['layouts']=dict(layouts=3,cases=count,raw_binding_controls=controls,guard_controls=4)
 def test_07_full_primary_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_150C308C.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),17);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj))
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.LAYOUT,source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));self.assertEqual(self.assemble(p).read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['owner']=dict(neighbors=17,actual_Make_commands=5,primary_padder=True,guards=2,diagnostics=0)
 def test_08_strict_whole_image_and_negative_controls(self):
  source.check_inputs(ROOT,self.out,self.installed);before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();literal=self.rom[source.ROM:source.ROM+212];source.check_image(before,actual,literal);at=source.elf_slot_offset(before,source.ENTRY,212);count=0
  for offset in set((0,4,52,len(actual)-1,*range(at,at+212))):
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),literal)
   count+=1
  self.receipt['image']=dict(strict=True,exclusions=0,controls=count,changed_bytes=152)
