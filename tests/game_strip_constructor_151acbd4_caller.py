"""Complete original scene callers connected to retail/private strip constructors.

Other scene providers are bounded ABI contracts. This is not gameplay or an
instruction-fault/FCSR model; the constructor's separate ordered proof remains.
"""
from pathlib import Path
from dataclasses import dataclass,replace
from collections import Counter
import hashlib,itertools,json,math,struct,subprocess
from tools.experiments import game_strip_constructor_151acbd4_recovery as source
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_strip_constructor_151acbd4_private_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
R=source.ROOT;P=source.OUT;Q=source.OUT;STACK=g.STACK
CALLERS={0x1500fa64:(972,4),0x15010110:(304,6),0x150109d0:(144,1)}
OTHERS={0x1500f9d0:5,0x15195aa8:8,0x150e8854:0}
TABLES=0x80096320;COLOR=0x800dcd20
TAG_ROWS={0x1500fa64:((1,0x80096320),(2,0x80096338),(3,0x80096350),(5,0x80096380)),0x15010110:tuple((i+1,0x800963a0+i*24)for i in range(6)),0x150109d0:((1,0x80096430),)}
@dataclass(frozen=True)
class Case:
 caller:int=0x1500fa64;seed:int=0;phase:int=0;failure_mask:int=0;category:int=0;mutation:int=0
def cases():
 for caller,seed,phase,fail,category,mutation in itertools.product(CALLERS,(0,1),(0,8),(0,1,0x15,0x3f),(0,11,44,57),(0,31)):
  yield Case(caller,seed,phase,fail,category,mutation)
def objects(i):return 0x100000+i*0x1000,0x200000+i*0x1000,0x300000+i*0x2000
def regions(desc,i):
 record,points,vertices=objects(i)
 return ((g.RECORD,record,88),(g.DESC,desc,36),(g.POINTS,points,480),(g.VERTICES,vertices,2560),(g.TABLE,g.TABLE,768),(g.CATEGORY,g.CATEGORY,4),(g.MARK,g.MARK,4))
def canonical(memory,desc,i):return{a+k:memory[b+k] for a,b,n in regions(desc,i)for k in range(n)}
def scatter(memory,values,desc,i):
 for a,b,n in regions(desc,i):
  for k in range(n):memory[b+k]=values[a+k]
def case_for(c,i):return g.Case(seed=c.seed+i,outcome=not(c.failure_mask>>i&1),category=c.category,mutation=c.mutation,phase=c.phase,extra=0)
def packet(memory,desc,tag,row):
 result=bytearray(g.data(memory,desc,36));result[0]=tag;result[4:28]=g.data(memory,row,24);result[32]=0
 value=g.fp(int.from_bytes(result[8:12],'big'),int.from_bytes(result[20:24],'big'),'sub','left')&0x7fffffff
 result[28:32]=value.to_bytes(4,'big');return bytes(result)
