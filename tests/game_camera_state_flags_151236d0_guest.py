"""Actor/height flags with exact pointer reloads and bounded transition providers."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
from functools import lru_cache
from tools.experiments import game_camera_state_flags_151236d0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,SIZE,CAMERA,SECOND_CAMERA,PRIMARY,SECONDARY=0x151236D0,612,0x30000,0x40000,0x50000,0x51000
SYMS={**{'func_1515BA'+s:0x1515BA00+int(s,16)for s in('10','1C','48','54','80','AC')},'func_15124B18':0x15124B18}
RELEASE,TRANSITION,RESET=0x1515BA48,0x1515BA54,0x15124B18
WRAPPERS={0x1515BA1C:0x1515AF90,0x1515BA54:0x1515B674,0x1515BA80:0x1515B5F4,0x1515BAAC:0x1515B5F4}
@dataclass(frozen=True)
class Case:
 phase:int=0;flags:int=0;mode:int=0;secondary:int=1;word9C:int=0;byte95:int=0;byte137:int=0;velocity:int=0;identity:int=0;byte16:int=0;byte4E:int=0;y:int=0;limit:int=0;counter:int=0;slot:int=0;mutation:int=0;alias:int=0;seed:int=0
def addresses(c):return PRIMARY,(SECONDARY,PRIMARY,CAMERA+0x554,CAMERA+0x5E8)[c.alias]if c.secondary else 0
def fixture(c):
 m={STACK+i:(i*17+c.seed*7+0xA5)&255 for i in range(-512,512)}
 for base,n in((CAMERA,0x900),(SECOND_CAMERA,0x900),(PRIMARY,0x400),(SECONDARY,0x400)):
  m.update({base+i:(i*29+c.seed*11+0x35)&255 for i in range(n)})
 p,s=addresses(c)
 put(m,p+0x28,c.velocity);m[p+0x137]=c.byte137
 if s:
  put(m,s+0x9C,c.word9C);m[s+0x95]=c.byte95;put(m,s+8,c.identity,2);m[s+0x16]=c.byte16;m[s+0x4E]=c.byte4E
 put(m,CAMERA+0x3D0,p if s else 0);put(m,CAMERA+0x3D4,s);put(m,CAMERA+0x5F0,c.flags);put(m,CAMERA+0x2C,c.mode)
 put(m,CAMERA+0x2FC,c.y);put(m,CAMERA+0x360,c.limit);put(m,CAMERA+0x7B0,bits(-31.25));m[CAMERA+0x23C]=c.counter;m[CAMERA+0x23D]=c.slot
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def effect(m,c,target,arg,home):
 if c.mutation&1:
  put(m,CAMERA+0x5F0,read(m,CAMERA+0x5F0)^0xA5A5);m[CAMERA+0x23D]^=0x5A;put(m,CAMERA+0x7B0,bits(37.5))
 if c.mutation&2 and target in(RELEASE,TRANSITION):put(m,home,SECOND_CAMERA)
 if target==RESET:put(m,arg+0x348,bits(17.25))
def reference(initial,c,connected=False):
 m=dict(initial);calls=[];camera=CAMERA;home=STACK+c.phase
 def call(target,arg):
  calls.append((target,(arg,)))
  if connected and target in WRAPPERS:calls.append((WRAPPERS[target],(arg,)))
  effect(m,c,target,arg,home)
 flags=read(m,camera+0x5F0);old=flags&1;s=read(m,camera+0x3D4)
 if s:
  if read(m,s+0x9C)or(m[s+0x95]and not m[read(m,camera+0x3D0)+0x137]):flags|=0x40
  else:flags&=~0x40
  put(m,camera+0x5F0,flags)
  if floating(read(m,read(m,camera+0x3D0)+0x28))==0.:put(m,camera+0x5F0,read(m,camera+0x5F0)&~0x400)
  s=read(m,camera+0x3D4);flags=read(m,camera+0x5F0)
  if read(m,s+8,2)!=0 and not m[s+0x16]:flags|=8
  else:flags&=~8
  put(m,camera+0x5F0,flags);s=read(m,camera+0x3D4);flags=read(m,camera+0x5F0)
  if m[s+0x4E]==2:flags|=0x80
  else:flags&=~0x80
  put(m,camera+0x5F0,flags)
 flags=read(m,camera+0x5F0)
 if floating(read(m,camera+0x2FC))<=floating(read(m,camera+0x360))and read(m,camera+0x2C)!=0x100:flags|=1
 else:flags&=~1
 put(m,camera+0x5F0,flags);new=flags&1;slot=m[camera+0x23D]
 def release():
  nonlocal camera
  put(m,home,camera);call(RELEASE,slot);camera=read(m,home);put(m,camera+0x7B0,0)
 if m[camera+0x23C]:
  if new:call(0x1515BA80,slot)
  else:release()
 elif not old and new:
  call(0x1515BA80 if flags&4 or read(m,camera+0x2C)&0x40000 else 0x1515BAAC,slot)
 elif old and not new:
  if flags&4 or read(m,camera+0x2C)&0x40000:release()
  else:
   put(m,home,camera);call(TRANSITION,slot);camera=read(m,home);call(RESET,camera)
 elif new:call(0x1515BA1C,slot)
 else:call(0x1515BA10,slot)
 return public(m),calls
class Machine(FactoryOracle):
 def __init__(self,words,c,m,connected=False):
  self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(CAMERA,),connected=helper_code()if connected else None)
 def record_call(self,t):
  assert t in set(SYMS.values())|set(WRAPPERS.values()),hex(t);a=tuple(self.arguments(1));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  effect(self.memory,self.c,t,self.calls[-1][1][0],STACK+self.c.phase)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def programs():return[bound_blob(*payload(p,'func_151236D0'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/game_14FF90.c.o')]
@lru_cache(maxsize=1)
def helper_code():
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();code={}
 for address,n in((0x1515BA10,3),(0x1515BA1C,11),(0x1515BA48,3),(0x1515BA54,11),(0x1515BA80,11),(0x1515BAAC,13)):
  offset=address-0x15000000+0x2D4B0;raw=rom[offset:offset+4*n];at=elf_slot_offset(elf,address,4*n);assert elf[at:at+4*n]==raw
  code.update(zip(range(address,address+4*n,4),struct.unpack('>%dI'%n,raw)))
 return code
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.current_pc,m.delay_of)
def corpus():
 values=(0,0x80000000,bits(1.),bits(-1.),0x7F800000,0xFF800000,0x7FC12345)
 for flags,mode,secondary,heights,counter,mutation in itertools.product((0,1,4,5,0xFFFFFFFF),(0,0x100,0x101,0x40000),(0,1),range(7),(0,1),(0,1)):
  yield Case(flags=flags,mode=mode,secondary=secondary,y=values[heights],limit=values[(heights+2)%7],counter=counter,mutation=mutation,slot=(heights*43)&255,
   word9C=flags&1,byte95=mode&1,byte137=(flags>>2)&1,velocity=values[(heights+1)%7],identity=0xFFFF if flags&1 else 0,byte16=mode&1,byte4E=2 if flags&4 else 255,phase=(flags&1)*8)
 for i in range(256):
  for field in('byte95','byte137','byte16','byte4E','slot','counter'):
   yield replace(Case(flags=0x401,mode=0,word9C=0,byte95=1,velocity=bits(1.),identity=0x8000,byte4E=2,y=bits(1.),slot=255),**{field:i})
 for flags,mode,value,counter,mutation in itertools.product((0,1,4,5),(0,0x100,0x101,0x40000),values,(0,1),(0,1)):
  yield Case(flags=flags,mode=mode,y=value,limit=value,counter=counter,mutation=mutation,byte4E=2,identity=0x8000,slot=255)
 for alias,flags,mode,counter,mutation,phase in itertools.product((1,2,3),(0,1,4,5,0x440),(0,0x100,0x101,0x40000),(0,255),(0,1,2,3),(0,8)):
  yield Case(phase=phase,alias=alias,flags=flags,mode=mode,counter=counter,mutation=mutation,identity=0x8000,byte95=1,byte4E=2,velocity=bits(-1.),y=bits(-1.),slot=255)
def compare(words,c,connected=False):
 initial=fixture(c);expected=reference(initial,c,connected);machines=[]
 for w in words:
  m=Machine(w,c,dict(initial),connected).run();assert(public(m.memory),m.calls)==expected,(c,m.calls,expected[1]);machines.append(m)
 assert all(state(m)==state(machines[0])for m in machines[1:]),c
 return machines[0]
def static_reachable(w):
 pending=[0];seen=set();instructions=set()
 while pending:
  i=pending.pop()
  if i in seen:continue
  assert 0<=i<len(w);seen.add(i);instructions.add(i);word=w[i];op,rs,rt=word>>26,word>>21&31,word>>16&31
  if op in(4,5,20,21,1)or(op==17 and rs==8):
   jump=((word&65535)^32768)-32768;likely=op in(20,21)or(op==1 and rt&2)or(op==17 and rt&2)
   always=op in(4,20)and rs==rt;never=op in(5,21)and rs==rt
   if not never:instructions.add(i+1);pending.append(i+1+jump)
   if not always:
    if not likely:instructions.add(i+1)
    pending.append(i+2)
  elif op==3:instructions.add(i+1);pending.append(i+2)
  elif op==0 and word&63==8:assert rs==31;instructions.add(i+1)
  else:pending.append(i+1)
 return instructions
def run():
 streams=programs();assert streams[0]==streams[1]==streams[2];coverage=set();count=0
 for c in corpus():
  m=compare(streams,c);coverage.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+SIZE);count+=1
 reachable=static_reachable(streams[0]);assert coverage==reachable,sorted(reachable-coverage)
 connected_count=0;provider_visits=set();code=helper_code()
 for flags,mode,heights,counter,slot,phase in itertools.product((0,1,4,5),(0,0x100,0x40000),(-1.,0.,1.),(0,1),(0,128,255),(0,8)):
  c=Case(flags=flags,mode=mode,y=bits(heights),counter=counter,slot=slot,phase=phase);m=compare(streams,c,True);provider_visits.update(m.visits&code.keys());connected_count+=1
 assert set(code)-provider_visits=={0x1515BAD8,0x1515BADC},sorted(set(code)-provider_visits)
 examples=[Case(flags=f,mode=mode,y=bits(y),limit=0,counter=counter,mutation=3,slot=255,identity=0xFFFF,byte95=1)for f,mode,y,counter in itertools.product((0,1,4,5),(0,0x100,0x101,0x40000),(-1.,0.,1.),(0,1))]
 faults=0
 for c in examples[:8]+examples[-8:]:
  full=compare(streams,c)
  for cut in range(full.all_accesses):
   states=[]
   for w in streams:
    m=Machine(w,c,fixture(c));m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert states[0]==states[1]==states[2];faults+=1
 controls={6:0x30660004,64:0x4608503C,69:0x24010101,50:0x24010003,95:0,133:0}
 rejected=[]
 examples += [Case(flags=1,byte4E=value,slot=255)for value in(2,3)]
 for index,value in controls.items():
  changed=list(streams[0]);assert changed[index]!=value;changed[index]=value;failures=0
  for c in examples:
   initial=fixture(c)
   try:m=Machine(changed,c,dict(initial)).run()
   except AssertionError:raise
   failures+=(public(m.memory),m.calls)!=reference(initial,c)
  assert failures,index;rejected.append({'word':index,'failures':failures})
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'static_unreachable_words':sorted(set(range(153))-reachable),'all_reachable_words_covered':True,
 'access_fault_prefixes':faults,'effective_controls':rejected,'full_memory_private_bytes_registers_calls_and_accesses_equal':True,
 'original_wrapper_cases_per_stream':connected_count,'original_wrapper_words':len(code),'original_wrapper_covered_words':len(provider_visits),'wrapper_tail_alignment_words':2,
 'limits':'Transition providers are bounded ABI/effect contracts. Aliases2/3 and mutation bit2 incoming-home redirects are guest-only; no native frame, complete provider or gameplay claim.',
 'source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
