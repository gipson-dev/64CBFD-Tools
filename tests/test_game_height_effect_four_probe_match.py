"""Height probe source, guard/ABI, original caller and closed image gates."""
from pathlib import Path
import csv,io,itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_height_effect_four_probe_match as source
from tools.tests import game_height_effect_four_probe_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ROOT=Path(__file__).resolve().parents[2]
class HeightEffectFourProbeTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];oracle.o=cls.fresh;cls.truth=list(struct.unpack_from('>53I',cls.rom,source.ROM));cls.words=oracle.linked(cls.out/'qualified-padded.o','qualified');cls.raw=oracle.linked(cls.out/'selected.o','raw');assert cls.words==cls.truth
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def assemble(self,p):subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_151A9FC8.o'));self.receipt['fresh_C']=dict(words=53,frame=64,guards=8,bindings=4)
 def test_02_guest_boundaries_mutations_and_payloads(self):
  count=0;visited=set();tops=[oracle.bits(oracle.value(oracle.THRESHOLD)-1.),oracle.THRESHOLD,oracle.bits(oracle.value(oracle.THRESHOLD)+1.),0x7FC12345,0x7F800000,0xFF800000]
  for top,y,outcome,mode,identity,phase in itertools.product(tops,(oracle.bits(-150.),oracle.bits(200.),0x7FC12345),(0,1,0xFFFFFFFF),(0,1,2,7),(0,255),(0,8)):
   c=oracle.Case(top=top,y=y,outcome=outcome,mode=mode,identity=identity,phase=phase);initial=oracle.fixture(c);want,calls=oracle.reference(initial,c);pair=[]
   for words in(self.truth,self.words,self.raw):
    m=oracle.Oracle(words,initial,c).run();self.assertEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls));pair.append(m)
   self.assertEqual((pair[0].r,pair[0].f,pair[0].memory,pair[0].events,pair[0].trace),(pair[1].r,pair[1].f,pair[1].memory,pair[1].events,pair[1].trace));visited.update(pair[0].visits);count+=1
  unvisited=[hex(pc)for pc in range(source.ENTRY,source.ENTRY+212,4)if pc not in visited];self.assertEqual(unvisited,['0x151aa01c']);self.receipt['guest']=dict(cases=count,executions=count*3,covered_words=len(visited),unvisited=unvisited,raw_public_payload_equivalence=True,normalized_full_state_equivalence=True,threshold=-9500.)
 def test_03_original_dispatch_window_and_registration(self):
  self.assertEqual(struct.unpack_from('>I',self.rom,0x22FAA8)[0],source.ENTRY);window=struct.unpack_from('>10I',self.rom,0x1863F0);mask=0xB0000;table=0x8008AFD0;count=0
  class Caller(oracle.Oracle):
   def __init__(self,words,memory,c,connected):oracle.FactoryOracle.__init__(self,words,memory,c,entry=0x15158F40,s=oracle.syms,connected=connected,arguments=(oracle.OWNER,))
   def record_call(self,t):
    if t==source.ENTRY:a=tuple(self.arguments(1));self.calls.append((t,a));self.events.append(('CALL',t,a));return
    return super().record_call(t)
  for outcome,mode,maskpass,top,phase in itertools.product((0,1),(0,7),(False,True),(oracle.bits(-9501.),oracle.bits(-9499.)),(0,8)):
   c=oracle.Case(outcome=outcome,mode=mode,top=top,phase=phase);initial=oracle.fixture(c);oracle.put(initial,mask+4,0xA5 if maskpass else 0);oracle.put(initial,table+6*4,source.ENTRY)
   if maskpass:want,calls=oracle.reference(initial,c);calls=[(source.ENTRY,(oracle.OWNER,))]+calls
   else:want,calls=initial,[]
   for words in(self.truth,self.words,self.raw):
    connected=dict(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));connected.update({0x15158F68:0,0x15158F6C:0});m=Caller(window,initial,c,connected);m.r[4]=mask;m.r[3]=6;m.r[17]=oracle.OWNER;m.r[18]=0xA5;m.r[22]=table;m.r[16]=3;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(0x15158F68,0x15158F6C)
    with self.assertRaises(WindowBoundary):m.run()
    self.assertEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls));self.assertEqual((m.r[17],m.r[18],m.r[22],m.r[16]),(oracle.OWNER,0xA5,table,3 if maskpass else 4))
   count+=1
  self.receipt['caller']=dict(words=10,cases=count,table='D_8008AFD0',index=6,first_mask_gate_precondition=True,second_mask_pass_and_skip=True,complete_parent_claimed=False,parent_C_placeholder_uncredited=True)
 def test_04_native32_UBSan_and_six_controls(self):
  p=self.fresh/'native.c';p.write_text(oracle.native_harness(source.HEADERS+source.SELECTED));rows={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.returncode,run.stderr));rows[opt]=dict(exit=0,cases=432,negative_controls=6,UBSan=True)
  self.receipt['native']=rows
 def test_05_access_prefixes_and_sparse_skips(self):
  count=0
  for c in(oracle.Case(top=oracle.bits(-9501.),outcome=0),oracle.Case(top=oracle.bits(-9499.),outcome=1,mode=7),oracle.Case(top=0x7FC12345,outcome=1)):
   initial=oracle.fixture(c);full=oracle.Oracle(self.truth,initial,c).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=oracle.Oracle(words,initial,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual((pair[0].r,pair[0].f,pair[0].memory,pair[0].events,pair[0].trace),(pair[1].r,pair[1].f,pair[1].memory,pair[1].events,pair[1].trace));count+=1
  sparse=0
  for c,remove in[(oracle.Case(top=oracle.bits(-9499.),outcome=1),[oracle.ACTOR+24+i for i in range(4)]),(oracle.Case(top=oracle.bits(-9501.),outcome=0),[oracle.OWNER+1,oracle.OWNER+12])]:
   initial=oracle.fixture(c)
   for at in remove:del initial[at]
   want,calls=oracle.reference(initial,c)
   for words in(self.truth,self.words):
    m=oracle.Oracle(words,initial,c).run();self.assertEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls))
   sparse+=1
  self.receipt['faults']=dict(prefix_pairs=count,sparse_skips=sparse,raw_C_fault_equivalence_claimed=False)
 def test_06_rebases_and_effective_guard_controls(self):
  previous=(oracle.QUERY,oracle.EFFECT,oracle.syms);count=0
  try:
   for k,(entry,query,effect,threshold)in enumerate(((0x15001000,0x10001000,0x17008000,0x80007FF0),(0x1F008000,0x1A008000,0x1800FFF0,0x80008000),(0x1000FFF0,0x12000040,0x1400FFF0,0x8000FFF0))):
    oracle.QUERY,oracle.EFFECT=query,effect;oracle.syms=dict(D_800A8F8C=threshold,func_15045800=query,func_151ABE40=effect);a=oracle.linked(self.out/'original-func_151A9FC8.o','original-layout'+str(k),entry,oracle.syms);b=oracle.linked(self.out/'qualified-padded.o','qualified-layout'+str(k),entry,oracle.syms);self.assertEqual(a,b)
    for top,outcome,mode in itertools.product((oracle.bits(-9501.),oracle.bits(-9499.)),(0,1),(0,7)):
     c=oracle.Case(top=top,outcome=outcome,mode=mode);initial=oracle.fixture(c);want,calls=oracle.reference(initial,c);m=oracle.Oracle(b,initial,c,entry=entry).run();self.assertEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls));count+=1
  finally:oracle.QUERY,oracle.EFFECT,oracle.syms=previous
  raw,rs=source.payload(self.out/'selected.o');controls=0
  for i in range(len(raw)):
   bad=bytearray(raw);bad[i]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   controls+=1
  for at in rs:
   with self.assertRaises(ValueError):source.checked_payload(raw,{**rs,at:[('R_MIPS_26','wrong_symbol')]})
   controls+=1
  rows=list(csv.DictReader(io.StringIO((self.out/'proposed-guards.csv').read_text())));fields=list(rows[0]);guard_controls=0
  def manifest(label,values):
   p=self.fresh/(label+'.csv');stream=io.StringIO();writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(values);p.write_text(stream.getvalue());return p
  for guard in source.NEW_GUARDS:
   modified=[dict(row,expected=hex(int(row['expected'],0)^1))if row['filename']==source.OWNER and row['function']==source.FUNCTION and row['offset']==guard['offset']else row for row in rows];bad=manifest('preimage-'+guard['offset'],modified)
   with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=bad,filename=source.OWNER)
   guard_controls+=1
  # Removing either end of the spill pair must break the submitted descriptor.
  for offset in('0x080','0x0A4'):
   bad=manifest('omission-'+offset,[row for row in rows if not(row['filename']==source.OWNER and row['function']==source.FUNCTION and row['offset']==offset)]);p=self.fresh/('omission-'+offset+'.s');p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=bad,filename=source.OWNER));obj=self.assemble(p);self.assertNotEqual(source.payload(obj),source.payload(self.out/'original-func_151A9FC8.o'));words=oracle.linked(obj,'bad-'+offset);c=oracle.Case(outcome=1);initial=oracle.fixture(c);want,calls=oracle.reference(initial,c);m=oracle.Oracle(words,initial,c).run();self.assertNotEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls));guard_controls+=1
  self.receipt['layouts']=dict(layouts=3,cases=count,raw_binding_controls=controls,guard_controls=guard_controls)
 def test_07_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_151A9FC8.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),40);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER));self.assertEqual(self.assemble(p).read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['owner']=dict(neighbors=40,actual_Make_commands=5,generated_padder=True,guards=8,diagnostics=0)
 def test_08_literal_image_and_named_metadata_controls(self):
  source.check_inputs(ROOT,self.out,self.installed);before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();literal=self.rom[source.ROM:source.ROM+212];source.check_image(before,actual,literal);at=source.elf_slot_offset(before,source.ENTRY,212);symbols={p:(n,f,s)for p,n,f,s in source.symbol_rows(before)};first,names,order=source.METADATA_GROUPS[0];string=symbols[first][2];offsets=set((0,4,52,len(actual)-1,*range(at,at+212),*range(first,first+16*len(names)),*range(string,string+sum(len(n)+1 for n in names))))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),literal)
  bad=bytearray(before);bad[string]^=1
  with self.assertRaises(ValueError):source.reorder_metadata(bytes(bad),bytearray(bad))
  self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=183,closed_metadata_bytes=27,closed_names=4,source_of_metadata_hypothesis='failed first link; fresh independent prediction subsequently verified')
