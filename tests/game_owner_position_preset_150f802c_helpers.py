"""Original256-word factory and11-word copy on actual captured target packets."""
from pathlib import Path
from dataclasses import dataclass,replace
import hashlib,itertools,json,struct,sys
from functools import lru_cache
sys.path.insert(0,str(Path.cwd()));pass
from tools.tests import game_owner_position_preset_150f802c_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_owner_position_preset_150f802c_match as p
r,o=p.ROOT,p.OUT
ALLOC,NODEALLOC,LOAD,DESTROY,FREE,VIEW,FINAL=0x15167a68,0x10003c40,0x151336a8,0x15168a9c,0x10004074,0x1515d480,0x1515d440
COUNT,REF,HEAD,TAIL,VIEWS,DEFAULT=0x800dc63c,0x800dc468+2*47,0x800dc460,0x800dc464,0x80082fa0,0x800a3868
NODE,CHAIN,RESOURCE=0x70000,0x71000,0x73000
signed=lambda x:((x&0xffffffff)^0x80000000)-0x80000000
@lru_cache(maxsize=1)
def default_bits():
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();start,base,_,_=g.load_game_data_layout(r/'conker');at=elf_slot_offset(elf,DEFAULT,4);blob=elf[at:at+4];assert blob==rom[start+DEFAULT-base:start+DEFAULT-base+4];return int.from_bytes(blob,'big')
@dataclass(frozen=True)
class Case:
 phase:int=0
 seed:int=0
 total:int=0
 refs:int=0
 outcome:int=1
 node_success:int=1
 load_success:int=1
 match:int=0
 old_head:int=1
 views:int=0
 mutate:int=0
def fixture(memory,c):
 m=dict(memory)
 for a,n in [(NODE,16),(CHAIN,16*102),(RESOURCE,16)]:m.update({a+i:(i*23+c.seed*7+0x31)&255 for i in range(n)})
 for i in range(101):
  node=CHAIN+16*i;g.put(m,node,RESOURCE);g.put(m,node+4,CHAIN+16*(i+1)if i<100 else 0);g.put(m,node+8,CHAIN+16*(i-1)if i else 0);g.put(m,node+12,47 if c.refs and i==c.match else 1000+i,2);m[node+14]=0
 g.put(m,COUNT,c.total);g.put(m,REF,c.refs,2);g.put(m,HEAD,CHAIN if c.old_head else 0);g.put(m,TAIL,CHAIN+16*100 if c.old_head else 0);g.put(m,VIEWS,g.u32(c.views));g.put(m,DEFAULT,default_bits());return m
def provider(memory,c,t,args,ordinal):
 g.put(memory,g.MARK,g.read(memory,g.MARK)+1)
 if t==ALLOC:
  if c.mutate&1:g.put(memory,COUNT,0xffffffff)
  return g.OUTPUT if c.outcome else 0
 if t==NODEALLOC:return NODE if c.node_success else 0
 if t==LOAD:
  if c.load_success:
   for i in range(16):memory[NODE+i]=(i*19+c.seed*11+0x45)&255
   g.put(memory,NODE,RESOURCE)
  return c.load_success
 if t==VIEW:
  if c.mutate&2:g.put(memory,VIEWS,1)
  return 0x74000+4*ordinal
 if t==FINAL:return 0x75000
 if t in(DESTROY,FREE):return 0xdeadbeef
 assert t==g.COPY and 0<=args[2]<=128;blob=g.data(memory,args[1],args[2])
 for i,v in enumerate(blob):memory[args[0]+i]=v
 return args[0]
