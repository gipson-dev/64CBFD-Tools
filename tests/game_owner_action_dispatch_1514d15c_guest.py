"""Literal dispatcher and independent ordered service reference; no FP normalization."""
from tools.experiments import game_owner_action_dispatch_1514d15c_match as target_packet
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,sys
sys.path.insert(0,str(target_packet.ROOT))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
r=target_packet.ROOT;o=target_packet.OUT;ENTRY=0x1514D15C;BASE=0x30000;STRIDE=0x32C;EFFECT=0x60000;MARK=0x90000;FIND=0x15155FD4;FREE=0x1516972C;RESET=0x15155780;CLASSIFY=0x1514CA80;TABLE=0x8008AA70;ROWS=0x8008AB90;THIRD=0x800A5ED8;SECOND=0x800A5EC0;ENABLE=0x800BE616;CB=0x20000000
u32=lambda n:n&0xFFFFFFFF;signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 index:int=0
 gate:int=0
 effects:int=1
 enable:int=0
 flags:int=7
 outputs:tuple=(1,1,1)
 selectors:tuple=(1,2,3)
 absent:int=0
 mode:int=0
 private:int=0
 phase:int=0
 seed:int=0

def owner(c):return u32(BASE+STRIDE*c.index)
def symbols():return dict(D_800CC2D0=BASE,D_800BE616=ENABLE,D_8008AACC=TABLE+23*4,D_8008AA70=TABLE,D_8008AB90=ROWS,D_800A5ED8=THIRD,D_800A5EC0=SECOND,func_15155FD4=FIND,func_1516972C=FREE,func_15155780=RESET,func_1514CA80=CLASSIFY)
def public(m,c):return {a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+512}
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*11+0xA5)&255 for i in range(-2048,512)}
 for base,n in((owner(c)-16,STRIDE+32),(EFFECT,128),(MARK,32),(THIRD,64),(SECOND,64),(TABLE,58*4),(ROWS,32*4)):
  for i in range(n):m[u32(base+i)]=(i*29+c.seed*13+0x5A)&255
 if c.private==2:
  for i in range(-16,STRIDE+16):m[0x50000+i]=(i*19+0xA5)&255
  put(m,0x50000+0x2F4,0)
 put(m,owner(c)+0x2F4,c.gate);m[ENABLE]=c.enable
 for i in range(58):put(m,TABLE+4*i,0 if(c.absent and i not in({23}|{v for v in c.selectors[:2]if v}|({57}if c.mode&2 else set())))else CB+i*32)
 for i in range(32):
  row=0xA0000+64*i;put(m,ROWS+i*4,row)
  for j in range(64):m[row+j]=c.selectors[2]
 for i in range(64):m[SECOND+i]=c.selectors[1];m[THIRD+i]=c.selectors[0]
 for i in range(8):put(m,MARK+4*i,0)
 return m

def effect(m,c,t,args,ordinal,callbacks,home,outptrs):
 p=args[0]if t not in(FIND,RESET,CLASSIFY)and t!=FREE else owner(c)
 if t==FIND:
  put(m,MARK,read(m,MARK)+1)
  if c.mode&1:m[ENABLE]=1
  return EFFECT+16*(ordinal-1)if ordinal<=c.effects else 0
 if t==FREE:put(m,args[0],0);put(m,MARK+4,read(m,MARK+4)+1);return 0xAABBCCDD
 if t==RESET:put(m,MARK+8,read(m,MARK+8)+1);return 0xBADC0DE
 if t==CLASSIFY:
  for p,value in zip(args[1:],c.outputs):put(m,p,value)
  return c.flags
 assert t in{CB+i*32 for i in range(58)},hex(t)
 put(m,MARK+12,read(m,MARK+12)+1);m[args[0]+0x66]^=(callbacks*11)&255
 if c.mode&2 and callbacks==1:put(m,owner(c)+0x2F4,0x87654320);m[THIRD+1]=57
 if c.mode&4 and callbacks==2:
  # Actual output pointers escape to the classifier, so a stronger provider may retain them.
  assert outptrs;put(m,outptrs[0],2);put(m,outptrs[1],2);m[SECOND+2]=23
 if c.mode&8 and callbacks==3:
  assert outptrs;put(m,outptrs[0],3);put(m,ROWS+4*read(m,outptrs[1]),0xA0000)
 if c.private==1 and callbacks==2:m[home-72+0x3B]=0
 if c.private==2 and callbacks==1:put(m,home,0x50000)
 return 0xCCCC0000+callbacks

