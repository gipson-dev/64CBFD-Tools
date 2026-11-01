"""Packed arguments, original descriptor providers and bounded allocation/copy services."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,random,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_classifier_candidates import sections
ENTRY,F=0x1510A930,'func_1510A930'
CREATE,CTOR,ALLOC,COPY=0x15169968,0x15169900,0x15167A68,0x10023A10
OUTPUT=0x30000
SYMS=dict(D_800917EC=0x800917EC,D_800A26A0=0x800A26A0,func_15169968=CREATE)
u32=lambda x:x&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 args:tuple=(1,2,3)
 result:int=OUTPUT
 phase:int=0
 seed:int=0
 mutation:int=0
 connected:bool=False
 scalar:int=0x3F800000

def fields(args,scalar,asset):
 a,b,c=args;total=u32(a+b+c)
 return [(0,asset,4),(8,u32(a<<16)|b,4),(12,u32(c<<16)|total,4),(16,10000,4),(20,total,2),(22,0,2),(24,0,2),(28,0x43640000,4),(32,scalar,4),(36,0,2),(38,0,2),(40,0x18FC,2),(42,0x1A12,2),(44,64,2),(46,32,2),*[(48+i,v,1)for i,v in enumerate((10,1,255,255,255,0,7,17))],(57,0,1)]
DEFINED=tuple(sorted({a+i for a,v,n in fields((1,2,3),0,0)for i in range(n)}));assert len(DEFINED)==51
def packet(c):return STACK+c.phase-60
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m):return {a:v for a,v in m.items()if not STACK-512<=a<STACK+768}
def corpus():
 values=(0,1,0xFFFF,0x10000,0x7FFFFFFF,0x80000000,0xFFFFFFFF)
 rows=[(v,1,3)for v in values]+[(1,v,3)for v in values]+[(1,2,v)for v in values]+[(v,v,v)for v in values]
 rng=random.Random(0x1510A930);rows.extend(tuple(rng.getrandbits(32)for _ in range(3))for i in range(64));return list(dict.fromkeys(rows))
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,768)}
 for base in (OUTPUT,s['D_800A26A0']):m.update({base+i:(i*29+c.seed*11+0x59)&255 for i in range(-8,128)})
 put(m,s['D_800A26A0'],c.scalar);return m
def effect(m,c,s):
 if c.mutation:
  put(m,s['D_800A26A0'],0xBF800000);put(m,packet(c)+20,0xFEDC,2);m[packet(c)+4]^=0x55
def reference(initial,c,s=SYMS):
 m=dict(initial);p=packet(c)
 # The asset publication precedes the scalar read; all remaining field stores follow it.
 put(m,p,s['D_800917EC']);scalar=read(m,s['D_800A26A0'])
 for at,value,n in fields(c.args,scalar,s['D_800917EC'])[1:]:put(m,p+at,value,n)
 observed=data(m,p,60);calls=[(s['func_15169968'],(p,))]
 if c.connected:calls.extend(((CTOR,(p,255)),(ALLOC,(94,0,76,0,255,1))))
 effect(m,c,s)
 if c.result:
  if c.connected:calls.append((COPY,(p,c.result+16,60)))
  copy=data(m,p,60)
  for i,b in enumerate(copy):m[c.result+16+i]=b
 return m,calls,[observed]
class Oracle(FactoryOracle):
 def __init__(self,program,initial,c,s=SYMS,entry=ENTRY,connected=None):
  self.observed=[];super().__init__(program,initial,c,entry=entry,s=s,connected=connected,arguments=c.args);self.before_f=self.f[:]
 def record_call(self,t):
  counts={ENTRY:3,self.syms['func_15169968']:1,CTOR:2,ALLOC:6,COPY:3};assert t in counts,hex(t)
  args=tuple(self.arguments(counts[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==self.syms['func_15169968']:self.observed.append(data(self.memory,args[0],60))
 def hook(self,t):
  c=self.case;args=self.calls[-1][1]
  if t in (self.syms['func_15169968'],ALLOC):
   assert args==((packet(c),)if t==self.syms['func_15169968']else(94,0,76,0,255,1))
   effect(self.memory,c,self.syms);answer=c.result
   if t==self.syms['func_15169968']and c.result:
    copied=data(self.memory,packet(c),60)
    for i,b in enumerate(copied):self.memory[c.result+16+i]=b
  else:
   assert t==COPY and args==(packet(c),c.result+16,60)
   copied=data(self.memory,args[0],args[2])
   for i,b in enumerate(copied):self.memory[args[1]+i]=b
   answer=0xAABBCCDD
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(answer)
def linked(obj,label,s=SYMS,entry=ENTRY):
 p=o/label;p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
 return list(struct.unpack('>57I',sections(p.with_suffix('.elf'))['.text'][1][:228]))
def configure(root,output,obj):
 global r,o,rom,objects,programs
 r,o=root,output;rom=(r/'conker/conker.us.bin').read_bytes();stage=r/'conker/build/game-packed-argument-descriptor-1510A930-match'
 objects=(stage/('original-'+F+'.o'),obj);programs=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]
def helpers():
 code={}
 for entry,off,n in ((CREATE,0x196E18,8),(CTOR,0x196DB0,26)):code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,off)))
 return code
def state(m):return (m.r,m.f,m.memory,m.trace,m.calls,m.events,m.observed,m.hi,m.lo)
def verify(m,initial,c,s=SYMS):
 expected,calls,obs=reference(initial,c,s)
 assert (public(m.memory),m.calls,m.observed,m.r[2])==(public(expected),calls,obs,c.result),c
 assert data(m.memory,packet(c),60)==data(expected,packet(c),60)
 assert m.r[29]==m.before[29]and all(m.r[i]==m.before[i]for i in (*range(16,24),28,30,31))and m.f[20:]==m.before_f[20:]
def run_suite():
 seen=set();count=connected_count=0
 for args,result,phase,mutation,connected in itertools.product(corpus(),(0,OUTPUT),(0,8),(0,1),(False,True)):
  c=Case(args,result,phase,args[0]&255,mutation,connected,(0x80000000,0x3F800000,0x7FC12345)[args[1]%3]);initial=fixture(c);pair=[]
  for program in programs:
   m=Oracle(program,initial,c,connected=helpers()if connected else None);m.run();verify(m,initial,c);pair.append(m);seen.update(m.visits)
  assert state(pair[0])==state(pair[1]);count+=1;connected_count+=connected
 root=seen&set(range(ENTRY,ENTRY+228,4));assert len(root)==57
 return dict(cases=count,executions=count*2,reachable_words=57,frame=96,descriptor_bytes=60,defined_bytes=51,unwritten_bytes=9,connected_original_provider_cases=connected_count,original_provider_words=34,allocation_and_bcopy_are_bounded_services=True,return_pointer_and_null_forwarded=True,all_callee_saved_state_preserved=True,portable_C_padding_or_fault_claimed=False)
def run_callers():
 pc=0x15026034;end=0x150265B4;window=list(struct.unpack_from('>8I',rom,0x534E4));count=0
 assert window[-2:]==[0x10000159,0x24020001]
 for first,remaining,third,consumed,result,phase in itertools.product((0,0x80000000,0xFFFFFFFF),(0,17,0xFFFFFFFF),(0,0x10000),(0,0xFFFFFFFF),(0,OUTPUT),(0,8)):
  args=(first,u32(remaining-consumed-third-first),third);c=Case(args,result,phase,connected=True);initial=fixture(c);put(initial,STACK+phase+0x164,consumed);want,calls,obs=reference(initial,c)
  for program in programs:
   code=helpers();code.update(zip(range(ENTRY,ENTRY+228,4),program));code[end]=0;m=Oracle(window,initial,c,entry=pc,connected=code);m.r[16]=first;m.r[17]=remaining;m.r[6]=third
   m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller boundary not reached')
   assert (public(m.memory),m.calls,m.observed,m.r[2])==(public(want),[(ENTRY,args)]+calls,obs,1)
  count+=1
 return dict(cases=count,executions=count*2,entry=hex(pc),JAL='0x15026044',JAL_ROM='0x534F4',static_words=8,full_word_arguments=True,delay_slot_supplies_first_argument=True,original_caller_ignores_pointer_and_publishes_one=True,full_parent_runtime_claimed=False)
def run_rebases_prefixes_aliases():
 rebases=prefixes=aliases=0
 profiles=[(0x1ABC0000,dict(D_800917EC=0x31008000,D_800A26A0=0x41007FFC,func_15169968=0x1A008000)),(0x151FFFF0,dict(D_800917EC=0x3200FFFC,D_800A26A0=0x42008000,func_15169968=0x15008000))]
 for i,(entry,s)in enumerate(profiles):
  ps=[linked(p,'rebase-%d-%d'%(i,k),s,entry)for k,p in enumerate(objects)];assert ps[0]==ps[1]
  for result,phase,mutation in itertools.product((0,OUTPUT),(0,8),(0,1)):
   c=Case((0xFFFFFFFF,0x80000000,0x10000),result,phase,mutation=mutation)
   for program in ps:m=Oracle(program,fixture(c,s),c,s,entry);m.run();verify(m,fixture(c,s),c,s);rebases+=1
 for c in (Case(),Case(result=0,connected=True),Case(phase=8,mutation=1,connected=True)):
  initial=fixture(c);complete=Oracle(programs[0],initial,c,connected=helpers()if c.connected else None);complete.run()
  for cut in range(complete.all_accesses):
   pair=[]
   for program in programs:
    m=Oracle(program,initial,c,connected=helpers()if c.connected else None);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access prefix did not fire')
    pair.append(state(m))
   assert pair[0]==pair[1];prefixes+=1
 for at in (0,20,44):
  c=Case((0xFFFFFFFF,0x10000,0x80000000));s=dict(SYMS,D_800A26A0=packet(c)+at);ps=[linked(p,'alias-%d-%d'%(at,k),s)for k,p in enumerate(objects)];pair=[]
  for program in ps:m=Oracle(program,fixture(c,s),c,s);m.run();verify(m,fixture(c,s),c,s);pair.append(state(m))
  assert pair[0]==pair[1];aliases+=1
 return dict(independent_rebase_profiles=2,rebase_executions=rebases,signed_low16_carries=True,fired_prefix_cases=prefixes,guest_descriptor_scalar_aliases=aliases,portable_C_fault_or_alias_claimed=False)
