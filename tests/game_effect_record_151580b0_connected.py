"""Original copy and owner-entry helpers with bounded allocator/bzero models."""
import itertools,json,struct
from tools.experiments import game_effect_record_151580b0_match as p
from tools.experiments import game_effect_record_151580b0_match as norm
from tools.tests import game_effect_record_151580b0_oracle as g
ALLOCATE=0x10003C40;ZERO=0x100226F0;BUFFER=0x60000
def main():
 rom=(p.root/"conker/conker.us.bin").read_bytes();helpers=((g.COPY,0x22ec0,11),(g.ENTRY,0x18a930,21),(g.CLOCK,0x18a8f0,16));code={}
 for addr,off,size in helpers:code.update(zip(range(addr,addr+4*size,4),struct.unpack_from(">"+str(size)+"I",rom,off)))
 class Connected(g.Oracle):
  def __init__(self,*args,**kwargs):self.alloc_count=0;super().__init__(*args,**kwargs)
  def record_call(self,t):
   if t in (ALLOCATE,ZERO):self.calls.append((t,tuple(self.arguments(4 if t==ALLOCATE else 2))))
   else:super().record_call(t)
  def hook(self,t):
   if t not in (ALLOCATE,ZERO):return super().hook(t)
   a=self.calls[-1][1]
   if t==ALLOCATE:value=BUFFER+self.alloc_count*0x200;self.alloc_count+=1
   else:
    assert a[1]<=0x200
    for i in range(a[1]):self.memory[a[0]+i]=0
    value=0
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
 raw,refs=p.payload(p.out/"independent-selected.o");lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};symbols={name:lookup[name]for es in refs.values()for _,name in es};rawwords=p.bound_blob(raw,refs,symbols);normal,nrefs=norm.normalize(raw,refs);normalwords=p.bound_blob(normal,nrefs,symbols);retail=struct.unpack_from(">74I",rom,p.ROM);visited=set();n=0
 for alloc,owner,alternate,mode,count,phase in itertools.product((0,1),(0,1),(0,1),(0,255),(-1,0,1,3),(0,8)):
  c=g.Case(alloc,owner,alternate,mode,count,0,phase,n%3,owner_addr=3);memory=g.fixture(c)
  for i in range(5*0x200):memory[BUFFER+i]=(i*7+0xa5)&255
  want=dict(memory);a=g.args(c);calls=[(g.ALLOC,(0x55 if alternate else 0x37,a[6],g.u32(a[4]+0xf8),1,mode,1))];nalloc=0
  if alloc:
   calls.append((g.COPY,(g.RECORD+0x10,g.SOURCE,0x44)))
   for i in range(0x44):want[g.RECORD+0x10+i]=want[g.SOURCE+i]
   g.put(want,g.RECORD+0xd8,a[1]);g.put(want,g.RECORD+0xf4,a[2]);want[g.RECORD+0xdc]=0
   for i in range(4):g.put(want,g.RECORD+0xe0+i*4,0)
   g.put(want,g.RECORD+0xf0,0)
   if owner:
    for i in range(max(0,count+1)):
     buf=BUFFER+nalloc*0x200;nalloc+=1;calls.extend(((g.ENTRY,(3,)),(ALLOCATE,(288,1,2,0)),(ZERO,(buf,288))))
     for j in range(288):want[buf+j]=0
     g.put(want,g.RECORD+0xe0+i*4,buf)
    buf=BUFFER+nalloc*0x200;calls.extend(((g.CLOCK,()),(ALLOCATE,(16,1,2,0)),(ZERO,(buf,16))))
    for j in range(16):want[buf+j]=0
    g.put(want,g.RECORD+0xf0,buf)
  for ws in (retail,rawwords,normalwords):
   m=Connected(ws,c,connected=code,memory=memory);m.run();assert g.public(m.memory)==g.public(want),(c,"memory");assert m.calls==calls,(c,m.calls,calls);assert m.r[2]==(g.RECORD if alloc else 0);visited.update(m.visits)
  n+=1
 result=dict(cases=n,executions=3*n,original_helpers={hex(addr):sum(addr+4*i in visited for i in range(size))for addr,off,size in helpers},outer_and_nested_allocators_and_zero_modeled=True,overlapping_copy_excluded=True,source_installed=False);(p.out/"connected.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result),flush=True);return result