def reference(initial,c,args):
 m=dict(initial);calls=[]
 def call(t,a):calls.append((t,a));return provider(m,c,t,a,len(calls))
 if signed(g.read(m,COUNT))>300:return m,calls,0
 assert args[1:5]==(3,255,0,180)
 output=call(ALLOC,(25,args[6],548,1,args[5],1))
 if not output:return m,calls,0
 if g.read(m,REF,2)==0:
  node=call(NODEALLOC,(16,1,2,1))
  if not node:call(DESTROY,(output,));call(FREE,(output,));return m,calls,0
  if not call(LOAD,(47,node,output)):call(DESTROY,(output,));call(FREE,(output,));call(FREE,(node,));return m,calls,0
  old=g.read(m,HEAD);g.put(m,node+4,old)
  if old:g.put(m,old+8,node)
  else:g.put(m,TAIL,node)
  g.put(m,HEAD,node);g.put(m,node+8,0);g.put(m,node+12,47,2);m[node+14]=0
 else:
  node=g.read(m,HEAD);remaining=100
  while g.read(m,node+12,2)!=47:
   remaining-=1;node=g.read(m,node+4)
   if remaining<=0:break
  if remaining<=0:call(DESTROY,(output,));call(FREE,(output,));return m,calls,0
 g.put(m,REF,g.read(m,REF,2)+1,2);g.put(m,output+0x8c,node);call(g.COPY,(output+16,args[0],124))
 m[output+0x149]=m[output+0x148]=0
 for at in(0x134,0x138,0x13c,0x140):g.put(m,output+at,0)
 g.put(m,output+0x144,g.bits(1.));assert all(g.read(m,args[0]+at)==0 for at in(0x34,0x38,0x3c))
 for at in(0x130,0x128):g.put(m,output+at,0)
 m[output+0x12c]=m[output+0x12d]=0;g.put(m,output+0x110,g.read(m,DEFAULT));g.put(m,COUNT,g.read(m,COUNT)+1);m[output+0x150]=0;g.put(m,output+0x14c,3);g.put(m,output+0x168,255)
 for at in(0x154,0x158,0x15c,0x160,0x164):g.put(m,output+at,0)
 i=0
 while i<=signed(g.read(m,VIEWS)):
  g.put(m,output+0x154+4*i,call(VIEW,(3,)));i+=1
 g.put(m,output+0x164,call(FINAL,()));g.put(m,output+0x60,g.read(m,output+0x60)&~0x200000)
 return m,calls,output
class Capture(g.Machine):
 def hook(self,t):
  if t==g.FACTORY:self.factory_input=(dict(self.memory),self.calls[-1][1])
  super().hook(t)
