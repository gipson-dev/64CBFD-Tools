"""Independent indexed-list model, live count/entry mutation and bounded providers."""
from pathlib import Path
from dataclasses import dataclass,replace
from types import FunctionType
import itertools,json,struct,sys
from tools.experiments import game_indexed_column_event_walker_15169260_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_node_range_walker_15169070_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_paired_ground_constructor_match import payload as object_payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x15169260;NAME='func_15169260';SYMS=g.SYMS;LIST=0x60000;CHILD_LIST=0x62000;NODES=tuple(0x30000+0x400*i for i in range(10));SIZE=0x1D8
u32=g.u32;s32=g.s32;put=g.put;read=g.read;STACK=g.STACK
@dataclass(frozen=True)
class Case:
 columns:tuple=(2,3,2,3,2,3,2,3)
 count:int=2
 opcode:int=1
 depth:int=-1
 pattern:int=2
 mode:int=0
 empty:bool=False
 payload_kind:int=0
 tag:int=0x39
 real_helpers:bool=False
 phase:int=0
 list_home:bool=False
 list_override:int|None=None
 payload_override:int|None=None
def helper_code():return FunctionType(g.helper_code.__code__,dict(g.helper_code.__globals__,root=root))(SYMS)
def indices(c):return c.list_override if c.list_override is not None else STACK+c.phase+4 if c.list_home else LIST
def payload(c,s=SYMS):
 return c.payload_override if c.payload_override is not None else(g.PAYLOAD,s['D_800DD190'],LIST,NODES[0]+8,STACK+c.phase+4)[c.payload_kind]
def args(c,s=SYMS):return(indices(c),u32(c.count),payload(c,s),u32(c.opcode))
def slot(m,s=SYMS):return u32(s['D_800DD198']+4*g.s8(m[s['D_800DD190']]))
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-4096,1024)}
 for i in range(-128,128):put(m,u32(s['D_800DD198']+4*i),0)
 for row in range(2):
  for col in range(104):
   n=(0 if col%2==0 else 3)if row==0 else(5 if col%2==0 else 7)
   put(m,s['D_800DCE50']+row*416+col*4,0 if c.empty else NODES[n])
 for col in range(104):
  at=s['D_8008B4A8']+col*52;m.update({at+i:(col*31+i*13+7)&255 for i in range(52)})
  put(m,at+28,g.CB0 if c.pattern==1 or c.pattern==2 and col%2==0 else 0)
 following={0:1,1:2,3:4,5:6,8:9}
 for i,node in enumerate(NODES):
  m.update({node+j:(i*19+j*13+5)&255 for j in range(-8,SIZE+8)});m[node]=2 if i in(0,1,2,5,6,8,9)else 3;m[node+12]=c.tag
  put(m,node+8,NODES[following[i]]if i in following else 0)
 for i in range(8):put(m,LIST+4*i,c.columns[i%len(c.columns)])
 put(m,CHILD_LIST,3)
 m.update({g.PAYLOAD+i:(i*17+3)&255 for i in range(32)});m[g.PAYLOAD]=0x39;m[s['D_800DD190']]=c.depth&255
 if c.list_home:
  for i in range(3):put(m,STACK+c.phase+4+4*i,c.columns[i])
  # A count-home mutation also retargets the aliased first list entry to3.
  # Keep that real callback reload callable and distinguish it from column2.
  put(m,s['D_8008B4A8']+3*52+28,g.CB1)
 return m
def snapshot(m,c,s):
 h=STACK+c.phase;return(m[s['D_800DD190']],read(m,slot(m,s)),read(m,h+4),read(m,h+12),read(m,h-8),read(m,h-24))
def effects(m,c,node,state,s,recurse):
 if state['fired']:return
 state['fired']=True;cursor=slot(m,s);following=read(m,cursor)
 if c.mode&1:put(m,node+8,NODES[8])
 if c.mode&2:put(m,cursor,read(m,following+8)if following else 0)
 if c.mode&4:
  following=read(m,cursor);m[s['D_800DD190']]=(m[s['D_800DD190']]+1)&255;put(m,slot(m,s),following)
 if c.mode&8:
  col=read(m,indices(c));put(m,u32(s['D_8008B4A8']+52*col+28),g.CB1)
 if c.mode&16:
  put(m,indices(c),3);put(m,s['D_8008B4A8']+3*52+28,g.CB1)
 if c.mode&32:put(m,STACK+c.phase+4,c.count+1)
 if c.mode&64:recurse()
 if c.mode&128:
  # A future entry changes between columns; the captured cursor still advances.
  put(m,indices(c)+4,102)
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];observations=[];state=dict(fired=False)
 def walk(c):
  h=STACK+c.phase;put(m,h+4,c.count);put(m,h+12,c.opcode);put(m,h-8,0);cursor=indices(c)
  if s32(read(m,h+4))<=0:return
  def record(t,a):calls.append((t,tuple(a)));observations.append(snapshot(m,c,s))
  def recur():
   child=replace(c,count=1,list_home=False,list_override=CHILD_LIST,payload_override=payload(c,s),phase=c.phase-152)
   record(ENTRY,args(child,s));walk(child)
  outer=0
  while True:
   outer+=1;assert outer<=12,'Unbounded private count mutation';put(m,h-24,s['D_800DCE50'])
   for row in range(2):
    col=read(m,cursor);desc=u32(s['D_8008B4A8']+52*col);callback=bool(read(m,desc+28));node=read(m,u32(read(m,h-24)+4*col))
    m[s['D_800DD190']]=(m[s['D_800DD190']]+1)&255;continuation=slot(m,s);steps=0
    while node:
     steps+=1;assert steps<=32,'Unbounded private list';put(m,continuation,read(m,node+8));a=(node,payload(c,s),c.opcode&255);record(s['func_1516968C'],a)
     if not c.real_helpers:effects(m,c,node,state,s,recur)
     elif c.opcode&255 in(15,16)and m[payload(c,s)]==m[node+12]:record(g.CLEAN,(node,));effects(m,c,node,state,s,recur)
     if callback:
      fresh=read(m,cursor);t=read(m,u32(s['D_8008B4A8']+fresh*52+28));assert t in(g.CB0,g.CB1);record(t,a);effects(m,c,node,state,s,recur)
     continuation=slot(m,s);node=read(m,continuation)
    m[s['D_800DD190']]=(m[s['D_800DD190']]-1)&255;put(m,h-24,u32(read(m,h-24)+416))
   old=read(m,h-8);count=read(m,h+4);cursor=u32(cursor+4);next_index=u32(old+1);put(m,h-8,next_index)
   if next_index==count:return
 walk(c);return m,calls,observations
