"""Independent packet/home reference and actual original helper execution."""
from pathlib import Path
from tools.experiments import game_owner_effect_packet_1514e31c_packet as target_packet
from dataclasses import dataclass
from functools import lru_cache
import itertools,json,struct,sys
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_owner_action_dispatch_1514d15c_classifier_abi import at
R=target_packet.ROOT;O=target_packet.OUT;B=O/'baseline';ENTRY=0x1514e31c
OWNER,ALTERNATE,LAST,OUTPUT=0x30000,0x40000,0x45000,0x50000
ALLOC,ATTACH,FINAL,FACTORY,COPY=0x15189ff0,0x1514ec1c,0x15160a58,0x151407d0,0x10022ec0
GLOBALS=(0x800a5e18,0x800a5e1c)
PATTERNS=(0,0x80000000,1,0x7fffff,0x800000,0x3f800000,0xbf800000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc01234,0x7f801234,0xffffffff)
S=dict(D_800A5E18=GLOBALS[0],D_800A5E1C=GLOBALS[1],func_15189FF0=ALLOC,func_1514EC1C=ATTACH,func_15160A58=FINAL)
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
public=lambda m:{a:b for a,b in m.items()if not STACK-2048<=a<STACK+256}
@dataclass(frozen=True)
class Case:
 identity:int=0;success:int=0;mutation:int=0;home_mutation:int=0;seed:int=0;phase:int=0
