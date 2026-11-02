"""Embedded integer oscillators: live providers, binary32 steps and private byte homes."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,math,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_random_selector_outputs_match import next_seed
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset

OWNER,SECOND,THIRD,SEED,FACTOR=0x30000,0x30400,0x30800,0x800885B0,0x8009F740
INTEGER,FLOAT=0x150ADA20,0x150ADA68
TARGETS=((0x150C5E0C,0xF32BC,'layout'),(0x151AB090,0x1D8540,'twin-layout'))
u32=lambda v:v&0xFFFFFFFF
half=lambda v:((v&65535)^32768)-32768
f32=lambda v:floating(bits(v))
class DomainBoundary(Exception):pass
class ZeroDivisor(Exception):pass

@dataclass(frozen=True)
class Case:
 remaining:int=-1
 ticks:int=1
 notification:int=1
 phase:int=0
 profile:int=0
 rng:int=17
 random:int=0x3E800000
 mutation:int=0
 alias:int=0
 seed:int=0x123456789ABCDEF0

def cases():
 rows=[]
 for i,(remaining,ticks,profile,rng,phase) in enumerate(itertools.product((-32768,-1,0,1,32767),(0,1,65535,65536,0x7FFFFFFF,0x80000000,0xFFFFFFFF),range(4),(0,1,0x80000000,0xFFFFFFFF),(0,8))):
  rows.append(Case(remaining,ticks,(0,128,255)[i%3],phase,profile,rng,(0,0x3E800000,0x3F400000,0x3F800000)[i%4],i%4))
 rows.extend(Case(notification=b,phase=p,profile=b%4,rng=u32(b*0x1234567),mutation=b%4)for b,p in itertools.product(range(256),(0,8)))
 rows.extend(Case(remaining=-1,ticks=t,phase=p,alias=a,mutation=m)for a,t,p,m in itertools.product((1,2,3),(0,1,0x80000000,0xFFFFFFFF),(0,8),(0,1,2,3)))
 rows.extend(Case(remaining=-1,notification=255,phase=p,mutation=m)for p,m in itertools.product((0,8),(4,8,12)))
 # Profiles 4/5 force signed-output addition to wrap while the float-to-int
 # conversion itself remains representable. These must stay in native tests.
 rows.extend(Case(remaining=99,ticks=0,phase=p,profile=q)for p,q in itertools.product((0,8),(4,5)))
 return rows

def address(c,s):return s['clock']-(0xC4,0xB4,0x24)[c.alias-1]if c.alias else OWNER

def fixture(c,s):
 p=address(c,s);home=STACK+c.phase;m={home+i:(i*17+165)&255 for i in range(-2048,2048)}
 for base,n in((p-16,0xF0),(SECOND-16,0xF0),(THIRD-16,0xF0),(s['clock']-8,24),(SEED-8,24),(FACTOR-8,24)):m.update({base+i:(i*29+c.notification*13+90)&255 for i in range(n)})
 profiles=((0.,3.,4.,.25,-32768,0,0),(2.,-5.,-10.,.5,32767,32767,1000),(-1.,2.,16777216.,.125,-7,-32768,-2000000000),(7.,11.,0.,.25,5,31,0x7FFFFFFF),(0.,1.,2147487744.,.5,0,1,0x7FFFFFFF),(0.,1.,-2147487744.,.5,0,1,0x80000000))
 base,amp,target,gain,minimum,span,value=profiles[c.profile]
 for at,v,n in((0x24,value,4),(0xB4,c.notification,1),(0xB8,bits(base),4),(0xBC,bits(amp),4),(0xC0,bits(target),4),(0xC4,c.remaining,2),(0xC6,minimum,2),(0xC8,span,2),(0xCC,bits(gain),4)):put(m,p+at,v,n)
 put(m,SECOND+0x24,12345);put(m,THIRD+0x24,u32(-12345));put(m,s['clock'],c.ticks);put(m,SEED,c.seed,8);put(m,FACTOR,0x37800080)
 return m

def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+2048}

def effect(m,c,s,ordinal,home):
 p=address(c,s)
 if ordinal==1 and c.mutation&1:
  m[p+0xB4]=165;put(m,p+0xC6,-123,2);put(m,p+0xC8,7,2);put(m,p+0xBC,bits(6.));put(m,p+0xB8,bits(-17.));put(m,p+0x24,77);put(m,p+0xCC,bits(.125));put(m,s['clock'],0x87654321)
 if ordinal==2 and c.mutation&2:
  put(m,p+0xB8,bits(11.));put(m,p+0xBC,bits(-8.));put(m,p+0xCC,bits(.25));put(m,p+0x24,1000);put(m,p+0xC4,-7,2)
 if ordinal==1 and c.mutation&4:put(m,home,SECOND)
 if ordinal==2 and c.mutation&8:put(m,home,THIRD)

def reference(initial,c,s,real=False,home=None):
 home=STACK+c.phase if home is None else home;m=dict(initial);p=address(c,s);active=int(m[p+0xB4]!=0);m[p+0xB4]=0
 put(m,p+0xC4,half(half(read(m,p+0xC4,2))-read(m,s['clock'])),2);calls=[]
 if half(read(m,p+0xC4,2))<0:
  calls.append((s['integer'],()));put(m,home,p)
  if real:value=next_seed(read(m,SEED,8));put(m,SEED,value,8);value&=0xFFFFFFFF
  else:effect(m,c,s,1,home);value=c.rng
  divisor=u32(half(read(m,p+0xC8,2))+1)
  if not divisor:raise ZeroDivisor
  put(m,p+0xC4,value%divisor+half(read(m,p+0xC6,2)),2)
  calls.append((s['floating'],()))
  if real:value=next_seed(read(m,SEED,8));put(m,SEED,value,8);sample=f32(float(value&65535)*floating(read(m,FACTOR)))
  else:effect(m,c,s,2,home);sample=floating(c.random)
  put(m,p+0xC0,bits(f32(f32(sample*floating(read(m,p+0xBC)))+floating(read(m,p+0xB8)))))
  owner=read(m,home)
 else:owner=p
 value=signed(read(m,owner+0x24));delta=f32(f32(floating(read(m,p+0xC0))-f32(float(value)))*floating(read(m,p+0xCC)))
 if not math.isfinite(delta)or not -2147483648<=math.trunc(delta)<=2147483647:raise DomainBoundary
 put(m,owner+0x24,u32(value+math.trunc(delta)))
 return public(m,c),calls,active

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,raw=False,connected=None,target_entry=None):
  self.c,self.s,self.root_entry,self.raw=c,s,entry,raw;self.home=STACK+c.phase-(32 if target_entry is not None else 0);self.target_entry=entry if target_entry is None else target_entry;self.pointer_live=False;self.flag_live=False;self.initial=dict(memory);self.trace_pcs=[];frame=self.home-40;self.private_projection={frame+i:memory[frame+i]for i in(*range(0x18,0x20),0x23,0x27)}
  super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(address(c,s),))
 def execute(self,w):
  op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==0 and fn==27 and not u32(self.r[rt]):raise ZeroDivisor
  if op==17 and rs in(16,20)and fn in(13,32):
   if rs==16 and fn==13:
    value=floating(self.f[rd]);assert math.isfinite(value)and -2147483648<=math.trunc(value)<=2147483647;self.f[sh]=u32(math.trunc(value))
   elif rs==20 and fn==32:self.f[sh]=bits(float(signed(self.f[rd])))
   else:raise AssertionError(hex(w))
   return
  island=self.s['integer']<=self.current_pc<self.s['integer']+72 or self.s['floating']<=self.current_pc<self.s['floating']+100
  if op in(55,63):
   self.own_instruction=True
   try:
    p=u32(self.r[rs]+half(w));assert p%8==0
    if op==55:self.r[rt]=self.get(p,8)
    else:self.put(p,self.r[rt],8)
   finally:self.own_instruction=False
  elif op==0 and fn in(56,58,60,62,63):
   value=self.r[rt]&((1<<64)-1)
   if fn in(56,60):value<<=sh+(32 if fn==60 else 0)
   elif fn in(58,62):value>>=sh+(32 if fn==62 else 0)
   else:value=(value if value<1<<63 else value-(1<<64))>>(sh+32)
   self.r[rd]=value&((1<<64)-1)
  elif island and op==0 and fn in(37,38):self.r[rd]=(self.r[rs]|self.r[rt])if fn==37 else(self.r[rs]^self.r[rt])
  else:
   before=self.r[:]
   if op==0 and fn==27:self.r[rs]=u32(self.r[rs]);self.r[rt]=u32(self.r[rt])
   super().execute(w)
   if island:
    dest=rt if op in(9,12,13,15,35)else rd if op==0 else None
    for i,v in enumerate(before):
     if i!=dest and v>0xFFFFFFFF:self.r[i]=v
  self.r[0]=0
 def mapped(self,p,pc):
  if not self.raw or not self.target_entry<=pc<self.target_entry+240:return p
  frame=self.home-40
  if p==frame+0x23:return frame+0x27
  if p==frame+0x18:return frame+0x1C
  return p
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace_pcs.append(self.current_pc)
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  own=getattr(self,'own_instruction',False)
  if getattr(self,'recording',False):
   if own:self.trace_pcs.append(self.current_pc)
   dest=self.mapped(p,self.current_pc)if own else p
   for j in range(n):
    if dest+j in self.private_projection:self.private_projection[dest+j]=(v>>(8*(n-j-1)))&255
  if own and self.current_pc==self.target_entry+0x50:self.flag_live=True
  if own and self.current_pc==self.target_entry+0x44:self.pointer_live=True
 def record_call(self,t):
  assert t in(self.s['integer'],self.s['floating']),hex(t);self.calls.append((t,()))
 def hook(self,t):
  ordinal=1 if t==self.s['integer']else 2;effect(self.memory,self.c,self.s,ordinal,self.home)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(self.c.rng if ordinal==1 else 0xABCD)
  if ordinal==2:self.f[0]=self.c.random

def state(m):
 memory=dict(m.memory);trace=list(m.trace)
 assert len(trace)==len(m.trace_pcs)
 if m.raw:
  trace=[(op,m.mapped(p,pc),n,v)for (op,p,n,v),pc in zip(trace,m.trace_pcs)]
  memory.update(m.private_projection)
 return memory,m.r,m.f,trace,m.calls,m.hi,m.lo,m.current_pc,m.delay_of,m.all_accesses

def programs(output,target,layout):
 E,rom,prefix=TARGETS[target];entry=E+layout*0x1000000;row=json.loads((output/'private-layout-v3.json').read_text())['layouts'][layout]
 s={k:row[k]for k in('clock','integer','floating')};original=(output/('%s-%d-original.elf'%(prefix,layout))).read_bytes();raw=(output/('%s-%d-raw.elf'%(prefix,layout))).read_bytes()
 a=elf_slot_offset(original,entry,240);b=elf_slot_offset(raw,entry,240);truth=list(struct.unpack_from('>60I',original,a));candidate=list(struct.unpack_from('>60I',raw,b));normalized=candidate[:]
 for offset,old,new in((0x44,0xAFA30018,0xAFA3001C),(0x54,0x8FA30018,0x8FA3001C),(0x90,0x8FA30018,0x8FA3001C),(0x50,0xA3A60023,0xA3A60027),(0x5C,0x83A60023,0x83A60027),(0x98,0x83A60023,0x83A60027)):
  assert normalized[offset//4]==old;normalized[offset//4]=new
 assert normalized==truth
 return entry,s,(truth,normalized,candidate)

def qualify(root,output):
 count=skipped=0;seen=[set(),set()];corpus=cases()
 for target in range(2):
  for layout in range(3):
   entry,s,roots=programs(output,target,layout)
   for c in corpus:
    initial=fixture(c,s)
    try:expected,calls,result=reference(initial,c,s)
    except DomainBoundary:skipped+=1;continue
    models=[]
    for i,words in enumerate(roots):
     m=Oracle(words,initial,c,s,entry,raw=i==2).run();assert(public(m.memory,c),m.calls,u32(m.r[2]))==(expected,calls,result),(target,layout,c,m.calls,calls)
     models.append(m);count+=1;seen[target].update(v-(entry-TARGETS[target][0])for v in m.visits)
    assert state(models[0])==state(models[1])==state(models[2]),(target,layout,c,'state')
 for target in range(2):assert set(range(TARGETS[target][0],TARGETS[target][0]+240,4))-seen[target]=={TARGETS[target][0]+0x80}
 prefixes=zero=0
 for target in range(2):
  entry,s,roots=programs(output,target,0)
  for c in(Case(),Case(notification=0,remaining=99,ticks=0),Case(notification=255,phase=8,mutation=3),Case(mutation=12,phase=8)):
   initial=fixture(c,s);full=Oracle(roots[0],initial,c,s,entry).run()
   for cut in range(full.all_accesses):
    models=[]
    for i,words in enumerate(roots):
     m=Oracle(words,initial,c,s,entry,raw=i==2);m.cut=cut
     try:m.run()
     except AccessBoundary:pass
     else:raise AssertionError('Access prefix did not fire')
     models.append(m)
    assert state(models[0])==state(models[1])==state(models[2]),(target,c,cut);prefixes+=1
  for rng,phase in itertools.product((0,0x80000000,0xFFFFFFFF),(0,8)):
   c=Case(rng=rng,phase=phase,mutation=0);initial=fixture(c,s);put(initial,address(c,s)+0xC8,-1,2);models=[]
   for i,words in enumerate(roots):
    m=Oracle(words,initial,c,s,entry,raw=i==2)
    try:m.run()
    except ZeroDivisor:pass
    else:raise AssertionError('Zero-divisor boundary not reached')
    assert m.current_pc==entry+0x6C and m.calls==[(s['integer'],())];models.append(m)
   assert state(models[0])==state(models[1])==state(models[2]);zero+=1
 return dict(success=True,private_only=True,matching_credit=0,targets=2,layouts_each=3,corpus=len(corpus),cases=count//3,executions=count,excluded_float_cast_cases=skipped,covered_words_each=59,zero_break_offset=0x80,access_prefix_triples=prefixes,zero_divisor_preinstruction_triples=zero,no_hardware_divide_zero_HILO_or_FCSR_claim=True,full_modeled_state_after_private_byte_home_mapping=True,ordinary_private_frame_domain=True,guest_clock_aliases_and_incoming_home_mutations=True)

def helpers(root,output):
 rom=(root/'conker/conker.us.bin').read_bytes();image=(root/'conker/build/conker.us.elf').read_bytes();code={}
 for entry,off,n in((INTEGER,0xDAED0,18),(FLOAT,0xDAF18,25)):
  original=rom[off:off+n*4];at=elf_slot_offset(image,entry,n*4);assert image[at:at+n*4]==original;code.update(zip(range(entry,entry+n*4,4),struct.unpack('>%dI'%n,original)))
 at=elf_slot_offset(image,FACTOR,4);retail_factor=rom[FACTOR-0x80082B20+0x2275E0:FACTOR-0x80082B20+0x2275E0+4];assert image[at:at+4]==retail_factor==struct.pack('>I',0x37800080)
 count=0;seen=set()
 for target in range(2):
  entry,s,roots=programs(output,target,0)
  for seed,remaining,ticks,notification,phase in itertools.product((0,1,0xFFFFFFFFFFFFFFFF,0x8000000000000000,0x123456789ABCDEF0,0xFEDCBA9876543210),(-1,0,32767),(0,1,0xFFFFFFFF),(0,255),(0,8)):
   c=Case(remaining=remaining,ticks=ticks,notification=notification,phase=phase,seed=seed);initial=fixture(c,s);expected,calls,result=reference(initial,c,s,True);models=[]
   for i,words in enumerate(roots):
    m=Oracle(words,initial,c,s,entry,raw=i==2,connected=code).run();assert(public(m.memory,c),m.calls,u32(m.r[2]))==(expected,calls,result),(target,c,m.calls,calls);models.append(m);seen.update(m.visits);count+=1
   assert state(models[0])==state(models[1])==state(models[2])
 assert set(code)<=seen
 return dict(success=True,cases=count//3,executions=count,integer_words=18,float_words=25,all43_helper_words_executed=True,shared64bit_seed_reference=True,retained_helpers_equal_original=True,no_rng_mocks_in_connected_cases=True)
