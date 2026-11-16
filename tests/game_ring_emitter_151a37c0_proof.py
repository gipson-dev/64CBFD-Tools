"""Inductive whole-body transfer; ordinary mapped memory, private stack, o32."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import json,struct,sys
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests import game_ring_emitter_151a37c0_setup_screen as setup
from tools.experiments import game_ring_emitter_151a37c0_recovery as m
QUERY,CLEAN,COPY,FACTORY,RNG=0x151A4E34,0x151A4E9C,0x10022EC0,0x151491F4,0x150ADA20
OWNER,PAYLOAD,ENTRIES=('OWNER',),('PAYLOAD',),('ENTRIES',)
SAVES={**{off-288:('ENTRY',reg) for off,reg in ((0x58,16),(0x5C,17),(0x60,18),(0x64,19),(0x68,20),(0x6C,21),(0x70,22))},0x74-288:('RETURN',),**{0x28+4*i-288:('ENTRY_FP',20+(i^1)) for i in range(12)}}
def cache(s):return -144 if s.side=='raw' else -140
def spills(s):return (-164,-160) if s.side=='raw' else (-160,-156)
def bounds(v):
 if isinstance(v,int):return v,v
 if e.tagged(v,'LOAD'):return 0,(1<<(8*v[2]))-1
 if e.tagged(v,'LINEAR'):
  low=high=v[1]
  for term,k in v[2]:
   a,b=bounds(term);assert k<0x80000000;low+=a*k;high+=b*k
  assert high<=0xFFFFFFFF;return low,high
 raise AssertionError(('no unsigned interval',v))
class State(e.State):
 def __init__(self,side,phase):
  super().__init__('common',phase);self.side=side;self.phase=phase;self.r[29]=('STACK',0 if phase=='prefix' else -288)
  self.mem={} if phase=='prefix' else dict(SAVES);self.effects=[];self.private_writes=[];self.fp=[];self.fp_condition=None;self.fcsr=('FCSR',phase)
  self.r[16]=('ENTRY',16);self.r[31]=('RETURN',)
  if phase=='prefix':self.r[4]=OWNER;return
  self.r[17]=OWNER;self.r[18]=PAYLOAD;self.r[22]=ENTRIES
  if phase=='transition':self.r[16]=e.add(OWNER,16);return
  self.r[19]=24;self.r[20]=255;self.r[21]=('STACK',-108)
  for reg,label in ((20,'VALUE'),(22,'REMAINING'),(26,'TIME_STEP'),(28,'STEP_X'),(30,'STEP_Y'),(2,'STEP_Z'),(12,'VALUE_STEP')):self.f[reg]=(label,)
  self.f[24]=0x3F800000;self.mem.update({-108:('POSITION',0),-104:('POSITION',1),-100:('POSITION',2),cache(self):e.add(PAYLOAD,52),spills(self)[0]:('VALUE_STEP',),spills(self)[1]:('STEP_Z',)})
  self.r[8]=('CURSOR',)
  if phase=='epilogue':self.r[2]=('RETURN_VALUE',)
 def load(self,address,size,pool):
  if e.tagged(address,'STACK'):
   assert size==4 and address[1]%4==0;assert address[1] in self.mem,('uninitialized private load',self.phase,address)
   return self.mem[address[1]]
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   assert size==4 and address[1]%4==0;self.mem[address[1]]=value;self.private_writes.append((address[1],size));return
  super().store(address,size,value);self.effects.append(self.trace[-1])
class Program(e.Program):
 def __init__(self,words,side,terms):
  super().__init__(words,b'',m.ENTRY);self.side=side;self.terms=terms;self.shift=4 if side=='raw' else 0
  self.epilogue=0x3E4+self.shift;self.core=0x28C+self.shift;self.tail=0x374+self.shift;self.finish=0x3C0+self.shift
 def step(self,s,w):
  op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
  if op==0 and fn==37 and ((rt==0 and e.tagged(s.r[rs],'STACK')) or(rs==0 and e.tagged(s.r[rt],'STACK'))):s.r[w>>11&31]=s.r[rs] if rt==0 else s.r[rt]
  elif op in(53,61):
   at=e.add(s.r[rs],((w&65535)^32768)-32768);assert e.tagged(at,'STACK') and at[1]%8==0
   if op==61:s.store(at,4,s.f[rt+1]);s.store(e.add(at,4),4,s.f[rt])
   else:s.f[rt+1]=s.load(at,4,b'');s.f[rt]=s.load(e.add(at,4),4,b'')
  elif op==17 and rs==4:s.f[w>>11&31]=s.r[rt]
  elif op==17 and rs==16 and fn in(0,1,2,3,4,5,7,60):
   fs,fd=w>>11&31,w>>6&31;args=(s.f[fs],) if fn in(4,5,7) else(s.f[fs],s.f[rt]);event=(fn,args,s.fcsr)
   s.fp.append(event);s.effects.append(('FP',event));value=self.terms.term('FP_VALUE',*event);s.fcsr=self.terms.term('FP_STATUS',*event)
   if fn==60:s.fp_condition=value
   else:s.f[fd]=value
  elif op==0 and fn==27:
   a,b=s.r[rs],s.r[rt];low,high=bounds(b);assert 1<=low<=high<=256,('unproved RNG divisor',low,high)
   s.lo=('UDIV',a,b);s.hi=('UREM',a,b);e.assume(s,e.pred('EQ',b,0),False)
  else:super().step(s,w)
 def call(self,s,target):
  counts={QUERY:2,CLEAN:1,COPY:3,FACTORY:8,RNG:0};assert target in counts,('wrong provider',hex(target));assert s.r[29]==('STACK',-288)
  n=counts[target];args=list(s.r[4:4+min(n,4)])
  if n>4:args += [s.load(('STACK',-288+16+4*i),4,b'') for i in range(n-4)]
  ordinal=s.calls[target];s.calls[target]+=1
  if target==COPY:
   snapshot=-72 if self.side=='raw' else -76
   if ordinal==0:
    assert args==[('STACK',snapshot),PAYLOAD,48],('snapshot copy-in',args,snapshot)
    packet=tuple(s.load(e.add(args[1],4*i),4,b'') for i in range(12))
    event=('COPY_IN',PAYLOAD,48,packet,s.fcsr)
    for i,v in enumerate(packet):s.store(('STACK',snapshot+4*i),4,v)
   else:
    assert ordinal==1 and args[1:]==[('STACK',snapshot),48],('snapshot copy-out',args)
    packet=tuple(s.load(('STACK',snapshot+4*i),4,b'') for i in range(12));event=('COPY_OUT',args[0],48,packet,s.fcsr)
    for i,v in enumerate(packet):s.store(e.add(args[0],4*i),4,v)
   s.trace.append(event);s.effects.append(event)
  else:
   for v in args:e.plain(v)
   if target==QUERY:assert args==[s.r[18],e.add(OWNER,16)],('query ABI',args)
   elif target==CLEAN:assert args==[OWNER],('cleanup ABI',args)
   elif target==FACTORY:assert args[:6]==[300,0xFFFFFFFF,10,0,5,48] and args[7]==0,('factory ABI',args)
   event=('CALL',target,tuple(args),s.fcsr);s.trace.append(event);s.effects.append(event)
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',target,ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',target,ordinal,reg)
  for i in range(max(4,n)):s.store(('STACK',-288+4*i),4,('CALL_HOME',target,ordinal,i))
  s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',target,ordinal);s.hi=('CALL_HI',target,ordinal);s.lo=('CALL_LO',target,ordinal);s.fcsr=('CALL_FCSR',target,ordinal)
 def paths(self,start,stops,initial):
  active=[(start,initial)];answers={};work=0
  while active:
   pc,s=active.pop();work+=1;s.steps+=1;assert work<30000 and s.steps<450,('unbounded phase',initial.phase,pc,work)
   if s.steps>1 and pc in stops:
    key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers,('duplicate phase path',key);answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;floating=op==17 and rs==8
   if floating or op in(4,5,20,21):
    if floating:
     condition=s.fp_condition;likely=bool(rt&2)
     if not rt&1:condition=e.negate(condition)
    else:
     condition=e.pred('EQ',s.r[rs],s.r[rt]);likely=op in(20,21)
     if op in(5,21):condition=e.negate(condition)
    for taken in e.choices(s,condition):
     n=deepcopy(s);e.assume(n,condition,taken)
     if taken or not likely:self.step(n,self.instruction(pc+4))
     active.append((pc+4+4*(((w&65535)^32768)-32768) if taken else pc+8,n))
   elif op==3:
    s.r[31]=self.entry+pc+8;self.step(s,self.instruction(pc+4));self.call(s,((self.entry+pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2));active.append((pc+8,s))
   elif op==0 and w&63==8:
    target=s.r[rs];self.step(s,self.instruction(pc+4));assert target==('RETURN',),('wrong return target',target);active.append((-4,s))
   else:self.step(s,w);active.append((pc+4,s))
  return answers
def saved(s):
 assert all(s.mem.get(at)==v for at,v in SAVES.items()),('saved frame changed',s.phase)
 assert s.r[29]==('STACK',-288)
def common(s,label):
 if s.phase=='epilogue':
  assert s.r[29]==('STACK',0) and s.r[31]==('RETURN',) and s.r[2]==('RETURN_VALUE',)
  assert all(s.r[i]==('ENTRY',i) for i in(16,17,18,19,20,21,22,23,28,30)),('epilogue GPRs',s.r[16:24])
  assert tuple(s.f[20:])==tuple(('ENTRY_FP',i) for i in range(20,32)),('epilogue FPR pairs',s.f[20:])
  assert not s.private_writes and not s.effects;return s.trace,s.fcsr,s.r[2]
 saved(s)
 if s.phase=='prefix':allowed=set(SAVES)|set(range(-288,-272,4))
 elif s.phase=='transition':allowed=set(range(-288,-256,4))|set(range(-72 if s.side=='raw' else -76,(-72 if s.side=='raw' else -76)+48,4))
 elif s.phase=='core':allowed={*spills(s),*range(-288,-272,4)}
 elif s.phase=='tail':allowed={-108,-104,-100}
 else:allowed=set()
 assert all(n==4 and at in allowed for at,n in s.private_writes),('private-write escape',s.phase,s.private_writes)
 if s.phase in('prefix','transition'):
  assert tuple(s.f[20:])==tuple(('ENTRY_FP',i) for i in range(20,32)),('saved FPR lifetime',s.phase)
 else:
  for i in range(21,32,2):assert s.f[i]==('ENTRY_FP',i)
 if label=='return':assert s.r[2] in(0,1),('return register',s.r[2]);live=(s.r[2],)
 elif s.phase=='prefix':
  assert s.r[17]==OWNER and s.r[16]==e.add(OWNER,16)
  live=(s.r[17],s.r[18],s.r[22],s.r[16],s.f[4] if label=='movement' else None)
 else:
  assert (s.r[17],s.r[18],s.r[19],s.r[20],s.r[21],s.r[22])==(OWNER,PAYLOAD,24,255,('STACK',-108),ENTRIES)
  live=(tuple(s.f[i] for i in(20,22,24,26,28,30,2,12)),tuple(s.mem[x] for x in(-108,-104,-100)),s.mem[cache(s)],s.r[8] if label=='repeat' else None)
 return s.effects,setup.read_epochs(s.trace),s.fp,s.fcsr,live
def prove(raw,retail,require_identical_epilogue=True,verbose=True):
 assert len(raw)==266 and len(retail)==265 and raw[0]==retail[0]==0x27BDFEE0
 if require_identical_epilogue:assert raw[-16:]==retail[-16:]
 counts={}
 for phase,start_raw,start_retail,stops_raw,stops_retail in(
  ('prefix',0,0,{0xEC:'transition',0x158:'movement',0x3E8:'return'},{0xEC:'transition',0x158:'movement',0x3E4:'return'}),
  ('transition',0xEC,0xEC,{0x3E8:'return'},{0x3E4:'return'}),
  ('core',0x290,0x28C,{0x378:'tail'},{0x374:'tail'}),
  ('tail',0x378,0x374,{0x290:'repeat',0x3C4:'finish'},{0x28C:'repeat',0x3C0:'finish'}),
  ('finish',0x3C4,0x3C0,{0x3E8:'return'},{0x3E4:'return'}),
  ('epilogue',0x3E8,0x3E4,{-4:'returned'},{-4:'returned'})):
  terms=Terms();a=Program(raw,'raw',terms).paths(start_raw,stops_raw,State('raw',phase));b=Program(retail,'retail',terms).paths(start_retail,stops_retail,State('retail',phase))
  assert a.keys()==b.keys(),('phase predicates',phase,len(a),len(b),list(a.keys()-b.keys())[:1],list(b.keys()-a.keys())[:1])
  for key in a:
   x,y=common(a[key],key[0]),common(b[key],key[0]);assert x==y,('phase transfer',phase,key,x,y)
  counts[phase]=len(a)
  if verbose:print(phase,len(a),'passed',flush=True)
 # Both entry routes reach +0x158 with F4 already loaded, one via a likely
 # delay slot. Seed that arbitrary common live value instead of replaying +154.
 terms=Terms();answers=[]
 for words,side in((raw,'raw'),(retail,'retail')):
  s=setup.State(288);s.phase='setup';s.side=side;s.f[4]=('OWNER_X',);s.mem.update(SAVES)
  p=Program(words,side,terms);answers.append(p.paths(0x158,{p.core-4:'loop',p.epilogue:'return'},s))
 a,b=answers;assert a.keys()==b.keys(),('setup predicates',len(a),len(b))
 for key in a:
  x,y=a[key],b[key];assert (x.effects,setup.read_epochs(x.trace),setup_relation(x,key[0]))==(y.effects,setup.read_epochs(y.trace),setup_relation(y,key[0])),('actual setup transfer',key)
 assert len(a)==8;counts['setup']=8
 return dict(phase_paths=counts,setup_paths=8,epilogue_identical=True,private_frame_preserved=True,ordered_FP_FCSR=True,opaque_o32_providers=True,all_48_snapshot_bytes=True,RNG_divisor=[1,256],whole_function_study=True,source_installed=False,c_match_credit=0)

def setup_relation(s,label):
 allowed={-24,-20,-76,-108,-104,-100,-144} if s.side=='raw' else {-16,-20,-144,-108,-104,-100,-140}
 assert all(n==4 and at in allowed for at,n in s.private_writes),('setup private-write escape',s.side,s.private_writes)
 saved(s)
 for i in range(21,32,2):assert s.f[i]==('ENTRY_FP',i)
 if label=='return':assert s.r[2]==1;return ()
 assert (s.r[19],s.r[20],s.r[21])==(24,255,('STACK',-108))
 assert {-108,-104,-100,cache(s)}<=s.mem.keys() and s.mem[cache(s)]==e.add(PAYLOAD,52)
 return tuple(s.f[i] for i in(20,22,24,26,28,30,2,12)),tuple(s.mem[x] for x in(-108,-104,-100)),s.mem[cache(s)],s.fcsr

def controls(raw,retail):
 mutations={}
 def flip(label,at,mask):
  bad=raw.copy();bad[at//4]^=mask;mutations[label]=bad
 flip('owner-live-gate',0x50,1<<26)
 flip('owner-identity-byte',0x64,1)
 flip('query-output-vector',0x8C,4)
 flip('initial-position-copy',0xA8,4)
 flip('snapshot-copy-extent',0x104,4)
 flip('factory-parameter-extent',0x10C,4)
 flip('factory-output-offset',0x138,4)
 flip('entry-stride',0x294,7<<16)
 flip('entry-lifetime-source',0x2B8,2)
 flip('RNG-range-signed-load',0x2DC,4<<26)
 flip('entry-phase-destination',0x2CC,1)
 flip('ring-count-increment',0x344,0xFFFE)
 flip('value-step-operation',0x380,1)
 flip('pending-decrement-operation',0x3A8,1)
 flip('final-time-destination',0x3E0,8)
 flip('saved-S6-restore',0x41C,0x1C)
 flip('saved-F30-pair-restore',0x400,0x18)
 rejected=[]
 for label,bad in mutations.items():
  try:prove(bad,retail,False,False)
  except AssertionError as error:rejected.append(dict(label=label,rejected=True,reason=str(error)[:400]))
  else:raise AssertionError(('ineffective whole-body control',label))
 renamed=raw.copy();swap=lambda n:10 if n==9 else 9 if n==10 else n
 for i,w in enumerate(raw):
  op,rs,rt,rd=w>>26,w>>21&31,w>>16&31,w>>11&31
  if op==17:
   if rs in(0,4):w=(w&~(31<<16))|(swap(rt)<<16)
  elif op not in(2,3):
   w=(w&~(31<<21))|(swap(rs)<<21)
   if op not in(49,53,57,61):w=(w&~(31<<16))|(swap(rt)<<16)
   if op==0:w=(w&~(31<<11))|(swap(rd)<<11)
  renamed[i]=w
 assert renamed!=raw;prove(renamed,retail,True,False)
 return dict(negatives=rejected,temporary_GPR_renaming_accepted=True,source_installed=False,c_match_credit=0)
if __name__=='__main__':
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.experiments.game_path_heading_turn_roles import bound_blob
 raw,retail=m.programs()['raw'],m.retail();report=prove(raw,retail);out=m.OUT/'whole-proof-report.json';out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
 tests=controls(raw,retail);out.with_name('whole-proof-controls.json').write_text(json.dumps(tests,indent=2)+'\n');print(json.dumps(tests),flush=True)