def reference(initial,c,classifier=None):
 m=dict(initial);home=STACK+c.phase;frame=home-72;outptrs=(frame+0x44,frame+0x40,frame+0x3C);calls=[];counts={};callbacks=0
 for p in outptrs:put(m,p,0xFFFFFFFF)
 if read(m,owner(c)+0x2F4):return public(m,c),calls,0
 index=signed(u32(owner(c)-BASE));index=(abs(index)//STRIDE)*(-1 if index<0 else 1)
 def call(t,args):
  nonlocal callbacks
  counts[t]=counts.get(t,0)+1;calls.append((t,tuple(map(u32,args))))
  if t not in(FIND,FREE,RESET,CLASSIFY):callbacks+=1
  if t==CLASSIFY and classifier is not None:return classifier(m,args,c)
  return effect(m,c,t,args,counts[t],callbacks,home,outptrs)
 while True:
  item=call(FIND,(index,))
  if item:call(FREE,(item,))
  else:break
 if index==0 and not m[ENABLE]:call(RESET,(index,255))
 put(m,home,owner(c));call(read(m,TABLE+4*23),(read(m,home),))
 flags=call(CLASSIFY,(read(m,home),*outptrs))
 if not flags:return public(m,c),calls,0
 flags&=255
 if flags&4:
  selector=m[u32(THIRD+read(m,outptrs[2]))]
  if selector:
   m[frame+0x3B]=flags;call(read(m,TABLE+4*selector),(read(m,home),));flags=m[frame+0x3B]
 if flags&2:
  selector=m[u32(SECOND+read(m,outptrs[1]))]
  if selector:call(read(m,TABLE+4*selector),(read(m,home),))
 if flags&2 and flags&1:
  row=read(m,u32(ROWS+4*read(m,outptrs[1])));selector=m[u32(row+read(m,outptrs[0]))];fn=read(m,u32(TABLE+4*selector))
  if fn:call(fn,(read(m,home),))
 return public(m,c),calls,1

class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;self.counts={};self.callback_ordinal=0;self.outptrs=None
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(owner(c),)if arguments is None else arguments,s=symbols(),connected=connected)
  self.initial=dict(self.memory);self.before_f=self.f[:];self.fcsr=c.seed&3
 def execute(self,w):
  op=w>>26;fn=w&63
  if op==0 and fn in(0x18,0x19,0x1A,0x1B):
   a,b=self.r[w>>21&31],self.r[w>>16&31]
   if fn in(0x18,0x19):value=(signed(a)*signed(b))if fn==0x18 else u32(a)*u32(b);self.lo,self.hi=u32(value),u32(value>>32)
   else:
    a,b=(signed(a),signed(b))if fn==0x1A else(u32(a),u32(b));assert b;quot=(abs(a)//abs(b))*(-1 if(a<0)!=(b<0)else 1);self.lo,self.hi=u32(quot),u32(a-quot*b)
  else:super().execute(w)
 def record_call(self,t):
  count=1 if t in(FIND,FREE)else 2 if t==RESET else 4 if t==CLASSIFY else 1 if t in{CB+i*32 for i in range(58)}else None;assert count is not None,hex(t)
  args=tuple(map(u32,self.arguments(count)));self.calls.append((t,args));self.events.append(('CALL',t,args));self.counts[t]=self.counts.get(t,0)+1
  if t==CLASSIFY:self.outptrs=args[1:]
  if t not in(FIND,FREE,RESET,CLASSIFY):self.callback_ordinal+=1
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.calls[-1][1],self.counts[t],self.callback_ordinal,STACK+self.c.phase,self.outptrs)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.trace,m.current_pc,m.delay_of,m.condition

def check(words,c):
 m=Machine(words,c).run();expected=reference(m.initial,c);actual=public(m.memory,c),m.calls,m.r[2];assert actual==expected,dict(case=str(c),parts=[a==b for a,b in zip(actual,expected)],actual_calls=m.calls,expected_calls=expected[1]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m

def streams():
 paths=('original-target.o','selected-owner.o','normalized-target.o','qualified-owner/selected-generic.o','qualified-owner/selected-generated.o');ws=[bound_blob(*payload(o/p,'func_1514D15C'),symbols())for p in paths];assert all(w==ws[0]for w in ws)and len(ws[0])==109;return ws

def cases():
 rows=[Case(index=index,gate=gate,effects=effects,enable=enabled,flags=flags,mode=mode,phase=8*(flags&1),seed=flags)for index,gate,effects,enabled,flags,mode in itertools.product((-2,0,3),(0,1),(0,2),(0,1),(0,1,2,3,4,5,6,7,255),(0,15))]
 rows.extend(Case(flags=f,selectors=selectors,absent=absent,seed=f)for f,selectors,absent in itertools.product(range(256),((0,0,0),(23,23,23),(57,1,2)),(0,1)))
 rows.extend(Case(private=private,flags=7,mode=mode)for private,mode in itertools.product((1,2),(0,15)));return rows

def main():
 ws=streams();rows=cases();seen=set()
 for c in rows:
  models=[check(w,c)for w in ws];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(p for p in models[0].visits if ENTRY<=p<ENTRY+436)
 cuts=0
 for c in(Case(gate=1),Case(),Case(flags=0,effects=0),Case(flags=7,mode=15,private=1)):
  full=Machine(ws[0],c).run()
  for cut in range(full.all_accesses):
   ms=[]
   for w in ws:
    m=Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:ms.append(m)
   assert all(state(m)==state(ms[0])for m in ms[1:]);cuts+=1
 controls=[]
 for name,off,value,c in(('gate-field',0x2C,0x8CB902F0,Case(gate=1)),('index-stride',0x48,0x24010330,Case(index=3)),('reset-channel',0x98,0x240500FE,Case()),('wrong-first-output',0xB4,0x27A50040,Case(flags=4)),('return',0x19C,0x24020000,Case()),('private-flag-home',0x104,0xA3A30033,Case(private=1))):
  bad=list(ws[0]);assert bad[off//4]!=value;bad[off//4]=value;m=Machine(bad,c).run();assert(public(m.memory,c),m.calls,m.r[2])!=reference(m.initial,c)or state(m)!=state(Machine(ws[0],c).run()),name;controls.append(dict(name=name,comparison_mismatch=True))
 assert len(seen)==109,(len(seen),[hex(p)for p in set(range(ENTRY,ENTRY+436,4))-seen])
 q=dict(cases_per_stream=len(rows),streams=5,executed_words=len(seen),fault_prefix_quintuples=cuts,all_literal_full_private_states_equal=True,independent_reference_public_memory_ordered_calls_and_return_equal=True,all256_classification_bytes=True,negative_zero_positive_owner_indices=True,callback_table23_and_pre_callback_alias=True,escaped_output_mutations_and_late_callback_table_reads=True,private_flag_home_and_incoming_home_are_guest_only=True,effective_controls=controls,other_services_opaque=True,source_installed=target_packet.installed(),matching_credit=0)
 (o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
