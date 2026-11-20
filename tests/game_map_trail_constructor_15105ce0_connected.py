"""Original allocator/list/copy/zero/PRNG/child code with bounded heap/curves."""
from dataclasses import replace
import csv,itertools,struct
from tools.tests import game_map_trail_constructor_15105ce0_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

HEAP,LIST,SEED,TABLE=0x10003C6C,0x15168A4C,0x800885B0,0x800DCE50
U64=(1<<64)-1

def prng(seed):
 mixed=(((seed<<63)&U64)>>31)|(((seed<<31)&U64)>>32)
 mixed^=((seed<<44)&U64)>>32
 return (((mixed>>20)&4095)^mixed)&U64

def original_code(root):
 names={'memcpy','bzero','func_15167A68','func_15168A4C','func_150ADA20','func_15130280'}
 with(root/'conker/retail_layout.us.txt').open()as f:rows=[r for r in csv.DictReader(f)if r['function']in names]
 # The handwritten 64-bit PRNG is outside the compiler-layout manifest.
 assert names-{row['function']for row in rows}=={'func_150ADA20'}
 rows.append(dict(function='func_150ADA20',section='game',address='0x150ADA20',end='0x150ADA68'))
 rom=(root/'conker/conker.us.bin').read_bytes();code={};spans={}
 for row in rows:
  start,end=int(row['address'],0),int(row['end'],0)
  offset=start-(0x10000000 if row['section']=='init'else 0x15000000)+ (0 if row['section']=='init'else 0x2D4B0)
  n=(end-start)//4;words=struct.unpack_from('>%dI'%n,rom,offset)
  code.update(zip(range(start,end,4),words));spans[row['function']]=(start,end,n)
 return code,spans

class Connected(g.ConstructorOracle):
 def __init__(self,words,memory,c,code,row):
  super().__init__(words,memory,c)
  self.code.update(code);self.r[7]=row;self.allocations=[];self.rng_expected=None;self.rng_returns=0
 def execute(self,w):
  pc=self.current_pc
  if g.RNG<=pc<g.RNG+72:
   op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
   imm=((w&65535)^32768)-32768
   if op==15:self.r[rt]=((w&65535)<<16)&U64
   elif op==55:self.r[rt]=self.get(g.u32(self.r[rs]+imm),8)
   elif op==63:self.put(g.u32(self.r[rs]+imm),self.r[rt],8)
   elif op==12:self.r[rt]=self.r[rs]&(w&65535)
   elif op==0 and fn in(37,38):self.r[rd]=(self.r[rs]|self.r[rt])if fn==37 else(self.r[rs]^self.r[rt])
   elif op==0 and fn in(56,58,60,62,63):
    shift=sa+(32 if fn in(60,62,63)else 0);value=self.r[rt]&U64
    if fn in(56,60):value=(value<<shift)&U64
    elif fn in(58,62):value>>=shift
    else:value=((value^(1<<63))-(1<<63))>>shift
    self.r[rd]=value&U64
    if fn==63:
     self.r[rd]=g.u32(value)
     assert self.r[rd]==g.u32(self.rng_expected)and self.get(SEED,8)==self.rng_expected
     self.rng_returns+=1
   else:return super().execute(w)
   self.r[0]=0;return
  return super().execute(w)
 def record_call(self,target):
  counts={**g.COUNTS,HEAP:5,LIST:2,g.ENTRY:4}
  assert target in counts,hex(target)
  args=tuple(map(g.u32,self.arguments(counts[target])));self.calls.append((target,args))
  self.provider_counts[target]=self.provider_counts.get(target,0)+1
  if target==g.ALLOCATE:self.allocations.append(args)
  if target==g.ENTRY:self.target_arguments=args
  if target==g.CHILD:self.snapshots.append(g.data(self.memory,args[0],112))
  if target==g.RNG:self.rng_expected=prng(self.get(SEED,8))
 def hook(self,target):
  if target!=HEAP:return super().hook(target)
  args=self.calls[-1][1];a=self.allocations[-1]
  assert args==(a[2],1,a[3],0,a[5]),('actual allocator heap ABI',args,a)
  at=len(self.allocations)-1
  value=(g.OUTPUT if self.case.success else 0)if at==0 else(0 if self.case.mode&(1<<(at-1))else 0x70000+at*0x100)
  for i in range(4):g.put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]
  self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def run(root,raw,retail):
 code,spans=original_code(root);coverage=set();count=0
 for pieces,ok,pattern,phase,row in itertools.product((0,1,7),(0,1),range(4),(0,8),(0,1)):
  c=g.Case(pieces,ok,pattern,pattern,phase);memory=g.fixture(c)
  for base,n in((0x70100,256),(0x70200,256),(TABLE,0x340)):
   memory.update({base+i:0 for i in range(n)})
  g.put(memory,SEED,(0,1,0x123456789ABCDEF0,0xFEDCBA9876543210)[pattern],8)
  models=[Connected(w,memory,c,code,row).run()for w in(raw,retail)]
  a,b=models
  assert(g.public(a.memory),a.calls,a.r[2],a.snapshots)==(g.public(b.memory),b.calls,b.r[2],b.snapshots),(c,row,'connected transfer')
  assert a.rng_returns==b.rng_returns==(5 if ok else 0)
  for m in models:coverage.update(m.visits)
  count+=1
 return dict(cases=count,original_provider_words={name:sum(pc in coverage for pc in range(start,end,4))for name,(start,end,_)in spans.items()},
             original_provider_slots={name:n for name,(_,_,n)in spans.items()},original_PRNG_independently_checked=True,
             modeled_heap=True,modeled_curve_and_sample_builders=True,gameplay_or_hardware_claim=False)

