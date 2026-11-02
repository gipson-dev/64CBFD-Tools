"""Complete factory/spawn-wrapper/memcpy execution including all 56 copied bytes."""
from pathlib import Path
from dataclasses import replace
import itertools,json,struct
from tools.tests import game_point_effect_payload_oracle as old
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY,ALLOC,COPY,CHILD=0x15152520,0x15157010,0x10022EC0,0x90000
symbols=dict(entry=old.ENTRY,point=old.POINT,factory=old.FACTORY,symbols={'D_800A%04X'%(0x81C0+4*i):0x800A81C0+4*i for i in range(9)})
connected={}
def configure(root,output):
 global connected
 rom=(root/'conker/conker.us.bin').read_bytes();image=(root/'conker/build/conker.us.elf').read_bytes();connected={}
 for entry,offset,n in((old.SPAWN,0x184D48,32),(COPY,0x22EC0,11)):
  raw=rom[offset:offset+4*n];at=elf_slot_offset(image,entry,len(raw));assert image[at:at+len(raw)]==raw
  connected.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,raw)))
 return connected

def fixture(c,empty=False):
 memory=old.fixture(c,symbols);_,_,packets=old.reference(memory,c,symbols);packet=bytearray(packets[0][1])
 packet[0x68:0x70]=bytes(((i*37+c.seed*23+1)&255)for i in range(8))
 if empty:packet[:8]=bytes(8)
 memory.update({old.STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-4096,2048)})
 for i,b in enumerate(packet):memory[c.owner+i]=b
 for i in range(16*512):memory[CHILD+i]=(i*37+c.seed*7+91)&255
 return memory,bytes(packet)

def live_packet(packet,c):
 data=bytearray(packet)
 if c.mutation&16:
  updates=((0,1,4),(4,1,4),(0x30,-7,2),(0x18,-12,2),(0x1C,old.bits(3.5),4),(0x24,old.bits(99.),4),(0x5C,old.bits(2.),4),(0x3C,0x87654321,4),(0x70,packet[0x70]^0x40,1),(0x71,packet[0x71]^0x80,1))
  for at,v,n in updates:
   for i in range(n):data[at+i]=(v>>((n-i-1)*8))&255
 return bytes(data)

def expected(initial,packet,c,input_address=None,factory_home=None):
 input_address=c.owner if input_address is None else input_address
 factory_home=old.STACK+c.phase if factory_home is None else factory_home
 original_packet=packet;packet=live_packet(packet,c)
 point_calls=[(old.FACTORY,(input_address,c.mode&255,old.U32(c.extra)))];q=replace(c,phase=factory_home-old.STACK+152)
 memory,calls,spawns=old.factory_reference(initial,q,symbols,point_calls,[(input_address,packet)])
 calls=calls[1:];full=[];outcalls=[];copies=[];flags=packet[0x70]|2;property_byte=packet[0x71]
 home=factory_home;state=home-256+0x70
 padding=bytearray(initial[state+i]for i in(49,50,51));descriptor_overrides={}
 flags=original_packet[0x70]|2;property_byte=original_packet[0x71]
 if c.mutation&16:
  for i,b in enumerate(packet):memory[input_address+i]=b
 count=0
 for t,args in calls:
  outcalls.append((t,args))
  if t!=old.SPAWN:continue
  count+=1;_,desc,vector=spawns[count-1];desc=bytearray(desc);desc[0]=flags
  vector=vector[:44]+original_packet[0x24:0x28]
  for i,b in descriptor_overrides.items():desc[i]=b
  tail=bytes((property_byte,))+bytes(padding)+bytes(desc[:4]);full.append((args,bytes(desc),vector+tail))
  allocation=(args[0],args[2],args[3],args[4],args[5],args[6]+56,args[7],args[8]);outcalls.append((ALLOC,allocation))
  if c.mutation&1:flags^=0x20
  if c.mutation&2:property_byte^=0x55
  if c.mutation&8:
   padding[:]=bytes((0xD1,0xD2,0xD3));descriptor_overrides[5]=0xEF
  copied=vector+bytes((property_byte,))+bytes(padding)+bytes((flags,))+bytes(desc[1:4])
  old.put(memory,old.MARK+4*(count-1),count)
  if count%3!=c.seed%3:
   child=CHILD+(count-1)*512;outcalls.append((COPY,(child+0x120,state,56)));copies.append((child+0x120,copied))
   for i,b in enumerate(copied):memory[child+0x120+i]=b
 return memory,outcalls,full,copies

