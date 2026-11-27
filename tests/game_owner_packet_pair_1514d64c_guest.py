"""Independent packet reference, actual 41-word helper and normalized faults.

Raw output is compared through its declared private-frame correspondence;
literal complete fault states are required only of the two normalized owners
and original routine. This is not a claim of raw literal private-state parity.
"""
from pathlib import Path
from tools.experiments import game_owner_packet_pair_1514d64c_packet as target_packet
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
R=target_packet.ROOT;O=target_packet.OUT;B=O/'baseline'
ENTRY=0x1514d64c;OWNER=0x30000;FIRST=0x50000;SECOND=0x60000
ALLOC=0x15189ff0;ATTACH=0x1514ec1c;FINAL=0x15160a58;FACTORY=0x151407d0;COPY=0x10022ec0
GLOBALS=(0x800a5df4,0x800a5df8,0x800a5dfc,0x800a5e00)
PATTERNS=(0,0x80000000,1,0x7fffff,0x800000,0x3f800000,0xbf800000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc01234,0x7f801234,0xffffffff)
S={f'D_{a:08X}':a for a in GLOBALS};S.update(func_15189FF0=ALLOC,func_1514EC1C=ATTACH,func_15160A58=FINAL)
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
public=lambda m:{a:b for a,b in m.items() if not STACK-2048<=a<STACK+256}
@dataclass(frozen=True)
class Case:
 identity:int=0;outcomes:int=0;mutation:int=0;seed:int=0;phase:int=0