def fixture(c):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,256)}
 for p,n in [(OWNER,1024),(ALTERNATE,1024),(LAST,1024),(OUTPUT,512)]:m.update({p+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for p,x in ((OWNER,c.identity),(ALTERNATE,c.identity^0x55),(LAST,c.identity^0xaa)):m[p+0x3b]=x
 for a,k in zip(GLOBALS,(0,7)):put(m,a,PATTERNS[(c.seed+k)%14])
 return m
def initialize(m,home):
 sp=home-304;d,s,r=sp+0x7c,sp+0xd4,sp+0x5c;owner=read(m,home)
 for off,v,n in [(0,3,1),(2,0x401,2),(4,0,2),(8,0,4),(12,0,4),(16,255,1),(17,230,1),(18,0,1),(19,255,1),(64,0x2012,4),(69,255,1)]:put(m,d+off,v,n)
 for i in range(6):put(m,d+28+4*i,0)
 for i,v in enumerate((0x42340000,0x425c0000,0x41c80000,0x42340000)):put(m,s+4*i,v)
 for off,v in [(16,0x3f000000),(20,0x3f000000),(24,read(m,GLOBALS[0])),(28,0),(32,read(m,GLOBALS[1])),(72,0x3f800000),(84,0)]:put(m,s+off,v)
 for i,v in enumerate((0,0,0x42c80000,0,0,0x44160000)):put(m,r+4*i,v)
 put(m,r+24,owner);put(m,r+28,12,1);put(m,r+29,m[owner+0x3b],1);put(m,r+30,2,1)
 return d,s,r
def mutate(m,c,home,stage):
 sp=home-304
 if c.mutation&(1<<stage):
  for p in (OWNER,ALTERNATE,LAST):m[p+0x3b]^=0x55+stage
  for a,x in zip(GLOBALS,(0x01234567,0x089abcde)):put(m,a,read(m,a)^x)
  for p,n,mul,bias in [(sp+0x7c,88,17,1),(sp+0xd4,92,23,3),(sp+0x5c,32,29,5)]:
   for i in range(n):m[p+i]=(i*mul+c.seed*13+stage*31+bias)&255
 if c.home_mutation&(1<<stage):put(m,home,ALTERNATE if stage==0 else LAST)
def callback_reference(m,c,home,deep):
 calls=[];snaps=[];d,s,r=initialize(m,home);answer=OUTPUT if c.success else 0
 calls.append((ALLOC,(d,s,r,2,3,0,0)));snaps.append((data(m,d,88),data(m,s,92),data(m,r,32)));m[s+88]=11
 if deep:calls.append((FACTORY,(s,128,d,2,3,0,0,0xffffffff,255,1)))
 mutate(m,c,home,0)
 if answer:
  if deep:calls.append((COPY,(answer+0x170,r,32)))
  for i,v in enumerate(data(m,r,32)):m[answer+0x170+i]=v
 calls.append((ATTACH,(answer,read(m,home),7)));mutate(m,c,home,1)
 v=home-304+0x50
 for i,value in enumerate((0,0,0x43160000)):put(m,v+4*i,value)
 calls.append((FINAL,(read(m,home),12,v,2,300,40,255,181,0,255,0,2,0,0,255,1)));snaps.append(data(m,v,12))
 return calls,snaps
def reference(c,deep):
 m=fixture(c);home=STACK+c.phase;put(m,home,OWNER);calls,snaps=callback_reference(m,c,home,deep);return public(m),calls,snaps
@lru_cache(None)
def helper_code():
 elf=(B/'conker/build/conker.us.elf').read_bytes();rom=(R/'conker/conker.us.bin').read_bytes();result={}
 for a,off,n in [(ALLOC,0x1b74a0,41),(COPY,0x22ec0,11)]:
  blob=rom[off:off+4*n];assert at(elf,a,4*n)==blob;result.update(zip(range(a,a+4*n,4),struct.unpack('>'+str(n)+'I',blob)))
 return result
class Oracle(FactoryOracle):
 def __init__(self,words,c,deep=False):
  self.home=STACK+c.phase;self.deep=deep;self.snaps=[]
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(OWNER,),connected=helper_code()if deep else {})
  self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  counts={ALLOC:7,ATTACH:3,FINAL:16,FACTORY:10,COPY:3};assert t in counts,hex(t);a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==ALLOC:self.snaps.append(tuple(data(self.memory,p,n)for p,n in zip(a[:3],(88,92,32))))
  if t==FINAL:self.snaps.append(data(self.memory,a[2],12))
 def hook(self,t):
  m=self.memory;c=self.case;a=self.calls[-1][1];sp=self.home-304
  if t==ALLOC:
   assert not self.deep;m[a[1]+88]=11;mutate(m,c,self.home,0);value=OUTPUT if c.success else 0
   if value:
    for i,v in enumerate(data(m,a[2],32)):m[value+0x170+i]=v
  elif t==FACTORY:assert self.deep;mutate(m,c,self.home,0);value=OUTPUT if c.success else 0
  elif t==ATTACH:mutate(m,c,self.home,1);value=0x81234567
  elif t==FINAL:value=0x76543210
  else:raise AssertionError(('unbounded helper',hex(t),hex(sp)))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def programs():
 result=[]
 for name,path in [('retail',O/'original-target.o'),('raw',O/'selected-owner.o'),('generic',O/'qualified-owner/selected-generic.o'),('generated',O/'qualified-owner/selected-generated.o')]:
  raw,rs=payload(path,'func_1514E31C');w=bound_blob(raw,rs,S);assert len(w)==123;result.append((name,w))
 assert result[0][1]==result[2][1]==result[3][1]
 assert struct.pack('>123I',*result[0][1])==(R/'conker/conker.us.bin').read_bytes()[0x17b7cc:0x17b9b8]
 return result
def post_state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.snaps,m.current_pc,m.delay_of)
def fault_state(m):return post_state(m)+(m.events,m.trace,m.all_accesses)
def main():
 target_packet.prepare()
 corpus=[Case(*v)for v in itertools.product((0,1,127,128,255),range(2),range(4),range(4),(0,1,11,12),(0,8))];progs=programs();seen=set();count=0
 for idx,c in enumerate(corpus):
  for deep in (False,True):
   want=reference(c,deep);models=[]
   for name,w in progs:
    m=Oracle(w,c,deep);m.run();assert(public(m.memory),m.calls,m.snaps)==want,(c,deep,name,'reference')
    assert m.r[2]==0x76543210 and m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
    models.append(m)
    if name=='retail':seen.update(m.visits)
   assert all(post_state(m)==post_state(models[0])for m in models[1:]),(c,deep,'post state')
  count+=1
  if idx%256==0:print(json.dumps(dict(cases=count,total=len(corpus))),flush=True)
 cuts=0
 for c in (Case(),Case(255,1,0,3,12,8),Case(128,1,3,3,11,0)):
  full=Oracle(progs[0][1],c,True);full.run()
  for cut in range(full.all_accesses):
   models=[]
   for name,w in (progs[0],progs[2],progs[3]):
    m=Oracle(w,c,True);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('missing fault',cut))
    models.append(m)
   assert all(fault_state(m)==fault_state(models[0])for m in models[1:]),(c,cut);cuts+=1
 controls=[];c=Case(255,1,0,3,12,0);want=reference(c,True);original=progs[0][1];assert original[85]==0x8fa50130 and original[109]==0x8fa40130 and original[111]==0x27a60050
 for name,index,value in [('stale-attach-owner',85,0x3c050003),('stale-final-owner',109,0x3c040003),('aliased-final-vector',111,0x27a6005c)]:
  bad=list(original);bad[index]=value;m=Oracle(bad,c,True);m.run();assert(public(m.memory),m.calls,m.snaps)!=want,name;controls.append(name)
 q=dict(cases_per_stream=count,streams=4,helper_modes=2,guest_runs=count*8,executed_words=sum(ENTRY+4*i in seen for i in range(123)),actual_packet_wrapper_words=sum(ALLOC+4*i in seen for i in range(41)),actual_memcpy_words=sum(COPY+4*i in seen for i in range(11)),normalized_fault_triples=cuts,all_incoming_home_mutation_masks=True,independent_packets_public_effects_and_owners_equal=True,all_raw_and_normalized_complete_post_states_equal=True,raw_literal_fault_prefix_parity_claimed=False,effective_controls=controls,providers='opaque factory attachment and final spawn',source_installed=target_packet.installed(),matching_credit=0)
 assert q['executed_words']==123 and q['actual_packet_wrapper_words']==41 and q['actual_memcpy_words']==11
 (O/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