class Machine(old.Oracle):
 def __init__(self,words,memory,c,raw=False,entry=ENTRY,extra_code=None):
  self.raw=raw;self.copy_snapshots=[];self.allocations=0;self.input=c.owner;self.point_home=old.STACK+c.phase;self.real_point=bool(extra_code and old.POINT in extra_code)
  super().__init__(words,memory,c,symbols,entry,connected=dict(connected,**{})|dict(extra_code or {}),target=ENTRY)
  self.connected_point=False
 def execute(self,w):
  if self.real_point and not self.point_done and self.current_pc==old.ENTRY+60:
   old.effect(self.memory,self.c,symbols,self.point_home-120,home=self.point_home);self.point_done=True
  op,rs,fn=w>>26,w>>21&31,w&63
  if op==17 and rs==16 and fn in(0,2):
   import math
   assert math.isfinite(old.floating(self.f[w>>11&31]))and math.isfinite(old.floating(self.f[w>>16&31]))
   super().execute(w);assert math.isfinite(old.floating(self.f[w>>6&31]));return
  return super().execute(w)
 def record_call(self,t):
  counts={ENTRY:3,old.POINT:3,old.INTEGER:0,old.FLOAT:0,old.VECTOR:4,old.SPAWN:9,ALLOC:8,COPY:3};assert t in counts,hex(t)
  args=tuple(old.U32(v)for v in self.arguments(counts[t]));self.calls.append((t,args))
  if t==ENTRY:self.input=args[0];self.home=self.r[29]
  if t==old.SPAWN:self.spawns.append((args,old.data(self.memory,args[0],88),old.data(self.memory,args[1],56)))
  if t==COPY:self.copy_snapshots.append((args[0],old.data(self.memory,args[1],args[2])))
 def hook(self,t):
  if t==old.INTEGER and self.rng_i==0 and self.c.mutation&16:
   current=old.data(self.memory,self.input,120);updated=live_packet(current,self.c)
   for i,b in enumerate(updated):self.memory[self.input+i]=b
  if t!=ALLOC:return super().hook(t)
  c=self.c;self.allocations+=1;a=self.calls[-1][1];descriptor=a[0];state=self.spawns[-1][0][1]
  if c.mutation&1:self.memory[descriptor]^=0x20
  if c.mutation&2:self.memory[state+48]^=0x55
  if c.mutation&8:
   self.memory.update({state+49:0xD1,state+50:0xD2,state+51:0xD3,descriptor+5:0xEF})
  old.put(self.memory,old.MARK+4*(self.allocations-1),self.allocations)
  value=CHILD+(self.allocations-1)*512 if self.allocations%3!=c.seed%3 else 0
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def canonical_call(row,raw,c):
 t,a=row;a=list(a)
 positions={old.VECTOR:(3,),old.SPAWN:(0,1),ALLOC:(0,),COPY:(1,)}.get(t,())
 if raw:
  for i in positions:a[i]-=4
 return t,tuple(a)

def programs(output):
 words=[]
 for label in('original','C','raw'):
  image=(output/('layout-0-'+label+'.elf')).read_bytes();at=elf_slot_offset(image,ENTRY,852);words.append(struct.unpack_from('>213I',image,at))
 assert words[0]==words[1];return words

def state(m):return m.memory,m.r,m.f,m.trace,m.calls,m.spawns,m.copy_snapshots,m.hi,m.lo,m.current_pc,m.delay_of,m.all_accesses,m.allocations,m.rng_i,m.rng_f

def seed_raw(initial,home):
 m=dict(initial);base=home-144
 for i in range(140):m[base+4+i]=initial[base+i]
 return m

def projected_trace(m,raw,home):
 if not raw:return m.trace
 start=home-140
 def pointer(v):return v-4 if start<=v<start+140 else v
 return[(kind,pointer(address),n,pointer(value)if n==4 else value)for kind,address,n,value in m.trace]

