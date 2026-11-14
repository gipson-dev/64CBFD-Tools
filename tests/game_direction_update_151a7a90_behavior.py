from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct
from tools.tests import game_attached_direction_151a87f8_behavior as child
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_paired_float_approach_1505a250_oracle import floating
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,EVENT,RANDOM,CROSS,FREE=0x151a7a90,0x151a8340,0x150ada68,0x151450b4,0x1516972c
TABLE_A,TABLE_B,GATE_A,GATE_B=0x8008f940,0x8008f948,0x22000000,0x23000000
TIME,TICKS,DEPTH,NEXTS=0x800be9a4,0x800be9e4,0x800dd190,0x800dd198
VERTICES,ALTERNATE,NEXT,NEXT2=0x70000,0x71000,0x72000,0x73000
fb=child.fb;u32=child.u32;signed8=lambda v:((v&255)^128)-128;signed16=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case(child.Case):
 flags:int=2
 first:int=-1
 second:int=-1
 first_answer:int=1
 second_answer:int=1
 lifetime:int=10
 ticks:int=1
 count:int=3
 timer:float=1.
 timestep:float=.25
 minimum:float=2.
 range:float=4.
 sample:float=.5
 vertices:int=VERTICES
 coupled:bool=False
 real_cross:bool=False
def homes(c,raw=False):
 base=STACK+c.phase-0x68
 return (base+0x38,base+0x44,base+0x50) if raw else (base+0x3c,base+0x48,base+0x54)
def fixture(c):
 m=child.fixture(c)
 for p,shift in ((c.vertices,0),(ALTERNATE,1)):
  for i in range(5):
   for j,v in enumerate((.5+i+shift,-1.+.25*i,.75-.125*i,-10.,-20.,-30.)):put(m,p+24*i+4*j,fb(v))
 m[c.record]=0x2d;put(m,c.record+8,NEXT);put(m,c.record+16,c.lifetime,2);put(m,c.record+18,c.count,2);put(m,c.record+20,fb(c.minimum));put(m,c.record+24,fb(c.range));m[c.record+28]=c.flags;put(m,c.record+32,0x87654321);m[c.record+44]=c.first&255;m[c.record+45]=c.second&255;put(m,c.record+100,c.vertices);put(m,c.record+104,fb(c.timer))
 put(m,TIME,fb(c.timestep));put(m,TICKS,c.ticks);m[DEPTH]=1;put(m,NEXTS+4,NEXT);put(m,NEXTS+8,NEXT2)
 put(m,TABLE_A,GATE_A);put(m,TABLE_A+4,child.ENTRY if c.coupled else GATE_A+4);put(m,TABLE_B,GATE_B);put(m,TABLE_B+4,GATE_B+4);put(m,0x8008bdcc,ENTRY)
 return m
def vector(m,p):return tuple(read(m,p+4*i) for i in range(3))
def cross_values(a,b):
 f=lambda v:floating(v)
 return tuple(fb(f(fb(f(a[i])*f(b[j])))-f(fb(f(a[j])*f(b[i])))) for i,j in ((1,2),(2,0),(0,1)))
def effect(m,c,stage):
 if not c.mutation&1:return
 p=c.record
 if stage=='a':m[p+45]=0;put(m,p+104,fb(-.5));put(m,TIME,fb(.5))
 elif stage=='b':m[p+28]|=2;put(m,p+18,2,2)
 elif stage=='event':put(m,p+18,2,2);put(m,p+104,fb(31.));put(m,p+20,fb(3.));put(m,p+24,fb(6.))
 elif stage=='random':
  put(m,p+20,fb(5.));put(m,p+24,fb(7.));put(m,p+104,fb(99.));m[p+28]|=2
 elif stage=='cross':
  for i,v in enumerate((7.5,-2.25,.5)):put(m,p+48+4*i,fb(v))
  put(m,p+88,fb(.5));put(m,p+18,2,2);put(m,p+100,ALTERNATE)
 elif stage=='free':m[p+1]=0xee;m[DEPTH]=2;put(m,NEXTS+8,NEXT2)
