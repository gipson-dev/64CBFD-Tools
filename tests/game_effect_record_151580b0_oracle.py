"""Private record constructor screen against original guest words."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_effect_record_151580b0_match as p
from tools.experiments import game_effect_record_151580b0_match as n
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
SOURCE=0x30000;OWNER=0x40000;RECORD=0x50000;COUNT=0x80082FA0;ALLOC=0x15167A68;COPY=0x10022EC0;ENTRY=0x1515D480;CLOCK=0x1515D440
u32=lambda x:x&0xffffffff
s32=lambda x:((x&0xffffffff)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 alloc:int;owner:int;alternate:int;mode:int;count:int;mutation:int;phase:int=0;seed:int=0;extra:int=0x12345678;bytes:int=0x7fffff40;parameter:int=0x87654321;data:int=SOURCE;owner_addr:int=OWNER
def args(c):return(c.data,c.owner_addr if c.owner else 0,c.extra,c.alternate,c.bytes,c.mode,c.parameter)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 for base,size in ((SOURCE,256),(OWNER,256),(RECORD,0x180)):
  m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(size)})
 put(m,COUNT,u32(c.count));return m
def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}
def effects(m,c,target,ordinal):
 if target==ALLOC and c.mutation&1:m[c.data+0x10]^=0x5a;put(m,COUNT,2)
 if target==COPY and c.mutation&2:m[RECORD+0xdc]^=0x80
 if target==ENTRY and ordinal==0:
  if c.mutation&4:put(m,COUNT,0xffffffff)
  if c.mutation&8:put(m,COUNT,3)
  if c.mutation&16:m[RECORD+0xe0]^=0x20
def reference(c,initial):
 m=dict(initial);calls=[];a=args(c);calls.append((ALLOC,(0x55 if (a[3]&255) else 0x37,a[6],u32(a[4]+0xf8),1,a[5]&255,1)));effects(m,c,ALLOC,0)
 if not c.alloc:return m,calls,0
 calls.append((COPY,(RECORD+0x10,c.data,0x44)));chunk=bytes(m[c.data+i]for i in range(0x44))
 for i,v in enumerate(chunk):m[RECORD+0x10+i]=v
 effects(m,c,COPY,0);put(m,RECORD+0xd8,a[1]);put(m,RECORD+0xf4,a[2]);m[RECORD+0xdc]=0
 for i in range(4):put(m,RECORD+0xe0+4*i,0)
 put(m,RECORD+0xf0,0)
 if a[1]:
  i=0
  while i<=s32(read(m,COUNT)):
   assert i<8;calls.append((ENTRY,(a[1],)));effects(m,c,ENTRY,i);put(m,RECORD+0xe0+4*i,0xabc00000+i);i+=1
  calls.append((CLOCK,()));put(m,RECORD+0xf0,0x1234abcd)
 return m,calls,RECORD
class Oracle(FactoryOracle):
 def __init__(self,words,c,connected=None,memory=None):
  self.c=c;self.entry_count=0;super().__init__(words,fixture(c)if memory is None else memory,c,entry=p.ENTRY,arguments=args(c),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  counts={ALLOC:6,COPY:3,ENTRY:1,CLOCK:0};assert t in counts,hex(t);self.calls.append((t,tuple(self.arguments(counts[t]))))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1];ordinal=self.entry_count if t==ENTRY else 0
  if t==COPY:
   assert a==(RECORD+0x10,c.data,0x44);chunk=bytes(self.memory[c.data+i]for i in range(0x44))
   for i,v in enumerate(chunk):self.memory[RECORD+0x10+i]=v
  effects(self.memory,c,t,ordinal)
  if t==ALLOC:value=RECORD if c.alloc else 0
  elif t==COPY:value=RECORD+0x10
  elif t==ENTRY:value=0xabc00000+ordinal;self.entry_count+=1
  else:assert t==CLOCK;value=0x1234abcd
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
def main():
 raw,refs=p.payload(p.out/"independent-selected.o");lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};syms={name:lookup[name]for es in refs.values()for _,name in es};candidate=p.bound_blob(raw,refs,syms);normal,nrefs=n.normalize(raw,refs);normalized=p.bound_blob(normal,nrefs,syms);retail=struct.unpack_from(">74I",(p.root/"conker/conker.us.bin").read_bytes(),p.ROM);cases=[]
 for i,(alloc,owner,alternate,mode,count,mutation)in enumerate(itertools.product((0,1),(0,1),(0,1,0x100,0x101),(0,0x1ff),(-1,0,2,3),(0,1,2,4,8,16,27))):cases.append(Case(alloc,owner,alternate,mode,count,mutation,(i&1)*8,i%3))
 visits=[set(),set(),set()]
 for c in cases:
  machines=[]
  for index,ws in enumerate((retail,candidate,normalized)):
   m=Oracle(ws,c);m.run();want,calls,value=reference(c,m.initial);assert public(m.memory)==public(want),(c,"public");assert m.calls==calls,(c,m.calls,calls);assert m.r[2]==value,(c,m.r[2],value);assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];visits[index].update(m.visits);machines.append(m)
  a,b,d=machines;assert(a.memory,a.r,a.f,a.calls,a.trace)==(d.memory,d.r,d.f,d.calls,d.trace),(c,"normalized state")
 report=dict(cases=len(cases),executions=3*len(cases),retail_words_visited=sum(p.ENTRY+4*i in visits[0]for i in range(74)),normalized_complete_state=True,dynamic_count_and_helper_mutations=True,helpers_modeled=True,overlapping_copy_not_qualified=True,source_installed=False,byte_exact=False);(p.out/"guest.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report),flush=True);return report
if __name__=="__main__":main()
