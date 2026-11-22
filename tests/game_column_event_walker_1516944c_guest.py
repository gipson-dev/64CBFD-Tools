"""Column-walker public/saved ABI model with live continuation-slot mutation."""
from pathlib import Path
from dataclasses import replace
import itertools,json,struct,sys
from tools.experiments import game_column_event_walker_1516944c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_node_range_walker_15169070_oracle as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from types import FunctionType
def helper_code(s=None):
 f=FunctionType(g.helper_code.__code__,dict(g.helper_code.__globals__,root=root))
 return f(g.SYMS if s is None else s)
ENTRY=0x1516944C;NAME='func_1516944C';Case=g.Case;SYMS=g.SYMS
def column(c):return min(g.s32(c.first),103)
def arguments(c,s):return(g.u32(c.first),g.payload(c,s),g.u32(c.opcode))
def descriptor(c,s):return g.u32(s['D_8008B4A8']+52*column(c))
def fixture(c,s=SYMS):
 m=g.fixture(c,s);d=descriptor(c,s)
 for j in range(52):m.setdefault(g.u32(d+j),(j*19+7)&255)
 g.put(m,g.u32(d+28),g.CB0 if c.pattern==1 or c.pattern==2 and column(c)%2==0 else 0)
 for row,n in ((0,0),(1,5)):g.put(m,g.u32(s['D_800DCE50']+row*416+4*column(c)),0 if c.empty else g.NODES[n])
 m[s['D_800DD190']]=c.depth&255
 return m
def effects(m,c,node,state,s,recurse):
 fresh=not state['fired'];g.effects(m,c,node,state,s,recurse)
 if fresh and c.mode&8:g.put(m,g.u32(descriptor(c,s)+28),g.CB1)
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];observations=[];state=dict(fired=False)
 def walk(c):
  g.put(m,g.STACK+c.phase+8,g.u32(c.opcode));d=descriptor(c,s)
  def record(t,a):calls.append((t,tuple(a)));observations.append(g.snapshot(m,c,s))
  def recur():
   child=replace(c,first=3,phase=c.phase-128);record(ENTRY,arguments(child,s));walk(child)
  for row in range(2):
   callback=bool(g.read(m,g.u32(d+28)));node=g.read(m,g.u32(s['D_800DCE50']+416*row+4*column(c)))
   m[s['D_800DD190']]=(m[s['D_800DD190']]+1)&255;cursor=g.slot(m,s);steps=0
   while node:
    steps+=1;assert steps<=32,'Unbounded private fixture';g.put(m,cursor,g.read(m,node+8));a=(node,g.payload(c,s),c.opcode&255);record(s['func_1516968C'],a)
    if not c.real_helpers:effects(m,c,node,state,s,recur)
    elif c.opcode&255 in(15,16)and m[g.payload(c,s)]==m[node+12]:record(g.CLEAN,(node,));effects(m,c,node,state,s,recur)
    if callback:
     t=g.read(m,g.u32(d+28));assert t in(g.CB0,g.CB1);record(t,a);effects(m,c,node,state,s,recur)
    cursor=g.slot(m,s);node=g.read(m,cursor)
   m[s['D_800DD190']]=(m[s['D_800DD190']]-1)&255
 walk(c);return m,calls,observations
class Oracle(g.Oracle):
 def __init__(self,ws,memory,c,s=SYMS,connected=None,state=None):
  FactoryOracle.__init__(self,ws,memory,replace(c,phase=c.phase&8),entry=ENTRY,s=s,connected=connected,arguments=arguments(c,s))
  self.case=c;self.target_home=g.STACK+c.phase;self.r[29]=self.target_home;self.ws=ws;self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observations=[];self.state=dict(fired=False)if state is None else state;self.bound_helpers={}if connected is None else connected
 def record_call(self,t):
  n=3 if t in(self.syms['func_1516968C'],g.CB0,g.CB1,ENTRY)else 1 if t==g.CLEAN else None;assert n is not None,hex(t)
  a=tuple(self.arguments(n));self.calls.append((t,a));self.observations.append(g.snapshot(self.memory,self.case,self.syms));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.case;s=self.syms;a=self.calls[-1][1]
  def recur():
   child=replace(c,first=3,phase=c.phase-128);self.calls.append((ENTRY,arguments(child,s)));self.observations.append(g.snapshot(self.memory,c,s))
   m=Oracle(self.ws,self.memory,child,s,connected=self.bound_helpers,state=self.state);m.run();self.memory.clear();self.memory.update(m.memory);self.calls.extend(m.calls);self.observations.extend(m.observations)
  assert t in(s['func_1516968C'],g.CB0,g.CB1,g.CLEAN);effects(self.memory,c,a[0],self.state,s,recur)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,0xA5000002
def words(path,s=SYMS):return bound_blob(*payload(path,NAME),s)
def check(m,c,s=SYMS):
 want,calls,observations=reference(m.initial,c,s)
 assert(g.public(m.memory),m.calls,m.observations)==(g.public(want),calls,observations),('Column walker public state',c)
 assert all(m.memory[p]==want[p]for p in m.initial if g.STACK+c.phase<=p<g.STACK+c.phase+64),('Incoming homes',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
def cases():
 result=[replace(Case(),pattern=p,mode=m,phase=(m&1)*8)for p,m in itertools.product(range(3),range(256))]
 result +=[replace(Case(),first=col,pattern=p,empty=e)for col,p,e in itertools.product((0,1,2,3,102,103,104,105,0x7FFFFFFF,-1,-2,-104,0x80000000,0xFFFFFFFF),range(3),(False,True))]
 result +=[replace(Case(),opcode=op,real_helpers=True,tag=t)for op,t in itertools.product(range(256),(0,0x39))]
 result +=[replace(Case(),depth=d,empty=e)for d,e in itertools.product(range(256),(False,True))]
 result +=[replace(Case(),payload_kind=k,mode=m,real_helpers=real,opcode=15)for k,m,real in itertools.product((1,2,3),(0,1,2,4,8,16,32,64,128),(False,True))]
 result +=[replace(Case(),opcode=op)for op in(0x100,0x1000F,0x80000010,0xFFFFFFFF)]
 return result
def main():
 paths={'raw':out/'assign-1/candidate.o','normalized':out/'qualified-owner/game_1944C0.c.o','retail':out/'original-target.o'};reports={};helpers=helper_code()
 for label,p in paths.items():
  ws=words(p);seen=set()
  for c in cases():
   m=Oracle(ws,fixture(c),c,connected=helpers if c.real_helpers else None)
   try:m.run();check(m,c)
   except(AssertionError,KeyError)as e:raise AssertionError((label,c,str(e)))from e
   seen.update(m.visits)
  reports[label]=dict(cases=len(cases()),unexecuted=[i for i in range(len(ws))if ENTRY+4*i not in seen])
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=dict(SYMS,func_1516968C=0x15310000,D_8008B4A8=0x80300000+low,D_800DCE50=0x80400000+low,D_800DD190=0x80400340+low,D_800DD198=0x80400348+low)
  for p in paths.values():
   for mode in(0,15,64):
    c=replace(Case(),mode=mode);m=Oracle(words(p,s),fixture(c,s),c,s);m.run();check(m,c,s);rebases+=1
 r=dict(streams=reports,guest_rebase_runs=rebases,public_calls_observations_and_saved_ABI_equal=True,raw_volatile_register_and_PC_identity_not_claimed=True,negative_columns_and_invalid_depths_guest_only=True,recursive_mutation_is_provider_extension=True,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