def apply_cross(m,c,a):
 delta,side,result=a;values=cross_values(vector(m,delta),vector(m,side))
 for i,v in enumerate(values):put(m,result+4*i,v)
 if not c.real_cross:
  effect(m,c,'cross')
  if c.mutation&1:put(m,delta,fb(floating(read(m,delta))+.25));put(m,side+8,fb(floating(read(m,side+8))-.5))
def reference(initial,c,raw=False):
 m=dict(initial);calls=[];obs=[];p=c.record;delta,side,cross=homes(c,raw);dead=False
 def call(t,a,stage,observed=None):
  calls.append((t,tuple(map(u32,a))))
  if observed is not None:obs.append((t,observed))
  effect(m,c,stage)
 if m[p+28]&1:
  put(m,p+16,read(m,p+16,2)-read(m,TICKS),2);dead=signed16(read(m,p+16,2))<0
 first=signed8(m[p+44])
 if first!=-1 and not dead:
  t=read(m,TABLE_A+4*first);calls.append((t,(p,)))
  if t==child.ENTRY:
   m,cc,co,answer=child.reference(m,replace(c,phase=c.phase-0x68));calls+=cc;obs+=co;dead=not answer
  else:effect(m,c,'a');dead=u32(c.first_answer)==0
 second=signed8(m[p+45])
 if second!=-1 and not dead:call(read(m,TABLE_B+4*second),(p,),'b');dead=u32(c.second_answer)==0
 if not dead:
  put(m,p+104,fb(floating(read(m,p+104))-floating(read(m,TIME))))
  if floating(read(m,p+104))<0:
   call(EVENT,(p,0,u32(signed16(signed16(read(m,p+18,2))-1)),read(m,p+32),100),'event')
   call(RANDOM,(),'random',read(m,p+104));put(m,p+104,fb(floating(fb(c.sample*floating(read(m,p+24))))+floating(read(m,p+20))))
  if m[p+28]&2:
   for i in range(3):put(m,delta+4*i,fb(floating(read(m,p+60+4*i))-floating(read(m,p+48+4*i))));put(m,side+4*i,read(m,p+72+4*i))
   a=(delta,side,cross);calls.append((CROSS,a));obs.append((CROSS,(vector(m,delta),vector(m,side))));apply_cross(m,c,a)
   for i in range(3):put(m,cross+4*i,fb(floating(read(m,cross+4*i))*floating(read(m,p+88))))
   index=0;v=read(m,p+100)
   if signed16(read(m,p+18,2))>0:
    while True:
     x,y,z=map(floating,vector(m,v))
     for axis in range(3):
      value=floating(fb(floating(read(m,p+48+4*axis))+floating(fb(x*floating(read(m,cross+4*axis))))));value=floating(fb(value+floating(fb(y*floating(read(m,side+4*axis))))));value=fb(value+floating(fb(z*floating(read(m,delta+4*axis)))));put(m,v+12+4*axis,value)
     index+=1;v+=24;assert index<=5
     if not index<signed16(read(m,p+18,2)):break
 if dead:call(FREE,(p,),'free')
 return m,calls,obs
class Oracle(child.Oracle):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None):super().__init__(words,initial,c,entry=entry,connected=connected)
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in (2,60):
   if fn==2:self.f[fd]=fb(floating(self.f[fs])*floating(self.f[ft]))
   else:self.condition=floating(self.f[fs])<floating(self.f[ft])
   self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  counts={ENTRY:1,EVENT:5,RANDOM:0,CROSS:3,FREE:1,GATE_A:1,GATE_A+4:1,GATE_B:1,GATE_B+4:1}
  if t not in counts:return super().record_call(t)
  a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==RANDOM:self.observed.append((t,read(self.memory,self.case.record+104)))
  if t==CROSS:self.observed.append((t,(vector(self.memory,a[0]),vector(self.memory,a[1]))))
 def hook(self,t):
  if t in (child.TRANSFORM,child.COLLISION,child.HIT,child.LENGTH,child.ORIENT):return super().hook(t)
  m=self.memory;c=self.case;a=self.calls[-1][1];answer=0
  if t in (GATE_A,GATE_A+4):effect(m,c,'a');answer=c.first_answer
  elif t in (GATE_B,GATE_B+4):effect(m,c,'b');answer=c.second_answer
  elif t==EVENT:effect(m,c,'event')
  elif t==RANDOM:effect(m,c,'random');answer=fb(c.sample)
  elif t==CROSS:apply_cross(m,c,a)
  else:assert t==FREE,hex(t);effect(m,c,'free')
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=u32(0xa5000000+reg)
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=u32(answer);self.hi,self.lo=0xa5000010,0xa5000011
  if t==RANDOM:self.f[0]=answer
