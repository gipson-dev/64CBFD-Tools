"""Original RNGs, emission wrapper, secondary factory and byte-copy execution.

Allocator, descriptor backend and initializer internals stay bounded providers;
their byte pins are distinct from the original instructions executed here.
"""
from dataclasses import replace
import hashlib,itertools,json,struct
from tools.experiments import game_dual_actor_emitter_150b37c8_match as p
from tools.tests import game_dual_actor_emitter_150b37c8_guest as g
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
SEED,FACTOR=0x800885b0,0x8009f740
ALLOCATE,COPY,CREATED,DEST=0x15147a80,0x10022ec0,0xb0000,0xa0000
BACKEND,INITIALIZE,FREE=0x1513c350,0x1513e2ac,0x1516972c

def original(entry,n,rom):
 at=entry-0x15000000+0x2d4b0 if entry>=0x15000000 else entry-0x10000000
 return list(struct.unpack_from('>'+str(n)+'I',rom,at))

def pin(entry,n,rom,elf):
 words=original(entry,n,rom);blob=struct.pack('>'+str(n)+'I',*words);at=p.elf_slot_offset(elf,entry,len(blob));assert elf[at:at+len(blob)]==blob
 return words,dict(entry=hex(entry),words=n,sha256=hashlib.sha256(blob).hexdigest(),matches_frozen_ELF=True)

def clobber(m,value):
 for i in range(4):m.put(m.r[29]+4*i,0xb5000000+i,4)
 for reg in(1,2,3,*range(4,16),24,25):m.r[reg]=0xa5000000+reg
 m.f[:20]=[0xa5000000+i for i in range(20)];m.hi,m.lo=0xa5000010,0xa5000011;m.r[2]=g.u32(value)

class RandomConnected(g.Oracle):
 def execute(self,w):
  op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  inside=g.RNG<=self.current_pc<g.RNG+72 or g.FRNG<=self.current_pc<g.FRNG+100
  if op in(55,63):
   prior=self.own_instruction;self.own_instruction=True
   try:
    at=g.u32(self.r[rs]+((w&65535)^32768)-32768);assert at%8==0
    if op==55:self.r[rt]=self.get(at,8)
    else:self.put(at,self.r[rt],8)
   finally:self.own_instruction=prior
  elif op==0 and fn in(56,58,60,62,63):
   value=self.r[rt]&((1<<64)-1)
   if fn in(56,60):value<<=sh+(32 if fn==60 else 0)
   elif fn in(58,62):value>>=sh+(32 if fn==62 else 0)
   else:value=(value if value<1<<63 else value-(1<<64))>>(sh+32)
   self.r[rd]=value&((1<<64)-1)
  elif op==0 and fn in(37,38)and inside:self.r[rd]=(self.r[rs]|self.r[rt])if fn==37 else(self.r[rs]^self.r[rt])
  elif op==0 and fn==27:
   left,right=self.r[rs]&0xffffffff,self.r[rt]&0xffffffff;assert right;self.lo,self.hi=left//right,left%right
  elif op==17 and rs==20 and fn==32:
   value=self.f[rd];assert 0<=value<=65535;self.f[sh]=g.bits(float(value));self.fcsr&=~0x3f000
  else:
   before=self.r[:];super().execute(w)
   if inside:
    dest=rt if op in(9,12,13,15,35)else rd if op==0 else None
    for i,value in enumerate(before):
     if i!=dest and value>0xffffffff:self.r[i]=value
  self.r[0]=0
 def record_call(self,t):
  super().record_call(t)
  if t in(g.RNG,g.FRNG):
   self.seeds.append(g.read(self.memory,SEED,8));g.put(self.memory,g.MARK,g.read(self.memory,g.MARK)+1)

