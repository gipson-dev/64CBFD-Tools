"""Original61-word factory and11-word memcpy on the target's actual complete packet."""
from pathlib import Path
import hashlib,importlib.util,itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests import game_random_particle_150b5e34_guest as g
from tools.experiments import game_random_particle_150b5e34_match as p
r,o=g.r,g.o;ALLOC,COPY,CREATED=0x15167a68,0x10022ec0,0x50000
def pin(a,n,rom,elf):
 offset=a-0x15000000+0x2d4b0 if a>=0x15000000 else a-0x10000000;blob=rom[offset:offset+4*n];at=elf_slot_offset(elf,a,len(blob));assert elf[at:at+len(blob)]==blob
 return list(struct.unpack('>'+str(n)+'I',blob)),dict(address=hex(a),words=n,sha256=hashlib.sha256(blob).hexdigest(),matches_frozen_ELF=True)
class Capture(g.Machine):
 def hook(self,t):
  if t==g.FACTORY:self.factory_input=(dict(self.memory),self.calls[-1][1])
  super().hook(t)
def initialize(memory,c):
 for i in range(168):memory[CREATED+i]=(i*19+c.seed*7+0x31)&255
class Factory(g.FactoryOracle):
 def __init__(self,words,copy,c,memory,args):
  self.c=c;self.input_args=args;self.allocations=[];self.copies=[]
  super().__init__(words,memory,c,entry=g.FACTORY,arguments=args,connected=dict(zip(range(COPY,COPY+44,4),copy)))
  self.memory=dict(memory);self.r[29]=self.before[29]=self.target_home=g.home(c)-152
  for i,v in enumerate(args[4:],4):g.put(self.memory,self.target_home+4*i,v)
  self.initial=dict(self.memory);self.before_f=self.f[:]
 def record_call(self,t):
  assert t in(ALLOC,COPY),hex(t);a=tuple(map(g.u32,self.arguments(6 if t==ALLOC else 3)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==ALLOC:self.allocations.append(a)
  else:self.copies.append(a)
 def hook(self,t):
  assert t==ALLOC;g.put(self.memory,g.MARK,g.read(self.memory,g.MARK)+1)
  if self.c.outcome:initialize(self.memory,self.c)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=CREATED if self.c.outcome else 0
def verify(m,c,memory,args):
 expected=dict(memory);g.put(expected,g.MARK,g.read(expected,g.MARK)+1)
 assert args[1:4]==(1,0,0)
 assert m.allocations==[(82,args[5],168,1,args[4],1)]
 if c.outcome:
  initialize(expected,c)
  for i,v in enumerate(g.data(memory,args[0],112)):expected[CREATED+16+i]=v
  expected[CREATED+0x9c]=0
 assert m.copies==([(CREATED+16,args[0],112)]if c.outcome else[])
 assert g.public(m.memory,c)==g.public(expected,c)
 assert g.data(m.memory,args[0],112)==g.data(memory,args[0],112)
 assert m.r[2]==(CREATED if c.outcome else 0)and m.r[29]==g.home(c)-152 and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
def main():
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();factory,pf=pin(g.FACTORY,61,rom,elf);copy,pc=pin(COPY,11,rom,elf);fv=set();cv=set();count=copied=0;controls=[]
 for value,parity,outcome,mode in itertools.product((0,1,6,7,8,0x7fffffff,0x80000000,0xffffffff),range(4),(0,1),(0,255)):
  c=g.Case(rng=(value,parity&1,(parity>>1)&1),mode=mode,extra=g.u32(value^parity),outcome=outcome,mutation=1,phase=8*(outcome^(mode&1)),seed=parity,fcsr=parity)
  capture=Capture(g.streams()[0],c).run();memory,args=capture.factory_input;m=Factory(factory,copy,c,memory,args).run();verify(m,c,memory,args)
  fv|={p for p in m.visits if g.FACTORY<=p<g.FACTORY+244};cv|={p for p in m.visits if COPY<=p<COPY+44};count+=1;copied+=bool(outcome)
 unreachable={g.FACTORY+4*i for i in[*range(13,19),*range(42,56)]};assert fv==set(range(g.FACTORY,g.FACTORY+244,4))-unreachable and len(fv)==41;assert cv==set(range(COPY,COPY+44,4))
 c=g.Case(outcome=1);capture=Capture(g.streams()[0],c).run();memory,args=capture.factory_input
 for name,find,change in [('copy-width-108',lambda w:w==0x24060070,lambda w:w-4),('copy-destination-offset',lambda w:w==0x24640010,lambda w:w+4)]:
  bad=list(factory);at=next(i for i,w in enumerate(bad)if find(w));bad[at]=change(bad[at]);m=Factory(bad,copy,c,memory,args).run();assert m.r[2]==CREATED and m.r[29]==g.home(c)-152
  try:verify(m,c,memory,args)
  except AssertionError:controls.append(dict(name=name,supported_complete_helper_execution=True,rejected=True))
  else:raise AssertionError('Ineffective factory control')
 q=dict(original_helpers=[pf,pc],cases=count,successful_112byte_copies=copied,original_factory_words=61,actual_argument_path_factory_words_visited=41,unreachable_for_actual_kind1_null_extra_words=20,unreachable_indices=sorted((a-g.FACTORY)//4 for a in unreachable),all11_memcpy_words_visited=True,source_packet_bytes=112,seeded_unspecified_bytes_copied=14,bounded_allocation_bytes=168,allocation_kind=82,mode_u8_and_context32_forwarded=True,failure_and_success_returns=True,input_packet_unchanged=True,allocation_canaries_and_9c_zero_checked=True,effective_controls=controls,allocator_internals_contracted=True,no_helper_FCSR_claim=True,helper_matching_credit=0,source_installed=p.installed(),matching_credit=0)
 (o/'helpers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
