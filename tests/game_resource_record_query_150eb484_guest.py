"""Bounded record-query contracts, hostile ABI clobbers and literal fault prefixes.

The unfinished geometry/effect implementations remain contracted providers.
Raw C has a translated private frame and different scratch registers; only the
literal retail streams claim identical full machine/fault-prefix state.
"""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_resource_record_query_150eb484_match as packet
o=packet.OUT;ENTRY=0x150eb484;A=0x30000;B=0x40000;CTX=0x50000;V=0x60000
symbols=dict(func_15083E90=0x15083e90,func_150A34B0=0x150a34b0,func_150A2864=0x150a2864,func_150EBC80=0x150ebc80,D_800D3098=0x800d3098,D_80088AA0=0x80088aa0,D_80088AB0=0x80088ab0,D_80088AD0=0x80088ad0)
tables=(1,2,4,3,45,46,47,48,49,50,51,52)
@dataclass(frozen=True)
class Case:
 context:int=1
 hit:int=-1
 mutation:int=0
 alias:int=0
 result:int=1
 phase:int=0
 seed:int=0
def args(c):
 start,end,out=V,V+16,V+32
 if c.alias==1:out=start
 if c.alias==2:out=end
 if c.alias==3:start=end=out=V
 if c.alias==4:start,end,out=STACK+c.phase+32,STACK+c.phase+48,STACK+c.phase+64
 return start,end,out
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-512,128)}
 for base,n in ((A-8,80*52+16),(B-8,80*52+16),(CTX-8,0x2ec+16),(V-8,64)):
  m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 put(m,symbols['D_800D3098'],A)
 for i,v in enumerate(tables):put(m,symbols['D_80088AA0']+4*i,v)
 put(m,symbols['D_80088AD0'],0x437f0000)
 for p in set(args(c)):
  for i in range(3):put(m,p+4*i,0x3f800000+0x800000*i)
 return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-512<=p<STACK+c.phase}
def vector(m,p):return tuple(read(m,p+4*i)for i in range(3))
def observation(m,t,a):
 return (t,a,read(m,symbols['D_800D3098']),read(m,CTX+0x2e8),tuple(vector(m,p)for p in a[1:4])if t==symbols['func_150A34B0']else ())
def effect(m,c,t,a,n):
 if c.mutation&1:
  old=read(m,symbols['D_800D3098']);put(m,symbols['D_800D3098'],B if old==A else A)
 if c.mutation&2:
  put(m,CTX+0x2e8,0x87654321^n)
  if t==symbols['func_150A34B0']:
   for i in range(3):put(m,a[3]+4*i,0x41000000+i*0x800000+n)
 if c.mutation&4 and t==symbols['func_150A2864']:
  put(m,symbols['D_800D3098'],B);put(m,CTX+0x2e8,0xfedcba98)
def reference(initial,c,argv=None):
 m=dict(initial);calls=[];obs=[];checks=0
 def call(t,a):
  nonlocal checks
  calls.append((t,a));obs.append(observation(m,t,a));effect(m,c,t,a,checks)
  if t==symbols['func_15083E90']:return CTX if c.context else 0
  if t==symbols['func_150A34B0']:
   result=c.result if checks==c.hit else 0;checks+=1;return result
  return 0xdeadbeef
 call(symbols['func_15083E90'],(9,));argv=args(c)if argv is None else argv
 if c.context:
  for i in range(4):
   index=read(m,symbols['D_80088AA0']+i*4);offset=index*52
   if call(symbols['func_150A34B0'],(read(m,symbols['D_800D3098'])+offset,*argv)):
    call(symbols['func_150A2864'],(index,1));put(m,CTX+0x2e8,i+1)
    call(symbols['func_150EBC80'],(read(m,symbols['D_800D3098'])+offset,255,1));return m,1,calls,obs
  for i in range(8):
   index=read(m,symbols['D_80088AB0']+i*4)
   if call(symbols['func_150A34B0'],(read(m,symbols['D_800D3098'])+index*52,*argv)):return m,1,calls,obs
 else:
  if call(symbols['func_150A34B0'],(read(m,symbols['D_800D3098'])+76*52,*argv)):put(m,read(m,symbols['D_800D3098'])+76*52+24,1)
 return m,0,calls,obs
class Machine(FactoryOracle):
 def __init__(self,words,c,arguments=None,entry=None,connected=None,memory=None):
  self.c=c;self.checks=0
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,connected=connected)
  self.initial=dict(self.memory);self.observations=[]
 def record_call(self,t):
  counts={symbols['func_15083E90']:1,symbols['func_150A34B0']:4,symbols['func_150A2864']:2,symbols['func_150EBC80']:3}
  a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.observations.append(observation(self.memory,t,a))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1];effect(self.memory,c,t,a,self.checks)
  if t==symbols['func_15083E90']:v=CTX if c.context else 0
  elif t==symbols['func_150A34B0']:v=c.result if self.checks==c.hit else 0;self.checks+=1
  else:v=0xdeadbeef
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=v&0xffffffff
def cases():
 rows=[Case(context=1,hit=h,mutation=m,alias=a,result=v,phase=8*(a&1),seed=h+1)for h,m,a,v in itertools.product(range(-1,12),range(8),range(5),(1,0x80000000))]
 rows += [Case(context=0,hit=h,mutation=m,alias=a,result=0xffffffff,phase=8*(a&1),seed=41)for h,m,a in itertools.product((-1,0),range(8),range(5))]
 return rows
def state(m):return m.memory,m.r,m.f,m.condition,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.all_accesses
def main():
 files=['original-target.o','normalized-target.o','qualified-owner/1188E0-generic.o','qualified-owner/1188E0-generated.o','selected-1188E0.o'];programs=[bound_blob(*payload(o/f,'func_150EB484'),symbols)for f in files];assert all(p==programs[0]for p in programs[:4]);rows=cases();seen=set();quads=0
 for c in rows:
  expected=reference(fixture(c),c);models=[]
  for ws in programs:
   m=Machine(ws,c).run();assert(public(m.memory,c),m.r[2],m.calls,m.observations)==(public(expected[0],c),*expected[1:]),('query contract',c,m.calls,expected[2]);models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:4]);seen.update(models[0].visits)
  assert all(models[-1].r[i]==models[-1].before[i]for i in (*range(16,24),28,29,30,31))
 for c in (Case(),Case(hit=0,mutation=7,alias=1),Case(hit=3,mutation=7),Case(hit=4,mutation=3),Case(hit=11,mutation=1),Case(context=0,hit=0,mutation=7),Case(context=0,hit=-1)):
  complete=Machine(programs[0],c).run()
  for cut in range(complete.all_accesses):
   models=[]
   for ws in programs[:4]:
    m=Machine(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing fault boundary')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);quads+=1
 missing=[hex(i*4)for i in range(100)if ENTRY+4*i not in seen];assert not missing,missing
 q=dict(cases_per_stream=len(rows),streams=5,retail_identical_streams=4,executed_retail_words=len(seen),fault_prefix_quads=quads,raw_frame_bytes=72,retail_frame_bytes=80,raw_public_memory_return_provider_arguments_observations_and_saved_registers_equal=True,raw_private_stack_and_scratch_register_and_fault_prefix_equality_not_claimed=True,geometry_and_effect_helpers_contracted=True,all_input_output_aliases_and_parent_stack_vectors_checked=True,all_priority_secondary_miss_and_null_context_paths=True,source_installed=packet.installed(),matching_credit=0)
 (o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