def fixture(c,static):
 memory={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-4096,1024)}
 for i in range(6):
  for address,n in zip(objects(i),(88,480,2560)):
   memory.update({address+k:(k*29+c.seed*11+i*7+0x5a)&255 for k in range(n)})
 for address,n in ((g.TABLE,768),(g.CATEGORY,4),(g.MARK,4),(COLOR,0xa4),(0x800b0e00,8),(0x800902e8,4)):
  memory.update({address+k:(k*23+c.seed*7+0x35)&255 for k in range(n)})
 for k,b in enumerate(static):memory[TABLES+k]=b
 if c.seed:
  for row in range(len(static)//24):
   # Deliberately vary finite coordinates and zero/nonzero scene scales.
   for k,v in enumerate((31.75,70.5,-45.25,18.5,-120.75,6.25)):
    at=TABLES+row*24+k*4
    if at+4<=TABLES+len(static):g.put(memory,at,g.bits(v))
  # The three groups have alignment gaps; write each actual template explicitly.
  for row in {at for values in TAG_ROWS.values()for _,at in values}:
   for k,v in enumerate((31.75,70.5,-45.25,18.5,70.5 if row&8 else-120.75,6.25)):g.put(memory,row+4*k,g.bits(v))
 g.put(memory,g.CATEGORY,c.category)
 for i in range(64):g.put(memory,g.TABLE+12*i+6,(0,1,63,256,65535)[(i+c.seed)%5],2);g.put(memory,g.TABLE+12*i+8,(0,1,16,1024,65535)[(i+c.seed)%5],2)
 g.put(memory,0x800b0e00,0x11111111);g.put(memory,0x800b0e04,0x22222222);g.put(memory,0x800902e8,0x33333333)
 return memory
class Caller(g.Oracle):
 def __init__(self,words,parent,initial,c):
  connected=dict(zip(range(g.ENTRY,g.ENTRY+len(words)*4,4),words))
  FactoryOracle.__init__(self,parent,initial,c,entry=c.caller,s={},arguments=(),connected=connected)
  self.initial=dict(initial);self.expected=dict(initial);self.c=c;self.parents=[];self.descriptors=[];self.target_sites=Counter();self.index=-1;self.service=None;self.helper_calls=[];self.parent_frame=(-parent[0])&65535
  self.saved={i:self.r[i] for i in(*range(16,24),28,29,30,31)};self.saved_fp=tuple(self.f[20:]);self.sites=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==5:self.f[w>>6&31]=self.f[w>>11&31]&0x7fffffff;return
  return super().execute(w)
 def record_call(self,t):
  if t==g.ENTRY:
   self.index+=1;i=self.index;assert i<len(TAG_ROWS[self.c.caller])
   self.desc,extra=self.arguments(2);assert extra==0,('extra',extra)
   parent_frame=self.parent_frame
   assert self.r[29]==STACK+self.c.phase-parent_frame
   assert self.r[29]+24<=self.desc and self.desc+36<=STACK+self.c.phase,('descriptor frame',hex(self.desc),parent_frame)
   tag,row=TAG_ROWS[self.c.caller][i]
   expected=packet(self.initial,self.desc,tag,row)
   assert g.data(self.memory,self.desc,36)==expected,('descriptor',self.c,i,g.data(self.memory,self.desc,36).hex(),expected.hex())
   self.descriptors.append(expected.hex());self.sites.append(self.r[31]-8);self.target_sites[self.r[31]-8]+=1
   # Build an independent constructor reference from the independently checked packet.
   for k,b in enumerate(expected):self.expected[self.desc+k]=b
   before=canonical(self.expected,self.desc,i);after,calls,value=g.reference(before,case_for(self.c,i))
   if value:g.put(after,g.RECORD+56,objects(i)[1]);g.put(after,g.RECORD+72,objects(i)[2])
   scatter(self.expected,after,self.desc,i)
   self.expected_ctor_calls=calls;self.expected_result=value;self.service=g.Service(canonical(self.memory,self.desc,i),case_for(self.c,i))
   return
  count=g.COUNTS.get(t,OTHERS.get(t));assert count is not None,('unbounded provider',hex(t))
  args=tuple(self.arguments(count));self.pending=t,args
  if t in OTHERS:self.parents.append((t,args));return
  assert self.service is not None
  self.helper_calls.append((self.index,t,args))
 def hook(self,t):
  target,args=self.pending;assert target==t
  if t in OTHERS:answer=0
  else:
   i=self.index;self.service.m=canonical(self.memory,self.desc,i)
   if t==g.COPY:
    assert args==(objects(i)[0]+16,self.desc,36),('copy ABI',args)
    provider_args=(g.RECORD+16,g.DESC,36)
   else:provider_args=args
   answer=self.service.invoke(t,provider_args)
   assert self.service.calls==self.expected_ctor_calls[:len(self.service.calls)],('constructor calls',self.c,self.service.calls,self.expected_ctor_calls)
   scatter(self.memory,self.service.m,self.desc,i)
   if t==g.CREATE:answer=objects(i)[0] if answer else 0
   elif t==g.ALLOC:answer=objects(i)[1 if self.service.allocations==1 else 2]
   elif t==g.COPY:answer=objects(i)[0]+16
  for k in range(max(4,g.COUNTS.get(t,OTHERS.get(t,0)))):self.put(self.r[29]+4*k,0xb5000000+k,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+k for k in range(20)];self.hi=self.lo=0xdeadbeef;self.r[2]=answer
def public(m):return{p:v for p,v in m.items()if not STACK-4096<=p<STACK+1024}
def verify(words,parent,static,c):
 initial=fixture(c,static);machine=Caller(words,parent,initial,c).run()
 assert machine.index+1==CALLERS[c.caller][1]
 if c.caller==0x1500fa64:
  expected_calls=[(0x1500f9d0,tuple(g.u32(v)for v in row))for row in[(-1767,-1130,1057,-1608,1),(-2673,1819,2091,-1538,2),(-2160,878,1249,-1538,2),(-3029,1009,1625,-1538,2),(-3691,-611,-1063,-1607,1)]]
  for off,dest in ((0,0x800dcda4),(1,0x800dcda8),(2,0x800dcdac),(8,0x800dcdb0),(9,0x800dcdb4),(10,0x800dcdb8),(28,0x800dcdbc),(29,0x800dcdc0)):g.put(machine.expected,dest,g.bits(float(initial[COLOR+off])))
 elif c.caller==0x15010110:expected_calls=[(0x15195aa8,(x,0x33333333,0,0xffffffff,0,i,0,0xfffffff8))for i,x in enumerate((0x11111111,0x22222222))]
 else:expected_calls=[(0x150e8854,())]
 assert machine.parents==expected_calls,('parent calls',c,machine.parents,expected_calls)
 assert public(machine.memory)==public(machine.expected),('public',c,next(((hex(p),v,machine.expected.get(p))for p,v in public(machine.memory).items()if v!=machine.expected.get(p)),None))
 assert all(machine.r[i]==v for i,v in machine.saved.items())and tuple(machine.f[20:])==machine.saved_fp
 return machine
def load():
 assert source.check_inputs()==source.PIN['frozen_input_count']
 rom=(R/'conker/conker.us.bin').read_bytes();elf=(R/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,TABLES,0x128);static=elf[at:at+0x128]
 parents={entry:list(struct.unpack_from('>'+str(size//4)+'I',rom,entry-0x14fd2b50))for entry,(size,_)in CALLERS.items()}
 raw,refs=payload(P/'v63.o',source.NAME);assert hashlib.sha256(raw).hexdigest()==source.PIN['raw_sha256']
 from tools.tests import game_strip_constructor_151acbd4_oracle as streams
 code=streams.programs()
 return code,parents,static
def main():
 code,parents,static=load();baseline={};inputs={}
 counts={};coverage={entry:set()for entry in CALLERS};sites=Counter()
 for label,words in code.items():
  n=0
  for c in cases():
   m=verify(words,parents[c.caller],static,c);coverage[c.caller]|=m.visits&set(range(c.caller,c.caller+CALLERS[c.caller][0],4));sites.update(m.target_sites);n+=1
   key=tuple(c.__dict__.values());state=hashlib.sha256(b''.join(struct.pack('>IB',a,v)for a,v in sorted(m.memory.items()))).hexdigest()
   if label=='retail':baseline[key]=state
   else:assert baseline[key]==state,('complete mapped RAM/stack',label,c)
   if n%64==0:print(json.dumps(dict(label=label,cases=n)),flush=True)
  counts[label]=n
 expected_sites={entry+i*4 for entry,parent in parents.items()for i,w in enumerate(parent)if w>>26==3 and(0x10000000|((w&0x3ffffff)<<2))==g.ENTRY};assert set(sites)==expected_sites and len(sites)==6
 report=dict(complete_mapped_RAM_and_private_stack_compared=True,cases_per_stream=counts,complete_original_callers=3,static_call_sites=len(sites),call_sites={hex(k):v for k,v in sorted(sites.items())},caller_words={hex(k):CALLERS[k][0]//4 for k in CALLERS},caller_words_visited={hex(k):len(v)for k,v in coverage.items()},all_initialized_public_bytes_compared=True,source_installed=source.installed(),c_match_credit=0,opaque_scene_provider_contracts=True,FP_status_not_checked_by_guest=True)
 (Q/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

def controls():
 code,parents,static=load();words=code['raw'];rows=[]
 for entry,parent in parents.items():
  for j,w in enumerate(parent):
   if w>>26!=3 or(0x10000000|((w&0x3ffffff)<<2))!=g.ENTRY:continue
   at=next(i for i in range(j+1,max(-1,j-40),-1)if parent[i]==0x00002825)
   bad=parent[:];bad[at]=0x24050001
   try:verify(words,bad,static,Case(caller=entry))
   except AssertionError as error:assert isinstance(error.args[0],tuple) and error.args[0][0]=='extra',error
   else:raise AssertionError('ineffective caller-extra control')
   rows.append(dict(label='wrong-extra-size',site=hex(entry+4*j),patched_word=hex(entry+4*at)))
 for label,old,new in [('wrong-time-field',0xe46c004c,0xe46c0050),('wrong-reciprocal',0x46062203,0x46062202)]:
  bad=words[:];assert bad.count(old)==1,(label,hex(old));bad[bad.index(old)]=new
  try:verify(bad,parents[0x1500fa64],static,Case())
  except AssertionError as error:assert isinstance(error.args[0],tuple) and error.args[0][0]=='public',error
  else:raise AssertionError(('ineffective constructor control',label))
  rows.append(dict(label=label))
 assert len(rows)==8
 (Q/'caller-controls.json').write_text(json.dumps(dict(effective_controls=rows,count=8,source_installed=source.installed(),c_match_credit=0),indent=2)+'\n');return rows
if __name__=='__main__':main();controls()