def compare(models,c,wanted,calls,spawns,copies,home=None):
 home=old.STACK+c.phase if home is None else home
 for index,m in enumerate(models):
  raw=index==2
  assert old.public(m.memory,c)==old.public(wanted,c),(c,'external')
  assert [canonical_call(v,raw,c)for v in m.calls]==calls,(c,'calls')
  snapshots=[(canonical_call((old.SPAWN,a),raw,c)[1],d,v)for a,d,v in m.spawns]
  assert snapshots==spawns,(c,'spawn snapshots')
  assert m.copy_snapshots==copies,(c,'all56 bytes')
  assert m.r[29]==old.STACK+c.phase
 assert state(models[0])==state(models[1])
 assert projected_trace(models[0],False,home)==projected_trace(models[2],True,home),(c,'translated access trace')
 assert models[0].r[16:24]==models[2].r[16:24]and models[0].r[28:32]==models[2].r[28:32]and models[0].f[20:]==models[2].f[20:]

def qualify(root,output):
 configure(root,output);words=programs(output);count=copies_seen=spawn_seen=0;seen=set();outcomes=set()
 for seed,mutation,phase,empty in itertools.product(range(4),(0,1,2,3,8,11,16,17,18,19,24,27),(0,8),(False,True)):
  c=old.Case(seed=seed,mutation=mutation,phase=phase,mode=(0,255,0x80000000,0xFFFFFFFF)[seed],extra=(0,1,0x80000000,0xFFFFFFFF)[seed],pattern=0)
  initial,packet=fixture(c,empty);wanted,calls,spawns,copies=expected(initial,packet,c);models=[]
  for index,code in enumerate(words):models.append(Machine(code,seed_raw(initial,old.STACK+phase)if index==2 else initial,c,raw=index==2).run())
  compare(models,c,wanted,calls,spawns,copies)
  for m in models:seen.update(m.visits)
  copies_seen+=len(copies);spawn_seen+=len(spawns);outcomes.add(bool(copies));count+=1
 rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>213I',rom,0x17F9D0);traps={ENTRY+4*i for i,w in enumerate(retail)if w&0xFC00003F==13}
 assert len(traps)==4 and set(range(ENTRY,ENTRY+852,4))-traps<=seen and not(traps&seen)
 assert set(connected)<=seen and outcomes=={False,True}
 prefixes=0
 for seed,mutation,empty,phase in((0,0,True,0),(0,0,False,0),(1,0,False,0),(0,11,False,8)):
  c=old.Case(seed=seed,mutation=mutation,phase=phase,pattern=0);initial,packet=fixture(c,empty)
  if not empty:
   packet=bytes.fromhex('0000000100000000')+packet[8:]
   for i,b in enumerate(packet):initial[c.owner+i]=b
  full=Machine(words[0],initial,c).run()
  for cut in range(full.all_accesses):
   models=[]
   for index,code in enumerate(words):
    m=Machine(code,seed_raw(initial,old.STACK+phase)if index==2 else initial,c,raw=index==2);m.cut=cut
    try:m.run()
    except old.faults.AccessBoundary:pass
    else:raise AssertionError('Access prefix did not fire')
    models.append(m)
   assert state(models[0])==state(models[1])
   assert projected_trace(models[0],False,old.STACK+phase)==projected_trace(models[2],True,old.STACK+phase)
   prefixes+=1
 report=dict(success=True,cases=count,executions=count*3,root_words=213,covered_nontrap_root_words=209,unreachable_divisor_traps=4,spawn_snapshots=spawn_seen,complete56byte_copies=copies_seen,real_wrapper_words=32,real_memcpy_words=11,all43_wrapper_copy_words_executed=True,access_prefix_triples=prefixes,raw_scratch_correspondence_shift=4,raw_original_normalized_outputs_calls_complete_packets_saved_roles_and_translated_traces_equal=True,original_normalized_complete_state_equal=True,live_input_after_first_RNG_and_cached_prefix_fields=True,finite_FP_operands_and_intermediates_enforced=True,native_uninitialized_padding_not_claimed=True)
 (output/'private-guest-v18.json').write_text(json.dumps(report,indent=2)+'\n');return report