def cases():
 for i,(flags,first,second,count,mutation,phase) in enumerate(itertools.product((0,1,2,3),(-1,0,1),(-1,0,1),(-1,0,1,3),(0,1),(0,8))):
  yield Case(flags=flags,first=first,second=second,count=count,mutation=mutation,phase=phase,lifetime=(0,1,-32768)[i%3],ticks=(0,1,65535,0x80000000)[i%4],timer=(0.,.25,.75)[i%3],first_answer=(0,1,256,0x80000000)[i%4],second_answer=(0,1,256,0x80000000)[(i//4)%4],sample=(.25,.5)[(i//3)%2])
 for lifetime,ticks,flags in itertools.product((-32768,-1,0,32767),(0,1,65535,0x80000000),(1,3)):
  yield Case(lifetime=lifetime,ticks=ticks,flags=flags)
 for count,timer,mutation,phase in itertools.product((-32768,-1,0,1,3),(-.25,.25),(0,1),(0,8)):
  yield Case(count=count,timer=timer,mutation=mutation,phase=phase)
 for answer,mutation in itertools.product((0,1,256,0x80000000),(0,1)):yield Case(first=0,first_answer=answer,mutation=mutation)
 yield Case(timer=-0.,timestep=0.)
def machine_state(m):return child.state(m)
def verify(m,initial,c,raw=False):
 expected,calls,obs=reference(initial,c,raw);assert (child.public(m.memory),m.calls,m.observed)==(child.public(expected),calls,obs),c
 assert bytes(m.memory[c.record+i] for i in range(108))==bytes(expected[c.record+i] for i in range(108)),c
 if not(c.coupled or c.vertices!=VERTICES):
  for p in (VERTICES,ALTERNATE):assert bytes(m.memory[p+i] for i in range(120))==bytes(expected[p+i] for i in range(120)),c
 assert m.r[29]==m.before[29] and all(m.r[i]==m.before[i] for i in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
def load():
 r=Path.cwd();o=r/'conker/build/game-direction-update-151a7a90-screen';sy={a[1]:a[2][1] for a in symbol_rows((r/'conker/build/conker.us.elf').read_bytes())};programs=[bound_blob(*payload(o/f,'func_151A7A90'),sy) for f in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2] and all(len(p)==183 for p in programs)
 rom=(r/'conker/conker.us.bin').read_bytes();cross,refs=payload(r/'conker/build/src/game_16EE20.c.o','func_151450B4');assert len(cross)==116 and not refs and cross==rom[0x172564:0x1725d8];childwords=struct.unpack_from('>138I',rom,0x1d5ca8)
 childcode=dict(zip(range(child.ENTRY,child.ENTRY+552,4),childwords));crosscode=dict(zip(range(CROSS,CROSS+116,4),struct.unpack('>29I',cross)))
 return rom,programs,childcode,crosscode
def run():
 rom,programs,childcode,crosscode=load();count=0;seen=set()
 for c in cases():
  initial=fixture(c);states=[]
  for i,p in enumerate(programs):m=Oracle(p,initial,c);m.run();verify(m,initial,c,raw=i==1);states.append(machine_state(m));seen.update(pc for pc in m.visits if ENTRY<=pc<ENTRY+732)
  assert states[0]==states[2];count+=1
 missing=set(range(ENTRY,ENTRY+732,4))-seen;assert not missing,[hex(a) for a in sorted(missing)]
 coupled=0
 for active,length,matrix,mutation,real_cross,phase in itertools.product((0,1),(0.,2.5),(0,1),(0,1),(0,1),(0,8)):
  c=Case(first=1,coupled=True,active=active,length=length,matrix=matrix,mutation=mutation,real_cross=bool(real_cross),phase=phase);initial=fixture(c);code=dict(childcode)
  if c.real_cross:code.update(crosscode)
  states=[]
  for i,p in enumerate(programs):m=Oracle(p,initial,c,connected=code);m.run();verify(m,initial,c,raw=i==1);states.append(machine_state(m))
  assert states[0]==states[2];coupled+=1
 aliases=0
 for kind,phase,real_cross in itertools.product(range(3),(0,8),(False,True)):
  c=Case(phase=phase,real_cross=real_cross,count=2 if kind==1 else 3)
  if kind==0:c=replace(c,vertices=c.record+4)
  elif kind==1:c=replace(c,vertices=STACK+phase-0x68+0x28)
  else:c=replace(c,record=STACK+phase+0x180)
  initial=fixture(c)
  if kind==0:
   for i in range(3):put(initial,c.vertices+4*i,fb(0.))
  expected,_,_=reference(initial,c);states=[]
  for p in (programs[0],programs[2]):
   m=Oracle(p,initial,c,connected=crosscode if real_cross else None);m.run();verify(m,initial,c)
   assert bytes(m.memory[c.vertices+i] for i in range(48))==bytes(expected[c.vertices+i] for i in range(48)),(kind,c)
   states.append(machine_state(m))
  assert states[0]==states[1];aliases+=1
 caller_cases=0;pc,end=0x15167164,0x15167188
 window=struct.unpack_from('>9I',rom,pc-0x15000000+0x2d4b0)
 assert struct.unpack_from('>I',rom,0x23088c)[0]==ENTRY
 for dead,mutation,phase,callback in itertools.product((0,1),(0,1),(0,8),(-1,0)):
  c=Case(flags=3,lifetime=0 if dead else 10,mutation=mutation,phase=phase,first=callback);initial=fixture(c)
  expected_initial=dict(initial);put(expected_initial,NEXTS+4,read(initial,c.record+8))
  states=[]
  for i,p in enumerate(programs):
   expected,calls,obs=reference(expected_initial,c,raw=i==1);code=dict(zip(range(ENTRY,ENTRY+732,4),p));code[end]=0
   m=Oracle(window,initial,c,entry=pc,connected=code);m.r[16]=c.record;m.r[18]=0x8008bdcc;m.r[19]=DEPTH;m.r[20]=NEXTS;m.r[17]=NEXTS+4;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('missing caller boundary')
   assert (child.public(m.memory),m.calls,m.observed,m.r[16])==(child.public(expected),[(ENTRY,(c.record,))]+calls,obs,read(expected,NEXTS+4*signed8(expected[DEPTH]))),c
   assert m.r[29]==STACK+c.phase
   states.append(machine_state(m))
  assert states[0]==states[2];caller_cases+=1
 prefixes=0
 for c in (Case(mutation=1),Case(flags=3,lifetime=0),Case(first=0,first_answer=0),Case(timer=-.25,mutation=1)):
  initial=fixture(c);whole=Oracle(programs[0],initial,c);whole.run()
  for cut in range(whole.all_accesses):
   states=[]
   for p in (programs[0],programs[2]):
    m=Oracle(p,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('missing fired boundary')
    states.append(machine_state(m))
   assert states[0]==states[1];prefixes+=1
 report=dict(cases=count,coupled_child_cases=coupled,caller_window_cases=caller_cases,guest_alias_cases=aliases,access_prefixes=prefixes,observed_words=len(seen),helpers_modeled=True,actual_child_words=138,actual_cross_words=29,raw_temporary_homes_separate=True)
 out=Path.cwd()/'conker/build/game-direction-update-151a7a90-screen';(out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':run()
