"""Camera transition gates, ordered guest accesses and connected small helpers."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct,sys
from tools.experiments import game_camera_mode_gates_1512317c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_camera_position_151247c0_guest import spring
from tools.tests.game_camera_state_flags_151236d0_guest import static_reachable
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY,SIZE,CAMERA,PRIMARY,SECONDARY,OTHER,INPUT,ALTINPUT=0x1512317C,908,0x30000,0x50000,0x51000,0x52000,0x60000,0x60010
QUERY,SAVE,RESTORE,ACTIVATE,SPRING,INDEX,RESET=0x15125490,0x15123934,0x151239CC,0x1511FC60,0x150495B0,0x15125394,0x15124B18
SYMS={f'func_{n:08X}':n for n in(QUERY,SAVE,RESTORE,ACTIVATE,SPRING,INDEX,RESET)}
@dataclass(frozen=True)
class Case:
 phase:int=0;mode:int=0;flags:int=0;old:int=0;stunned:int=0;state:int=0;value:int=0;water:int=0;secondary_flags:int=0;actor65:int=0;query:int=0;health:int=1;kind:int=0;speed:int=0;secondary_ac:int=0;input:int=16;edge:int=16;slot:int=0;substate:int=0;mutation:int=0;alias:int=0;pattern:int=0;dt:int=0x3E000000

def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 for base,n in((CAMERA,0xA00),(PRIMARY,0x400),(SECONDARY,0x400),(OTHER,0x400),(INPUT,32)):
  m.update({base+i:(i*29+0x35)&255 for i in range(n)})
 p=CAMERA+0x500 if c.alias==4 else PRIMARY;s=p if c.alias==1 else SECONDARY
 for a in(p,s,OTHER):
  for at,v in((0x104,c.stunned),(0xAD,c.water),(0x65,c.actor65),(0x1CA,c.health),(0x4E,c.kind),(0x1AC,c.secondary_ac)):m[a+at]=v
  put(m,a+0x28,c.value);put(m,a+0x3C,c.speed);put(m,a+0x9C,c.secondary_flags)
 m[OTHER+0x1CA]=c.pattern&1;put(m,OTHER+0x3C,bits(16.))
 ip=CAMERA+0x36A if c.alias==2 else CAMERA+0x20E if c.alias==3 else INPUT
 for at,v in((0x2C,c.mode),(0x84,c.flags),(0x5F0,c.old),(0x3D0,p),(0x3D4,s),(0x36C,ip),(0x134,0x12345678)):
  put(m,CAMERA+at,v)
 m[CAMERA+0x23E]=c.state
 for at,v in((0x36A,c.edge),(0x20E,c.slot),(0x73C,c.substate),(0,3),(0x1B4,5),(0x1E0,7),(4,2),(0x1B8,9),(0x1E4,11)):
  put(m,CAMERA+at,v,2)
 for at,v in((0x34,0x20),(0x8C,0x101),(0xE4,8),(0x13C,0x87654321),(0x74C,bits((2.,-.5,1.,0.)[c.pattern%4])),(0x754,bits((-1.,2.,-.25,0.)[c.pattern%4])),(0x79C,bits(.5)),(0x7A0,bits(-.5)),(0x7B4,c.dt)):
  put(m,CAMERA+at,v)
 put(m,ip,c.input,2);put(m,ALTINPUT,c.input^16,2)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def effect(m,c,t):
 if t==QUERY and c.mutation&1:put(m,CAMERA+0x3D0,OTHER)
 if t==RESET and c.mutation&2:
  put(m,CAMERA+0x3D4,OTHER);put(m,CAMERA+0x73C,3,2);put(m,CAMERA+0x2C,0x100 if c.pattern&1 else 0x20);put(m,CAMERA+0x36C,ALTINPUT)
 if t==SPRING and c.mutation&4:put(m,CAMERA+0x7B4,bits(.5))
 if t==ACTIVATE:put(m,CAMERA+0x7C8,0x13579BDF)
def index_effect(m):
 mode=read(m,CAMERA+0x2C);assert mode
 put(m,CAMERA,(mode&-mode).bit_length()-1,2)
def reset_effect(m,c):
 put(m,CAMERA+0x7C8,0x2468ACE0);effect(m,c,RESET)
def save_effect(m,c,a,nested=False):
 assert a==(CAMERA,0x100,4,0x12345678,1)
 if read(m,CAMERA+0x20E,2):return 0,[]
 for src,dst,n in((0,4,2),(0x2C,0x34,4),(0x84,0x8C,4),(0xDC,0xE4,4),(0x134,0x13C,4),(0x1B4,0x1B8,2),(0x1E0,0x1E4,2)):put(m,CAMERA+dst,read(m,CAMERA+src,n),n)
 put(m,CAMERA+0x2C,a[1]);put(m,CAMERA+0xDC,a[2]);put(m,CAMERA+0x134,a[3]);put(m,CAMERA+0x20E,1,2);index_effect(m)
 return 1,[(INDEX,(CAMERA,))]if nested else[]
def restore_effect(m,c,nested=False):
 if not read(m,CAMERA+0x20E,2):return 0,[]
 for src,dst,n in((4,0,2),(0x34,0x2C,4),(0xE4,0xDC,4),(0x8C,0x84,4),(0x13C,0x134,4),(0x1B8,0x1B4,2),(0x1E4,0x1E0,2)):put(m,CAMERA+dst,read(m,CAMERA+src,n),n)
 reset_effect(m,c);put(m,CAMERA+0x20E,0,2)
 return 1,[(RESET,(CAMERA,))]if nested else[]
def reference(initial,c,connected=False):
 m=dict(initial);calls=[];p=read(m,CAMERA+0x3D0);old=read(m,CAMERA+0x5F0)
 stunned=m[p+0x104]!=0 and m[CAMERA+0x23E]not in(9,0x38,0x39,0x3B,0x37,0x15,0x26,0x3A)
 blocked=bool(read(m,CAMERA+0x2C)&0x80 or read(m,CAMERA+0x84)&0x1000000)
 if not blocked and floating(read(m,p+0x28))!=0.:
  if not m[p+0xAD] and not read(m,read(m,CAMERA+0x3D4)+0x9C) and not old&0x300 and m[CAMERA+0x23E]!=3:blocked=True
 if not blocked and m[p+0x65] and not old&0x300:blocked=True
 blocked=blocked or stunned
 if not blocked:
  calls.append((QUERY,(CAMERA,)));effect(m,c,QUERY);blocked=bool(c.query)
  if not blocked:
   p=read(m,CAMERA+0x3D0);s=read(m,CAMERA+0x3D4)
   blocked=not m[p+0x1CA] or (m[s+0x4E]&15==1 and floating(read(m,p+0x3C))>15.) or bool(m[s+0x1AC])
 if read(m,read(m,CAMERA+0x36C),2)&16 and not blocked:
  if read(m,CAMERA+0x36A,2)&16:
   a=(CAMERA,0x100,4,read(m,CAMERA+0x134),1);calls.append((SAVE,a));result,sub=save_effect(m,c,a,connected);calls+=sub
   if result:calls.append((ACTIVATE,(CAMERA,)));effect(m,c,ACTIVATE)
  return public(m),calls
 if read(m,CAMERA+0x2C)==0x100 and not read(m,CAMERA+0x73C,2):
  calls.append((RESTORE,(CAMERA,1)));_,sub=restore_effect(m,c,connected);calls+=sub
  m[read(m,CAMERA+0x3D4)+0x198]=0;m[read(m,CAMERA+0x3D4)+0x197]=0
  put(m,CAMERA+0x5F8,1,2);put(m,CAMERA+0x5FC,2,2)
  put(m,CAMERA+0x36A,read(m,CAMERA+0x36A,2)&~16,2)
  ip=read(m,CAMERA+0x36C);put(m,ip,read(m,ip,2)&~16,2)
 if read(m,CAMERA+0x2C)==0x100 or read(m,CAMERA+0x73C,2):
  put(m,CAMERA+0x36A,read(m,CAMERA+0x36A,2)&~16,2)
  ip=read(m,CAMERA+0x36C);put(m,ip,read(m,ip,2)&~16,2)
 m[read(m,CAMERA+0x3D4)+0x198]=read(m,CAMERA+0x73C,2)&255
 if read(m,CAMERA+0x73C,2):
  for p,v in((0x74C,0x79C),(0x754,0x7A0)):
   a=(CAMERA+p,0,CAMERA+v,bits(4.),bits(9.),read(m,CAMERA+0x7B4));calls.append((SPRING,a));spring(m,*a);effect(m,c,SPRING)
 if read(m,CAMERA+0x2C)!=0x100 and read(m,CAMERA+0x73C,2):put(m,CAMERA+0x73C,0,2)
 return public(m),calls
@lru_cache(maxsize=1)
def helper_code():
 r={};rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 for entry,n in((SPRING,54),(SAVE,38),(RESTORE,34)):
  p=entry-0x15000000+0x2D4B0;raw=rom[p:p+4*n];at=elf_slot_offset(elf,entry,4*n);assert elf[at:at+4*n]==raw
  r.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,raw)))
 return r
class Machine(FactoryOracle):
 def __init__(self,words,c,m,connected=False):
  self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(CAMERA,),connected=helper_code()if connected else None)
 def record_call(self,t):
  n={QUERY:1,SAVE:5,RESTORE:2,ACTIVATE:1,SPRING:6,INDEX:1,RESET:1}[t];a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  a=self.calls[-1][1];answer=0xA5000002
  if t==QUERY:effect(self.memory,self.c,t);answer=self.c.query
  elif t==SAVE:answer,_=save_effect(self.memory,self.c,a)
  elif t==RESTORE:answer,_=restore_effect(self.memory,self.c)
  elif t==ACTIVATE:effect(self.memory,self.c,t)
  elif t==SPRING:spring(self.memory,*a);effect(self.memory,self.c,t)
  elif t==INDEX:index_effect(self.memory)
  elif t==RESET:reset_effect(self.memory,self.c)
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=answer&0xFFFFFFFF
def programs():return[bound_blob(*payload(p,'func_1512317C'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/game_14FF90.c.o')]
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.current_pc,m.delay_of)
def corpus():
 for name in('stunned','state','actor65','health','kind','secondary_ac'):
  for v in range(256):yield replace(Case(),**{name:v})
 for v in range(256):
  yield Case(stunned=1,state=v)
  yield Case(value=bits(1.),state=v)
 for mode,flags,old,value,water,sec,actor65 in itertools.product((0,0x80,0x100),(0,0x1000000),(0,0x100,0x200,0x300),(0,bits(1.)),(0,1),(0,1),(0,1)):
  yield Case(mode=mode,flags=flags,old=old,value=value,water=water,secondary_flags=sec,actor65=actor65)
 for mode,inp,edge,slot,substate,mutation,alias in itertools.product((0,0x100),(0,16),(0,16),(0,1),(0,3,0x8000),(0,1,2,4),range(4)):
  yield Case(mode=mode,input=inp,edge=edge,slot=slot,substate=substate,mutation=mutation,alias=alias,phase=8*(alias&1),pattern=alias)
 for value,speed in itertools.product((0,0x80000000,bits(1.),0x7FC12345,0x7F800000),(bits(14.99),bits(15.),bits(15.01),0x7FC12345,0x7F800000)):
  yield Case(value=value,water=1,kind=1,speed=speed)
 for pattern,query,mutation in itertools.product(range(4),(0,1,0x80000000),(0,1,2,4,7)):
  yield Case(pattern=pattern,query=query,mutation=mutation,mode=0x100,input=0,slot=1)
 for old,stunned,substate in itertools.product((0,0x300),(0,1),(0,3)):
  yield Case(alias=4,old=old,stunned=stunned,substate=substate,input=0)
def compare(streams,c,connected=False):
 initial=fixture(c);expected=reference(initial,c,connected);machines=[]
 for w in streams:
  m=Machine(w,c,dict(initial),connected).run()
  assert(public(m.memory),m.calls)==expected,('model',c,m.calls,expected[1],[(hex(a),b,expected[0].get(a))for a,b in public(m.memory).items()if expected[0].get(a)!=b][:12])
  machines.append(m)
 assert all(state(m)==state(machines[0])for m in machines[1:]),c
 return machines[0]
def run():
 streams=programs();assert streams[0]==streams[1]==streams[2];coverage=set();count=0
 for c in corpus():
  m=compare(streams,c);coverage.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+SIZE);count+=1
 reachable=static_reachable(streams[0]);assert coverage==reachable,sorted(reachable-coverage)
 connected_count=0;seen=set();code=helper_code()
 for mode,inp,slot,substate,pattern,dt in itertools.product((0,0x100),(0,16),(0,1),(0,3),range(4),(0,bits(.125),bits(1.))):
  c=Case(mode=mode,input=inp,slot=slot,substate=substate,pattern=pattern,dt=dt);m=compare(streams,c,True);seen.update(m.visits&code.keys());connected_count+=1
 reachable_helpers=set()
 for entry,n in((SPRING,54),(SAVE,38),(RESTORE,34)):
  w=[code[entry+4*i]for i in range(n)];reachable_helpers|={entry+4*i for i in static_reachable(w)}
 assert seen==reachable_helpers,sorted(hex(p)for p in reachable_helpers-seen)
 faults=0
 for c in(Case(),Case(mode=0x100,input=0,slot=1,mutation=2),Case(substate=3,input=0,mutation=4)):
  full=compare(streams,c)
  for cut in range(full.all_accesses):
   states=[]
   for w in streams:
    m=Machine(w,c,fixture(c));m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert states[0]==states[1]==states[2];faults+=1
 controls=[]
 for label,old,new,c in(('old-flag-mask',0x30460100,0x30460400,Case(old=0x100,actor65=1)),
  ('stunned-exclusion',0x38430009,0x38430008,Case(stunned=1,state=9)),
  ('input-gate',0x312A0010,0x312A0020,Case())):
  changed=list(streams[0]);assert changed.count(old)==1,(label,changed.count(old));changed[changed.index(old)]=new
  initial=fixture(c);expected=reference(initial,c);m=Machine(changed,c,dict(initial)).run()
  assert(public(m.memory),m.calls)!=expected,label;controls.append(label)
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'static_unreachable_words':sorted(set(range(227))-reachable),
  'connected_helper_cases_per_stream':connected_count,'connected_helper_words':len(code),'connected_helper_covered_words':len(seen),'access_fault_prefixes':faults,
  'full_memory_private_bytes_registers_calls_and_ordered_accesses_equal':True,'effective_controls':controls,
  'limits':'Modeled query, activation and downstream reset/index contracts; actual original/current save, restore and spring helpers connected separately. No full 318-word activation, query, reset, FCSR/hardware/gameplay claim. Overlapping camera/actor alias is guest-only.',
  'source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