def randoms(rom,elf):
 code={};pins=[]
 for entry,n in[(g.RNG,18),(g.FRNG,25)]:
  words,row=pin(entry,n,rom,elf);code.update(zip(range(entry,entry+4*n,4),words));pins.append(row)
 at=p.elf_slot_offset(elf,FACTOR,4);assert elf[at:at+4]==bytes.fromhex('37800080')
 old=g.effect;cases=0;visits=set()
 def effect(memory,c,t,count,args):
  value=old(memory,c,t,count,args)
  if t in(g.RNG,g.FRNG):g.put(memory,SEED,next_seed(g.read(memory,SEED,8)),8)
  return value
 g.effect=effect
 try:
  programs=[*g.streams(),g.bound_blob(*g.payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION),g.symbols())]
  for seed,rm,phase,outcome in itertools.product(SEEDS,range(4),(0,8),(0,1)):
   value=seed;floats=[];integers=[];flags=[];seeds=[]
   for t in(g.FRNG,g.RNG,g.RNG,g.RNG,g.RNG,g.FRNG):
    seeds.append(value);value=next_seed(value)
    if t==g.RNG:integers.append(value&0xffffffff)
    else:
     draw,status=g.arithmetic(g.bits(float(value&65535)),0x37800080,2,rm);floats.append(draw);flags.append(status)
   c=g.Case(rng=tuple(integers),samples=tuple(floats),provider_float_flags=tuple(flags),phase=phase,fcsr=rm,outcome=outcome);baseline=None
   for words in programs:
    m=RandomConnected(words,c,connected=code);m.seeds=[];g.put(m.memory,SEED,seed,8);g.put(m.memory,FACTOR,0x37800080);m.initial=dict(m.memory);m.run();expected,calls,obs,fcsr=g.reference(m.initial,c)
    assert m.calls==calls and m.observations==obs,(seed,rm,'connected boundaries')
    assert g.public(m.memory,c)==g.public(expected,c)and g.packet_snapshots(m.memory,c)==g.packet_snapshots(expected,c),(seed,rm,'connected memory')
    assert m.fcsr==fcsr and m.seeds==seeds and g.read(m.memory,SEED,8)==value,(seed,rm,'connected FCSR/seed')
    assert m.r[2]==1 and m.r[29]==g.home(c)and m.r[16:24]==m.before[16:24]and m.f[20:]==m.before_f[20:]
    state=(m.calls,m.observations,g.public(m.memory,c),m.fcsr)
    if baseline is None:baseline=state
    else:assert state==baseline
    visits.update(m.visits)
   cases+=1
 finally:g.effect=old
 assert all(entry+4*i in visits for entry,n in[(g.RNG,18),(g.FRNG,25)]for i in range(n))
 return dict(original_rng_pins=pins,original_rng_cases_per_stream=cases,rng_streams=5,original_rng_words_executed=43,seed_transitions_per_case=6,four_integer_and_two_float_draws=True,all_four_rounding_modes=True,independent_seed_and_finite_FP_reference=True,submission_and_factory_contracted_in_RNG_gate=True)

class Capture(g.Oracle):
 def hook(self,t):
  if t==g.SUBMIT:self.submit_input=(dict(self.memory),self.calls[-1][1])
  if t==g.FACTORY:self.factory_input=(dict(self.memory),self.calls[-1][1])
  super().hook(t)

