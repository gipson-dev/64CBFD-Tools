"""Actual direct caller, classifier tables, RNG64, notification and constructor."""
import itertools,json,struct
from dataclasses import replace
from tools.tests import game_owner_payload_effect_151b4cd0_oracle as g
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.game_paired_float_approach_1505a250_oracle import Oracle as FloatOracle,bits,floating,rounded,divide
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_actor_effect_type_selector_candidates import GROUPS
WINDOW,END=0x15194770,0x15194780
DISPATCH,ALLOC,DELETE,TRANSFORM,SEED,MATRIX=0x1516944C,0x15167A68,0x1516972C,0x15143134,0x800885B0,0x70000
HELPERS=((g.SELECT,252),(g.NOTIFY,60),(g.RNG,72),(g.CREATE,304),(g.COPY,44))
def original(rom,a,n):return struct.unpack_from('>%dI'%(n//4),rom,a-0x15000000+0x2D4B0 if a>=0x15000000 else a-0x10000000)
def caller(rom,ws,c):
 c=replace(c,selector=255,category=1);memory=g.fixture(c);code=dict(zip(range(g.ENTRY,g.ENTRY+380,4),ws));code[END]=0;m=g.Oracle(original(rom,WINDOW,16),memory,c,entry=WINDOW,connected=code);m.r[16]=c.owner;m.code=WindowCode(m.code,m);m.code.ends=(END,)
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing caller continuation')
 expected,calls,value,packets,copies=g.reference(m.initial,c);assert g.public(m.memory)==g.public(expected);assert m.calls==[(g.ENTRY,(c.owner,255,1))]+calls;assert m.r[2]==value and m.packets==packets and m.copies==copies;assert m.r[16]==c.owner and m.r[29]==g.STACK+c.phase and m.r[31]==END;return m
def census(rom):
 sites=[];literals=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
  if w==g.ENTRY:literals.append(4*i)
  if w>>26 in(2,3)and(w&0x3FFFFFF)<<2==g.ENTRY&0x0FFFFFFF:sites.append(4*i)
 assert sites==[0x1C1C28]and not literals
 return dict(direct_J_JAL_ROM=sites,literal_pointers=literals,actual_parent='func_151945CC',owner_S0_selector_FF_category_1=True,current_parent_placeholder_unchanged=True,full_parent_qualified=False)
class RealOracle(g.Oracle,RngInstructions,FloatOracle):
 def __init__(self,ws,memory,c,code,valid=True,matrix=False,invalidate=False):
  self.c=c;self.s=g.symbols();self.valid=valid;self.matrix=matrix;self.invalidate=invalidate;self.notifications=[];self.factory_copies=[]
  FactoryOracle.__init__(self,ws,memory,c,entry=g.ENTRY,arguments=(c.owner,c.selector,c.category),connected=code);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.packets=[];self.copies=[]
 def record_call(self,t):
  counts={g.SELECT:1,g.NOTIFY:3,g.RNG:0,g.CREATE:4,g.COPY:3,DISPATCH:3,ALLOC:6,DELETE:1,TRANSFORM:4};assert t in counts,hex(t);a=tuple(map(g.u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==g.CREATE:self.packets.append(g.data(self.memory,a[0],48))
  if t==g.COPY:
   (self.copies if a[2]==1 else self.factory_copies).append(g.data(self.memory,a[1],a[2]))
  if t==DISPATCH:self.notifications.append(g.data(self.memory,a[1],8))
 def hook(self,t):
  a=self.calls[-1][1];value=0x87654321
  if t==DISPATCH:pass
  elif t==ALLOC:
   if self.invalidate:g.put(self.memory,g.OWNER+0x3B,g.read(self.memory,g.OWNER+0x3B,1)^1,1)
   value=g.OUTPUT if self.c.outcome else 0
  elif t==DELETE:pass
  elif t==TRANSFORM:
   assert a==(g.OUTPUT+0x24,g.OUTPUT+0x40,MATRIX+128,g.OUTPUT),a
   for i,v in enumerate((0x3F800000,0x40000000,0x40400000)):g.put(self.memory,g.OUTPUT+0x40+4*i,v)
  else:raise AssertionError(('Unconnected original helper',hex(t)))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=value
def real_helpers(rom,elf,programs):
 code={};seen=set();pairs=0
 for a,n in HELPERS:
  data=original(rom,a,n);at=elf_slot_offset(elf,a,n);assert elf[at:at+n]==struct.pack('>%dI'%len(data),*data),(hex(a),'helper bytes changed');code.update(zip(range(a,a+n,4),data))
 # Both classifier jump tables and all twenty 16-byte descriptor records.
 spans=((0x800A4350,129*4),(0x800A4554,23*4),(0x800A3FE6,20*16));pool={}
 for a,n in spans:
  at=elf_slot_offset(elf,a,n);pool.update({a+i:v for i,v in enumerate(elf[at:at+n])})
 kind_of={identity:kind for kind,identities in GROUPS.items()for identity in identities}
 cases=[(identity,SEEDS[identity%len(SEEDS)],True,False,False,1)for identity in range(256)]
 cases.extend((0x87,seed,valid,matrix,invalidate,outcome)for seed,valid,matrix,invalidate,outcome in itertools.product(SEEDS,(False,True),(False,True),(False,True),(0,1)))
 for identity,seed,valid,matrix,invalidate,outcome in cases:
  kind=kind_of.get(identity,99);c=g.Case(kind=kind,identity=identity,outcome=outcome,random=g.u32(next_seed(seed)),selector=identity,category=0x87654321);memory=g.fixture(c);memory.update(pool);g.put(memory,SEED,seed,8);g.put(memory,g.OWNER,int(valid));g.put(memory,g.OWNER+0x1D4,MATRIX if matrix else 0);g.put(memory,g.OWNER+0x74,0,1);memory.update({MATRIX+i:(i*13+90)&255 for i in range(0xC0)})
  expected,opaque,answer,packets,copies=g.reference(memory,c);calls=[];factory_copies=[];real_answer=0
  for t,a in opaque:
   if t==g.COPY:continue
   calls.append((t,a))
   if t==g.NOTIFY:calls.append((DISPATCH,(40,g.STACK+c.phase-96,22)))
   if t==g.RNG:g.put(expected,SEED,next_seed(seed),8)
   if t==g.CREATE:
    calls.append((ALLOC,(40,g.u32(c.category),89,1,c.selector&255,1)))
    if invalidate:g.put(expected,g.OWNER+0x3B,g.read(expected,g.OWNER+0x3B,1)^1,1)
    if not outcome:continue
    calls.append((g.COPY,(g.OUTPUT+16,a[0],48)));factory_copies.append(packets[0])
    for i,b in enumerate(packets[0]):g.put(expected,g.OUTPUT+16+i,b,1)
    if not valid or invalidate:calls.append((DELETE,(g.OUTPUT,)));continue
    if matrix:
     calls.append((TRANSFORM,(g.OUTPUT+0x24,g.OUTPUT+0x40,MATRIX+128,g.OUTPUT)))
     for i,v in enumerate((0x3F800000,0x40000000,0x40400000)):g.put(expected,g.OUTPUT+0x40+4*i,v)
    else:g.put(expected,g.OUTPUT+0x3A,14,1)
    g.put(expected,g.OUTPUT+0x4C,bits(divide(1.,30.)));g.put(expected,g.OUTPUT+0x50,0);real_answer=g.OUTPUT
    payload=g.STACK+c.phase-56;calls.append((g.COPY,(g.OUTPUT+0x58,payload,1)));g.put(expected,g.OUTPUT+0x58,g.read(expected,payload,1),1)
  # The opaque model's final byte copy must be removed on constructor rejection.
  if opaque and any(t==g.CREATE for t,_ in opaque)and not real_answer:expected[g.OUTPUT+0x58]=memory[g.OUTPUT+0x58]
  models=[]
  for ws in programs:
   m=RealOracle(ws,memory,c,code,valid,matrix,invalidate);m.run();assert g.public(m.memory)==g.public(expected),(identity,seed,valid,matrix,invalidate,outcome,'real-public');assert m.calls==calls,(identity,'calls',m.calls,calls);assert g.u32(m.r[2])==real_answer;(models.append(m));seen.update(pc for pc in m.visits if any(a<=pc<a+n for a,n in HELPERS))
   assert m.packets==packets and m.factory_copies==factory_copies
   if any(t==g.NOTIFY for t,_ in opaque):assert g.read(dict(enumerate(m.notifications[0])),0)==g.OWNER and m.notifications[0][4]==identity
  a,b=models;assert(a.memory,a.r,a.f,a.trace,a.calls,a.packets,a.copies)==(b.memory,b.r,b.f,b.trace,b.calls,b.packets,b.copies);pairs+=1
 return dict(pairs=pairs,all_256_identities=True,all_12_seed_patterns=True,original_helper_words=sum(n//4 for a,n in HELPERS),covered_helper_words=len(seen),two_original_classifier_tables=True,all_20_descriptor_class_records=True,real_notification_RNG64_factory_and_copy=True,allocator_dispatch_delete_transform_are_modeled=True,FCSR_or_hardware_qualified=False)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();elf=(g.out/'frozen/conker/build/conker.us.elf').read_bytes();programs=(g.words(g.out/'selected.o'),original(rom,g.ENTRY,380));pairs=0;seen=set()
 for owner,kind,cl,mu,outcome,phase in itertools.product((0,g.OWNER),(1,99),(1,2),(0,15,48),(0,1),(0,8)):
  c=g.Case(owner=owner,kind=kind,class_byte=cl,mutation=mu,outcome=outcome,phase=phase);a,b=[caller(rom,ws,c)for ws in programs];assert(a.memory,a.r,a.f,a.trace,a.calls,a.packets,a.copies)==(b.memory,b.r,b.f,b.trace,b.calls,b.packets,b.copies);pairs+=1;seen.update(pc for pc in a.visits if WINDOW<=pc<END)
 report=dict(census=census(rom),caller_pairs=pairs,caller_window_words=len(seen),real_helpers=real_helpers(rom,elf,programs),full_parent_or_gameplay_qualified=False);(g.out/'callers.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