class Oracle(g.Oracle):
 def __init__(self,ws,memory,c,s=SYMS,connected=None,state=None):
  FactoryOracle.__init__(self,ws,memory,replace(c,phase=c.phase&8),entry=ENTRY,s=s,connected=connected,arguments=args(c,s))
  self.case=c;self.target_home=STACK+c.phase;self.r[29]=self.target_home;self.ws=ws;self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observations=[];self.state=dict(fired=False)if state is None else state;self.bound_helpers={}if connected is None else connected
 def record_call(self,t):
  counts={ENTRY:4,self.syms['func_1516968C']:3,g.CB0:3,g.CB1:3,g.CLEAN:1};assert t in counts,hex(t);n=counts[t]
  a=tuple(self.arguments(n));self.calls.append((t,a));self.observations.append(snapshot(self.memory,self.case,self.syms));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.case;s=self.syms;a=self.calls[-1][1]
  def recur():
   child=replace(c,count=1,list_home=False,list_override=CHILD_LIST,payload_override=payload(c,s),phase=c.phase-152);self.calls.append((ENTRY,args(child,s)));self.observations.append(snapshot(self.memory,c,s))
   m=Oracle(self.ws,self.memory,child,s,connected=self.bound_helpers,state=self.state);m.run();self.memory.clear();self.memory.update(m.memory);self.calls.extend(m.calls);self.observations.extend(m.observations)
  assert t in(s['func_1516968C'],g.CB0,g.CB1,g.CLEAN);effects(self.memory,c,a[0],self.state,s,recur)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,0xA5000002
def words(path,s=SYMS):return bound_blob(*object_payload(path,NAME),s)
def check(m,c,s=SYMS):
 want,calls,observations=reference(m.initial,c,s)
 assert(g.public(m.memory),m.calls,m.observations)==(g.public(want),calls,observations),('Indexed walker public state',c)
 h=STACK+c.phase;assert all(m.memory[a]==want[a]for a in m.initial if h<=a<h+64),('Incoming homes',c)
 assert read(m.memory,h-8)==read(want,h-8)and read(m.memory,h-24)==read(want,h-24),('Named frame slots',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
def cases():
 result=[replace(Case(),pattern=p,mode=m,phase=(m&1)*8)for p,m in itertools.product(range(3),range(256))]
 result +=[replace(Case(),count=n,columns=cols,empty=e)for n,cols,e in itertools.product((0,-1,0x80000000,0xFFFFFFFF,1,2,3,4),((0,103,2,3),(2,2,3,3)),(False,True))]
 result +=[replace(Case(),opcode=op,real_helpers=True,tag=t)for op,t in itertools.product(range(256),(0,0x39))]
 result +=[replace(Case(),depth=d,empty=e)for d,e in itertools.product(range(256),(False,True))]
 result +=[replace(Case(),payload_kind=k,mode=m,opcode=15,real_helpers=r)for k,m,r in itertools.product((1,2,3,4),(0,1,2,4,8,16,32,64,128),(False,True))]
 result +=[replace(Case(),list_home=True,opcode=2,mode=m)for m in(0,1,2,4,8,16,32,128)]
 result +=[replace(Case(),opcode=op)for op in(0x100,0x1000F,0x80000010,0xFFFFFFFF)]
 return result
def main():
 paths={'raw':out/'sdk-frame-last/candidate.o','normalized':out/'qualified-owner/game_1944C0.c.o','retail':out/'original-target.o'};helpers=helper_code();reports={}
 for label,path in paths.items():
  ws=words(path);seen=set()
  for c in cases():
   m=Oracle(ws,fixture(c),c,connected=helpers if c.real_helpers else None)
   try:m.run();check(m,c)
   except(AssertionError,KeyError)as e:raise AssertionError((label,c,str(e)))from e
   seen.update(m.visits)
  reports[label]=dict(cases=len(cases()),unexecuted=[i for i in range(len(ws))if ENTRY+4*i not in seen])
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=dict(SYMS,func_1516968C=0x15310000,D_8008B4A8=0x80300000+low,D_800DCE50=0x80400000+low,D_800DD190=0x80400340+low,D_800DD198=0x80400348+low)
  for path in paths.values():
   for mode in(0,16,32,64):
    c=replace(Case(),mode=mode);m=Oracle(words(path,s),fixture(c,s),c,s);m.run();check(m,c,s);rebases+=1
 r=dict(streams=reports,guest_rebase_runs=rebases,public_calls_observations_named_frame_slots_and_saved_ABI_equal=True,
  live_input_entry_and_count_mutations=True,recursive_mutation_is_provider_extension=True,private_register_and_PC_identity_not_claimed=True,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