class Factory(g.FactoryOracle):
 def __init__(self,words,copy,c,memory,args):
  self.c=c;self.input_args=args;self.allocations=[];self.copies=[]
  super().__init__(words,memory,c,entry=g.FACTORY,arguments=args,connected=dict(zip(range(COPY,COPY+44,4),copy)))
  self.r[29]=self.before[29]=self.target_home=g.home(c)-248
  for i,v in enumerate(args[4:],4):g.put(self.memory,self.target_home+4*i,v)
  self.before_f=self.f[:]
 def record_call(self,t):
  assert t in(ALLOCATE,COPY),hex(t);a=tuple(map(g.u32,self.arguments(11 if t==ALLOCATE else 3)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==ALLOCATE:self.allocations.append(a)
  else:self.copies.append(a)
 def hook(self,t):
  assert t==ALLOCATE;args=self.input_args
  assert self.allocations[-1]==(args[0],72,20,1,0,1,0,0,0,args[13],args[14])
  assert g.read(self.memory,args[0]+16)==1;g.put(self.memory,g.MARK,g.read(self.memory,g.MARK)+1);clobber(self,CREATED if self.c.outcome else 0)

class Wrapper(g.FactoryOracle):
 def __init__(self,words,c,memory,args,allocated,initialized):
  self.c=c;self.input_args=args;self.allocated=allocated;self.initialized=initialized;self.forwarded=[]
  super().__init__(words,memory,c,entry=g.SUBMIT,arguments=args)
  self.r[29]=self.before[29]=self.target_home=g.home(c)-248
  for i,v in enumerate(args[4:],4):g.put(self.memory,self.target_home+4*i,v)
  self.before_f=self.f[:]
 def record_call(self,t):
  assert t in(BACKEND,INITIALIZE,FREE),hex(t);a=tuple(map(g.u32,self.arguments({BACKEND:11,INITIALIZE:9,FREE:1}[t])));self.calls.append((t,a));self.events.append(('CALL',t,a));self.forwarded.append((t,a))
 def hook(self,t):
  a=self.input_args;got=self.forwarded[-1][1]
  if t==BACKEND:
   assert got==(a[0],0,a[1]&255,a[2]&255,a[10]&255,0,0,0,a[11],a[12]&255,a[13]);value=CREATED if self.allocated else 0
  elif t==INITIALIZE:
   assert got==(CREATED,0,*a[3:9],a[9]&255);value=self.initialized
  else:assert got==(CREATED,);value=0x12345678
  clobber(self,value)

def emission(rom,elf):
 factory,pf=pin(g.FACTORY,70,rom,elf);copy,pc=pin(COPY,11,rom,elf);wrapper,pw=pin(g.SUBMIT,50,rom,elf)
 pins=[pf,pc,pw,*[pin(a,n,rom,elf)[1]for a,n in[(BACKEND,103),(INITIALIZE,271)]]]
 cases=wrapper_cases=copy_cases=0;fv=set();cv=set();wv=set();copy40_visits=set()
 for phase,outcome,mode,index in itertools.product((0,8),(0,1),(0,15),(-128,127)):
  c=g.Case(phase=phase,outcome=outcome,mode=mode,index=index);capture=Capture(g.streams()[0],c).run();memory,args=capture.factory_input;initial=dict(memory);q,d,*_=args;render=args[11]
  for address,n in[(CREATED,256),(DEST,128)]:initial.update({address+i:(i*23+0x65)&255 for i in range(n)})
  g.put(initial,CREATED+0x98,DEST);g.put(initial,q+16,0);wanted=dict(initial);g.put(wanted,q+16,1);g.put(wanted,g.MARK,g.read(wanted,g.MARK)+1)
  if outcome:
   for i,v in enumerate(g.data(initial,d,32)):wanted[DEST+i]=v
   for i,v in enumerate(args[3:9]):g.put(wanted,DEST+32+i,v,1)
   for i,v in enumerate(g.data(initial,render,32)):wanted[DEST+40+i]=v
  m=Factory(factory,copy,c,initial,args).run();assert g.public(m.memory,c)==g.public(wanted,c);assert g.packet_snapshots(m.memory,c)==g.packet_snapshots(wanted,c)
  assert m.r[2]==(CREATED if outcome else 0)and m.r[29]==g.home(c)-248 and m.r[16:24]==m.before[16:24]and m.f[20:]==m.before_f[20:]
  assert m.copies==([(DEST,d,32)]if outcome else[]);fv.update(pc for pc in m.visits if g.FACTORY<=pc<g.FACTORY+280);cv.update(pc for pc in m.visits if COPY<=pc<COPY+44);cases+=1
  memory,a=capture.submit_input
  for allocated,initialized in itertools.product((0,1),(0,1)):
   m=Wrapper(wrapper,c,memory,a,allocated,initialized).run();assert m.r[2]==(CREATED if allocated and initialized else 0)
   assert m.r[29]==g.home(c)-248 and m.r[16:24]==m.before[16:24]and m.f[20:]==m.before_f[20:]
   assert [t for t,_ in m.forwarded]==[BACKEND]+([INITIALIZE]+([FREE]if not initialized else[])if allocated else[])
   wv.update(m.visits);wrapper_cases+=1
  # The backend's descriptor copy is 40 bytes. Execute the original memcpy
  # independently, including every seeded unspecified byte; do not shrink it.
  initial=dict(memory);initial.update({DEST+i:0xa5 for i in range(64)})
  m=g.FactoryOracle(copy,initial,c,entry=COPY,arguments=(DEST,a[0],40)).run()
  assert g.data(m.memory,DEST,40)==g.data(initial,a[0],40)and g.data(m.memory,DEST+40,24)==bytes([0xa5])*24 and m.r[2]==DEST
  copy40_visits.update(m.visits);copy_cases+=1
 assert fv==set(range(g.FACTORY,g.FACTORY+280,4))and cv==set(range(COPY,COPY+44,4))
 assert all(g.SUBMIT+4*i in wv for i in range(50))and copy40_visits==set(range(COPY,COPY+44,4))
 return dict(original_emission_helper_pins=pins,original_secondary_factory_cases=cases,original_secondary_factory_words_executed=70,original_memcpy_words_executed=11,secondary_copy_bytes=64,secondary_guest_unspecified_bytes_copied=10,original_wrapper_cases=wrapper_cases,original_wrapper_words_executed=50,original_descriptor_copy_cases=copy_cases,first_descriptor_copy_bytes=40,first_guest_unspecified_bytes_copied=15,allocator_backend_and_initializer_internals_contracted=True,backend_and_initializer_byte_pins_only=True)

def main():
 p.prepare();rom=(p.ROOT/'conker/conker.us.bin').read_bytes();elf=(p.OUT/'baseline/conker/build/conker.us.elf').read_bytes()
 q=dict(**randoms(rom,elf),**emission(rom,elf),source_installed=p.installed(),helper_matching_credit=0,matching_credit=0)
 (p.OUT/'helpers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