class Factory(g.FactoryOracle):
 def __init__(self,words,copy,c,memory,args):
  self.c=c;self.provider_ordinal=0;self.packet=args[0]
  super().__init__(words,memory,replace(c,phase=c.phase&8),entry=g.FACTORY,arguments=args,connected=dict(zip(range(g.COPY,g.COPY+44,4),copy)))
  self.memory=dict(memory);self.r[29]=self.before[29]=g.STACK+c.phase
  for i,v in enumerate(args[:4]):self.r[4+i]=v
  for i,v in enumerate(args[4:],4):g.put(self.memory,self.r[29]+4*i,v)
  self.initial=dict(self.memory);self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==4:
   fs,fd=w>>11&31,w>>6&31;assert self.f[fs]in(0,0x80000000);self.f[fd]=0;self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  counts={ALLOC:6,NODEALLOC:4,LOAD:3,DESTROY:1,FREE:1,VIEW:1,FINAL:0,g.COPY:3};assert t in counts,hex(t);a=tuple(map(g.u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t!=g.COPY,'The actual11word copy must execute';value=provider(self.memory,self.c,t,self.calls[-1][1],len(self.calls))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def pin(a,n,rom,elf):
 at=a-0x15000000+0x2d4b0 if a>=0x15000000 else a-0x10000000;blob=rom[at:at+4*n];slot=elf_slot_offset(elf,a,len(blob));return list(struct.unpack('>'+str(n)+'I',blob)),dict(address=hex(a),words=n,sha256=hashlib.sha256(blob).hexdigest(),matches_frozen_ELF=elf[slot:slot+len(blob)]==blob)
def verify(m,c,args):
 expected,calls,value=reference(m.initial,c,args)
 # Original memcpy is a real helper, so its body has no provider marker effect.
 for t,a in calls:
  if t==g.COPY:g.put(expected,g.MARK,g.read(expected,g.MARK)-1)
 assert m.calls==calls,(c,'calls',m.calls,calls);gc=g.Case(phase=c.phase)
 assert g.public(m.memory,gc)==g.public(expected,gc),(c,'public memory');assert g.data(m.memory,args[0],124)==g.data(m.initial,args[0],124)
 assert m.r[2]==value and m.r[29]==g.STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return value
def main():
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();words,pf=pin(g.FACTORY,256,rom,elf);copy,pc=pin(g.COPY,11,rom,elf);assert not pf['matches_frozen_ELF']and pc['matches_frozen_ELF']
 capture=Capture(g.programs()[0],g.Case()).run();initial,args=capture.factory_input;cases=[]
 for total in(0x80000000,0xffffffff,0,300,301,0x7fffffff):cases.append(Case(total=total))
 for outcome,nodeok,loadok,oldhead,views,mutate in itertools.product((0,1),(0,1),(0,1),(0,1),(-1,0,3),range(4)):cases.append(Case(outcome=outcome,node_success=nodeok,load_success=loadok,old_head=oldhead,views=views,mutate=mutate))
 for refs,match,views,mutate in itertools.product((1,0x7fff,0xffff),(0,1,98,99,100),(-1,0,3),range(4)):cases.append(Case(refs=refs,match=match,views=views,mutate=mutate))
 seen=set();copy_seen=set();success=0
 for i,c in enumerate(cases):
  c=replace(c,phase=-200,seed=i&15);m=Factory(words,copy,c,fixture(initial,c),args).run();success+=bool(verify(m,c,args));seen|={p for p in m.visits if g.FACTORY<=p<g.FACTORY+1024};copy_seen|={p for p in m.visits if g.COPY<=p<g.COPY+44}
 assert copy_seen==set(range(g.COPY,g.COPY+44,4));controls=[];c=Case(phase=-200)
 for name,find,change in [('descriptor-copy-width',lambda w:w==0x2406007c,lambda w:w-4),('allocation-size',lambda w:w==0x24c60170,lambda w:w-4),('new-node-id-offset',lambda w:w==0xa4eb000c,lambda w:w-2)]:
  bad=list(words);at=next(i for i,w in enumerate(bad)if find(w));bad[at]=change(bad[at]);m=Factory(bad,copy,c,fixture(initial,c),args).run();assert m.r[2]==g.OUTPUT and m.r[29]==g.STACK+c.phase
  try:verify(m,c,args)
  except AssertionError:controls.append(dict(name=name,supported_complete_execution=True,rejected=True))
  else:raise AssertionError('Ineffective helper control')
 missing=sorted(i for i in range(256)if g.FACTORY+4*i not in seen);assert missing==[15,21,22,25,26,59,60,*range(98,117),*range(184,198)]
 q=dict(original_factory=pf,original_memcpy=pc,cases=len(cases),successful_allocations=success,original_factory_words=256,visited_factory_words=len(seen),unvisited_factory_indices=missing,unreachable_for_actual_inputs=dict(duplicate_load=1,alternate_kind=2,alternate_pool=4,retained_resource_flag_path=19,non_null_state_copy=14),all11_memcpy_words_visited=True,actual_descriptor_copy_bytes=124,actual_allocation_bytes=548,actual_kind=25,actual_pool=1,resource_id=47,null_state_default_path=True,default_state_coefficient_pinned=hex(default_bits()),all_count_node_allocation_load_and_search_failures=True,search_boundary_indices=[0,1,98,99,100],views_negative_zero_three_and_provider_mutation=True,full_allocation_node_list_counters_and_canaries_checked=True,original_sqrt_of_fixed_zero_only=True,no_helper_FCSR_claim=True,allocator_loader_and_view_providers_contracted=True,semantic_factory_C_remains_unmatched_and_uncredited=True,effective_controls=controls,source_installed=p.installed(),matching_credit=0)
 (o/'helpers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