def fixture(c,frame):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,256)}
 # The raw function's private bytes are related by SP-relative placement;
 # caller-owned homes and all public input bytes are identical.
 for i in range(-2048,0):m[home+i]=((i+frame)*17+c.seed*13+0xa5)&255
 for p,n in [(OWNER,1024),(FIRST,512),(SECOND,512)]:m.update({p+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 m[OWNER+0x3b]=c.identity
 for a,k in zip(GLOBALS,(0,3,7,11)):put(m,a,PATTERNS[(c.seed+k)%14])
 return m
def initialize(m,c,sp,phase):
 d,s,r=sp+0x74,sp+0xcc,sp+0x54
 for off,v,n in [(0,3,1),(2,0x401,2),(4,0,2),(8,0,4),(12,0,4),(16,255,1),(17,0,1),(18,0,1),(19,255,1),(64,0x12012,4),(69,255,1)]:put(m,d+off,v,n)
 for i in range(6):put(m,d+0x1c+4*i,0)
 dims=((0x41e00000,0x41e00000,0x40800000,0x41880000),(0x41f00000,0x41f00000,0x41200000,0x41800000))[phase]
 for i,v in enumerate(dims):put(m,s+4*i,v)
 for off,v in [(16,read(m,GLOBALS[1])if phase else 0x3f000000),(20,read(m,GLOBALS[1])if phase else 0x3f000000),(24,read(m,GLOBALS[2])if phase else 0x3f400000),(28,read(m,GLOBALS[2])if phase else 0x3e800000),(32,read(m,GLOBALS[3]if phase else GLOBALS[0])),(72,0x3f800000),(84,0)]:put(m,s+off,v)
 vectors=((0,0,0x41c80000,0,0,0x42960000),(0,0x41200000,0xc28c0000,0,0x41a00000,0xc30c0000))[phase]
 for i,v in enumerate(vectors):put(m,r+4*i,v)
 put(m,r+24,OWNER);put(m,r+28,5 if phase else 43,1);put(m,r+29,m[OWNER+0x3b],1);put(m,r+30,0 if phase else 1,1)
 return d,s,r
def mutate(m,c,sp,stage):
 if not c.mutation&(1<<stage):return
 m[OWNER+0x3b]^=0x31+stage*17
 for a,x in zip(GLOBALS[1:],(0x01234567,0x089abcde,0x06543210)):put(m,a,read(m,a)^x)
 for p,n,mul,bias in [(sp+0x74,88,17,1),(sp+0xcc,92,29,3),(sp+0x54,32,31,5)]:
  for i in range(n):m[p+i]=(i*mul+stage*(37 if n==88 else 41 if n==92 else 43)+c.seed+bias)&255
def reference(c,frame,connected):
 m=fixture(c,frame);sp=STACK+c.phase-frame;calls=[];snaps=[]
 for phase in (0,1):
  d,s,r=initialize(m,c,sp,phase);answer=(FIRST if phase==0 else SECOND)if c.outcomes&(1<<phase)else 0
  calls.append((ALLOC,(d,s,r,2,0,0,0)));snaps.append((data(m,d,88),data(m,s,92),data(m,r,32)))
  m[s+88]=11
  if connected:calls.append((FACTORY,(s,128,d,2,0,0,0,0xffffffff,255,1)))
  mutate(m,c,sp,phase*2)
  if answer:
   if connected:calls.append((COPY,(answer+0x170,r,32)))
   packet=data(m,r,32)
   for i,v in enumerate(packet):m[answer+0x170+i]=v
  calls.append((ATTACH,(answer,OWNER,9+phase)));mutate(m,c,sp,phase*2+1)
 calls.append((FINAL,(OWNER,5,sp+0x54,2,300,40,255,0,0,255,0,1,0,0,255,1)))
 snaps.append(data(m,sp+0x54,12));return public(m),calls,snaps
@lru_cache(None)
def helper_code():
 elf=(B/'conker/build/conker.us.elf').read_bytes();rom=(R/'conker/conker.us.bin').read_bytes();result={}
 for a,off,n in [(ALLOC,0x1b74a0,41),(COPY,0x22ec0,11)]:
  blob=rom[off:off+4*n];assert at(elf,a,4*n)==blob
  result.update(zip(range(a,a+4*n,4),struct.unpack('>'+str(n)+'I',blob)))
 return result
class Oracle(FactoryOracle):
 def __init__(self,words,c,frame=296,connected=False):
  self.frame=frame;self.parent_sp=STACK+c.phase-frame;self.deep=connected;self.snaps=[];self.packet_ordinal=0
  super().__init__(words,fixture(c,frame),c,entry=ENTRY,arguments=(OWNER,),connected=helper_code()if connected else {})
  self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  counts={ALLOC:7,ATTACH:3,FINAL:16,FACTORY:10,COPY:3};assert t in counts,hex(t)
  args=tuple(self.arguments(counts[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==ALLOC:self.snaps.append(tuple(data(self.memory,p,n)for p,n in zip(args[:3],(88,92,32))))
  if t==FINAL:self.snaps.append(data(self.memory,args[2],12))
 def hook(self,t):
  m=self.memory;c=self.case;a=self.calls[-1][1];sp=self.parent_sp;phase=self.packet_ordinal
  if t==ALLOC:
   assert not self.deep;m[a[1]+88]=11;mutate(m,c,sp,phase*2)
   value=(FIRST if phase==0 else SECOND)if c.outcomes&(1<<phase)else 0
   if value:
    for i,v in enumerate(data(m,a[2],32)):m[value+0x170+i]=v
   self.packet_ordinal+=1
  elif t==FACTORY:
   assert self.deep;mutate(m,c,sp,phase*2);value=(FIRST if phase==0 else SECOND)if c.outcomes&(1<<phase)else 0;self.packet_ordinal+=1
  elif t==ATTACH:mutate(m,c,sp,(phase-1)*2+1);value=0x80000000|phase
  elif t==FINAL:value=0x76543210
  else:raise AssertionError(('unbounded helper',hex(t)))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def programs():
 result=[]
 for name,path,frame in [('retail',O/'original-target.o',296),('raw',O/'selected-owner.o',304),('generic',O/'qualified-owner/selected-generic.o',296),('generated',O/'qualified-owner/selected-generated.o',296)]:
  b,rs=payload(path,'func_1514D64C');w=bound_blob(b,rs,S);assert len(w)==200;result.append((name,w,frame))
 assert result[0][1]==result[2][1]==result[3][1]
 assert struct.pack('>200I',*result[0][1])==(R/'conker/conker.us.bin').read_bytes()[0x17aafc:0x17ae1c]
 return result
def fault_state(m):return (m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.snaps,m.current_pc,m.delay_of,m.all_accesses)
def main():
 target_packet.prepare()
 progs=programs();seen=set();cases=0;helper_seen=set()
 corpus=[Case(*a)for a in itertools.product((0,1,127,128,255),range(4),range(16),(0,1,11,12),(0,8))]
 for idx,c in enumerate(corpus):
  for deep in (False,True):
   for name,w,frame in progs:
    expected,calls,snaps=reference(c,frame,deep);m=Oracle(w,c,frame,deep);m.run()
    assert public(m.memory)==expected and m.calls==calls and m.snaps==snaps,(c,deep,name,'reference mismatch',m.calls,calls)
    assert m.r[2]==0x76543210 and m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
    if name=='retail':seen.update(m.visits);helper_seen.update(m.visits if deep else ())
  cases+=1
  if idx%512==0:print(json.dumps(dict(cases=cases,total=len(corpus))),flush=True)
 cuts=0
 for c in (corpus[0],corpus[142],corpus[-1]):
  full=Oracle(progs[0][1],c,296,True);full.run()
  for cut in range(full.all_accesses):
   models=[]
   for name,w,frame in [progs[0],progs[2],progs[3]]:
    m=Oracle(w,c,frame,True);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('missing fault',cut))
    models.append(m)
   assert all(fault_state(m)==fault_state(models[0])for m in models[1:]),(c,cut);cuts+=1
 report=dict(cases_per_stream=cases,streams=4,helper_modes=2,guest_runs=cases*8,target_words_executed=sum(ENTRY+4*i in seen for i in range(200)),actual_factory_wrapper_words_executed=sum(ALLOC+4*i in helper_seen for i in range(41)),actual_memcpy_words_executed=sum(COPY+4*i in helper_seen for i in range(11)),normalized_literal_fault_triples=cuts,independent_packets_and_public_effects_equal=True,raw_private_frame_correspondence_only=True,raw_literal_private_fault_parity_claimed=False,factory_and_attachment_final_providers='opaque',source_installed=target_packet.installed(),matching_credit=0)
 assert report['target_words_executed']==200 and report['actual_factory_wrapper_words_executed']==41 and report['actual_memcpy_words_executed']==11
 (O/'guest-packet.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
 return report
if __name__=='__main__':main()
