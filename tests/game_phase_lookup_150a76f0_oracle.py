"""Finite table-bit lookup and signed-arithmetic traps for the non-C ABI."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,os,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments import game_phase_lookup_150a76f0_restoration as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.check_game_data_layout import load_section
from tools.patch_generated_slice_ld import load_game_data_layout
from tools.tests.game_paired_float_approach_1505a250_oracle import bits
u32=lambda n:n&0xffffffff
signed=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
RETURN=0xdead0000
class ArithmeticFault(Exception):pass
class AlignmentFault(Exception):pass
@dataclass(frozen=True)
class Case:
 angle:int=0
 table:int=0x8009a220
 s7:int=128
 t9:int=256
 phase:int=0
 pattern:int=0
def table_words(root):
 rom=(root/'conker/conker.us.bin').read_bytes();layout=load_game_data_layout(root/'conker');start,base,_,_=layout;at=0x8009a220-base
 address,data=load_section(root/'conker/build/conker.us.elf','.game_data');assert address==base and data[at:at+260]==rom[start+at:start+at+260]
 return tuple(struct.unpack_from('>65I',rom,start+at))
def values(c,original):
 if c.pattern==0:return original
 if c.pattern==1:return tuple(bits(i*.125) for i in range(65))
 if c.pattern==2:return tuple(bits((i%7+1)*.25*(-1 if i&1 else 1)) for i in range(65))
 if c.pattern==3:return tuple(0x80000000 if i&1 else 0 for i in range(65))
 return tuple(0x3f000000|((i*0x010203+19)&0x7fffff) for i in range(65))
def fixture(c,original):
 m={}
 for i,v in enumerate(values(c,original)):put(m,u32(c.table+i*4),v)
 return m
def arithmetic(a,b,subtract=False):
 n=signed(a)-signed(b) if subtract else signed(a)+signed(b)
 if not -2147483648<=n<=2147483647:raise ArithmeticFault
 return u32(n)
def reference(c,m):
 phase=c.angle&255
 # The T9 subtraction executes in a branch delay slot even in quadrant three.
 if phase>=129:
  difference=arithmetic(c.t9,phase,True);index=phase-128 if phase<=192 else difference
 elif phase>=65:index=arithmetic(c.s7,phase,True)
 else:index=phase
 address=arithmetic(c.table,u32(index<<2))
 if address&3:raise AlignmentFault
 word=read(m,address);answer=word^(0x80000000 if 65<=phase<=192 else 0)
 return answer,word if phase<=64 else address,phase,int(phase<=192)
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=source.ENTRY,connected=None):
  super().__init__(words,initial,c,entry=entry,arguments=(),connected=connected)
  self.r[12]=u32(c.angle);self.r[22]=u32(c.table);self.r[23]=u32(c.s7);self.r[25]=u32(c.t9);self.r[2]=RETURN;self.r[31]=0x12345678;self.before=self.r[:];self.saved_f=self.f[20:];self.initial_f=self.f[:]
 def execute(self,w):
  op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
  if op==0 and fn in (32,34):self.r[rd]=arithmetic(self.r[rs],self.r[rt],fn==34)
  elif op==8:self.r[rt]=arithmetic(self.r[rs],((w&65535)^32768)-32768)
  elif op==17 and rs==16 and fn==7:self.f[w>>6&31]=self.f[rd]^0x80000000
  else:return super().execute(w)
  self.r[0]=0
 def get(self,p,n):
  if n==4 and p&3:raise AlignmentFault
  return super().get(p,n)
 def record_call(self,t):raise AssertionError('The helper has no calls')
 def hook(self,t):raise AssertionError('The helper has no provider hooks')
def check(machine,initial,c):
 answer,v3,t4,at=reference(c,initial)
 assert (machine.f[8],machine.r[3],machine.r[12],machine.r[1])==(answer,v3,t4,at),c
 assert machine.memory==initial and not machine.calls,c
 assert all(machine.r[i]==machine.before[i] for i in range(32) if i not in (1,3,12)),c
 assert all(machine.f[i]==machine.initial_f[i] for i in range(32) if i!=8),c
def main():
 root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD;original=table_words(root);programs=[list(struct.unpack('>29I',payload(out/f,source.FUNCTION)[0])) for f in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[1]==programs[2];seen=set();count=0
 for phase,pattern,upper,stack in itertools.product(range(256),range(5),(0,0xa5b60000),(0,8)):
  c=Case(angle=phase|upper,pattern=pattern,phase=stack);initial=fixture(c,original)
  for words in programs:machine=Oracle(words,initial,c);machine.run();check(machine,initial,c);seen.update(machine.visits)
  count+=1
 for angle,base in itertools.product((0,64,65,128,129,192,193,255),(0x33007ffc,0xffffff80)):
  c=Case(angle=angle,table=base,pattern=4);initial=fixture(c,original)
  for words in programs:machine=Oracle(words,initial,c);machine.run();check(machine,initial,c)
  count+=1
 assert len(seen)==29
 faults=0
 fault_cases=(Case(angle=1,table=0x7ffffffc),Case(angle=64,table=0x7fffff00),Case(angle=65,s7=0x80000000),Case(angle=129,t9=0x80000000),Case(angle=192,t9=0x80000000),Case(angle=193,t9=0x80000000),Case(angle=0,table=0x70002))
 for c in fault_cases:
  initial=fixture(c,original)
  try:reference(c,initial)
  except (ArithmeticFault,AlignmentFault) as error:kind=type(error)
  else:raise AssertionError('Ineffective fault fixture')
  for words in programs:
   machine=Oracle(words,initial,c)
   try:machine.run()
   except kind:pass
   else:raise AssertionError('Missing arithmetic/alignment fault')
   assert machine.memory==initial
  faults+=1
 rom=(root/'conker/conker.us.bin').read_bytes();windows=((0x150a75ac,0x150a75bc),(0x150a75e0,0x150a75f0),(0x150a75fc,0x150a760c),(0x150a7614,0x150a7624),(0x150a762c,0x150a763c),(0x150a7644,0x150a7654));callers=0
 for (pc,end),angle,pattern in itertools.product(windows,range(256),(0,1)):
  c=Case(angle=angle,pattern=pattern);initial=fixture(c,original);window=struct.unpack_from('>4I',rom,pc-0x15000000+0x2d4b0)
  for words in programs:
   code=dict(zip(range(source.ENTRY,source.ENTRY+116,4),words));code[end]=0;machine=Oracle(window,initial,c,entry=pc,connected=code);machine.code=WindowCode(machine.code,machine);machine.code.ends=(end,)
   try:machine.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing computed continuation boundary')
   machine.before[2]=end;check(machine,initial,c)
  callers+=1
 prefixes=0
 for angle in range(256):
  c=Case(angle=angle);initial=fixture(c,original);states=[]
  for words in programs:
   machine=Oracle(words,initial,c);machine.cut=0
   try:machine.run()
   except AccessBoundary:pass
   else:raise AssertionError('Missing fired table-read boundary')
   states.append((machine.r,machine.f,machine.memory,machine.trace))
  assert states[0]==states[1]==states[2];prefixes+=1
 # Deliberate instruction controls must fail the independent protocol model.
 base=programs[0];controls={}
 modified=base[:];modified[0]=(modified[0]&0xffff0000)|127;controls['wrong_phase_mask']=modified
 modified=base[:];modified[1]=(modified[1]&0xffff0000)|64;controls['wrong_first_boundary']=modified
 controls['omit_sign_reversal']=[0x46004206 if w==0x46004207 else w for w in base]
 controls['wrong_return_register']=[0x03e00008 if w==0x00400008 else w for w in base]
 controls['wrong_stride']=[w+64 if w==0x00031880 or w==0x000c1880 else w for w in base]
 killed=set()
 for angle in range(256):
  c=Case(angle=angle,pattern=1);initial=fixture(c,original)
  for name,words in controls.items():
   if name in killed:continue
   machine=Oracle(words,initial,c)
   try:machine.run();check(machine,initial,c)
   except (AssertionError,KeyError):killed.add(name)
 assert killed==set(controls)
 report=dict(cases=count,observed_words=len(seen),computed_return_windows=6,caller_cases=callers,arithmetic_alignment_faults=faults,full_state_access_prefixes=prefixes,negative_controls=sorted(killed),no_memory_writes=True,raw_register_protocol=True,native_c_not_applicable=True,nonfinite_fcsr_not_qualified=True)
 (out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