def run_callers(root,raw,retail):
 """Execute real call setup/return-use windows, not complete parent functions."""
 providers,_=original_code(root);rom=(root/'conker/conker.us.bin').read_bytes();count=0
 windows=((0x15104F84,5,0x8C,0,(0x15104F98,)),
          (0x151075B8,6,0x54,4,(0x151075D0,0x151075E0)),
          (0x1510789C,8,0xC0,12,(0x151078BC,0x151078D0)),
          (0x15107E00,8,0xBC,24,(0x15107E20,0x15107E34)))
 for (start,n,packet_offset,extra,ends),ok,phase,row in itertools.product(windows,(0,1),(0,8),(0,1)):
  c=g.Case(7,ok,2,0,phase);memory=g.fixture(c);home=g.STACK+phase;packet=home+packet_offset
  for i in range(-1024,768):memory.setdefault(g.STACK+i,(i*17+c.seed*13+0xA5)&255)
  g.write(memory,packet,g.data(memory,g.PACKET,80))
  for base,size in((0x70100,256),(0x70200,256),(TABLE,0x340),(0x60000,32),(0x62000,32)):
   memory.update({base+i:0 for i in range(size)})
  priority=0x80+row;memory[0x6000C]=priority;memory[0x60001]=row
  memory[home+0x14B]=memory[home+0x15B]=priority
  g.put(memory,home+0x14C,row);g.put(memory,home+0x15C,row)
  g.put(memory,SEED,0x123456789ABCDEF0,8)
  offset=start-0x15000000+0x2D4B0;setup=struct.unpack_from('>%dI'%n,rom,offset)
  models=[]
  for body in(raw,retail):
   m=Connected(body,memory,c,providers,row);m.entry=start
   m.code.update(zip(range(start,start+4*n,4),setup))
   for end in ends:m.code[end]=0
   m.r[4]=packet
   for reg,value in((18,0x60000),(19,0x60000),(17,0x62000)):
    m.r[reg]=m.before[reg]=value
   m.code=WindowCode(m.code,m);m.code.ends=ends
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller boundary not reached')
   assert m.target_arguments==(packet,extra,priority,row)
   assert m.r[2]==(g.OUTPUT if ok else 0)
   assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30))and m.f[20:]==m.saved_f
   assert m.allocations[0]==(64,row,7*52+9*12+extra+136,1,priority,1)
   if start==0x151075B8:assert g.read(m.memory,0x62008)==(g.OUTPUT if ok else 0)
   if start in(0x1510789C,0x15107E00):
    assert m.r[3]==(g.OUTPUT if ok else 0)
    if ok:assert m.r[4]==g.OUTPUT+7*52+9*12+136
   models.append(m)
  a,b=models
  assert(g.public(a.memory),a.calls,a.r[2],a.snapshots)==(g.public(b.memory),b.calls,b.r[2],b.snapshots)
  count+=1
 return dict(cases=count,original_caller_windows=4,original_target_and_providers_executed=True,
             NULL_and_return_pointer_uses=True,complete_parent_execution_claim=False)
