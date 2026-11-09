"""Resolver state-machine contract with bounded allocator, DMA, decoder and free."""
import itertools,json,re,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_resource_resolver_1510d0ec_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.pad_generated_object import parse_object
ENTRY=0x1510D0EC;OFFSET=0x1510D374;ALLOC=0x10003C6C;DMA=0x10004514;DECODE=0x10006240;FREE=0x10004074
OUTPUT,TEMP,EXPANDED=0x50000,0x60000,0x70000
NAMES=('D_800D9F58','D_800D9F5C','D_80091D20','D_800B87A0','D_800B0E58','D_800BC448','D_800D9F68','D_800DBDBA','D_8003809C','func_1510D374','func_10003C6C','func_10004514','func_10006240','func_10004074')
SYMS={n:int(n.split('_')[1],16)for n in NAMES};SYMS['D_1A37E0']=0x1A37E0
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:(u32(v)^0x80000000)-0x80000000
byte=lambda v:((v&255)^128)-128
@dataclass(frozen=True)
class Case:
 identity:int=1
 size:int=17
 expanded_size:int=64
 cache:int=0xFFFFFFFF
 priority:int=63
 prior:int=0
 activity:int=0
 retain:int=1
 output:int=1
 failure:int=0
 effects:int=0
 source:int=0x1A37E1
 decoder:int=0
 minimum:int=7762
 maximum:int=-1
 phase:int=0
def positions(c,s=SYMS):return(s['D_80091D20']+c.identity*2,s['D_800B87A0']+c.identity*2,s['D_800B0E58']+c.identity*4,s['D_800BC448']+c.identity,s['D_800D9F68']+c.identity)
def output(c,s=SYMS):
 _,expanded,cache,priority,activity=positions(c,s)
 return(0,OUTPUT,cache,priority,activity,STACK+c.phase+8,expanded,s['D_800D9F58'])[c.output]
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def fixture(c,s=SYMS,prefix=False):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base in(OUTPUT,TEMP,EXPANDED):m.update({base+i:(i*29+0x59)&255 for i in range(-16,144)})
 put(m,s['D_800D9F58'],c.minimum);put(m,s['D_800D9F5C'],c.maximum);put(m,s['D_8003809C'],0x1234);m[s['D_800DBDBA']]=0xA5
 if 0<=c.identity<7762:
  a,b,d,e,f=positions(c,s)
  for p,n in((a,2),(b,4),(d,4),(e,4),(f,4)):m.update({p+i:0x5A for i in range(n)})
  put(m,a,c.size,2);put(m,b,c.expanded_size,2);put(m,d,c.cache);m[e]=c.prior&255;m[f]=c.activity
  if prefix:
   for i in range(c.identity):put(m,s['D_80091D20']+i*2,(i*7+1)&65535,2)
 return m
def effects(m,c,s,stage):
 a,b,d,e,f=positions(c,s)
 if stage=='offset'and c.effects&1:put(m,a,7,2)
 if stage=='first'and c.effects&2:put(m,b,96,2)
 if stage=='dma'and c.effects&4:put(m,b,112,2);put(m,s['D_8003809C'],0x5678)
 if stage=='second'and c.effects&8:put(m,s['D_8003809C'],0x9ABC)
 if stage=='decode'and c.effects&16:put(m,b,128,2);m[f]=200
 if stage=='free'and c.effects&32:
  put(m,b,256,2)
  if output(c,s):put(m,output(c,s),0xBAD)
 if c.effects&64:put(m,STACK+c.phase+8,127);put(m,STACK+c.phase+12,0)
def observe(m,c,s):
 if not 0<=c.identity<7762:return()
 a,b,d,e,f=positions(c,s);p=output(c,s)
 return(read(m,a,2),read(m,b,2),read(m,d),m[e],m[f],read(m,s['D_8003809C']),read(m,p)if p else None)
def reference(initial,c,s=SYMS,connected=False):
 m=dict(initial);calls=[];observations=[];home=STACK+c.phase
 for i,v in enumerate((output(c,s),c.priority,c.retain),1):put(m,home+4*i,v)
 put(m,s['D_800D9F58'],min(signed(read(m,s['D_800D9F58'])),signed(c.identity)));put(m,s['D_800D9F5C'],max(signed(read(m,s['D_800D9F5C'])),signed(c.identity)))
 def call(target,args,stage):
  calls.append((target,tuple(map(u32,args))));observations.append(observe(m,c,s))
  if not(connected and stage=='offset'):effects(m,c,s,stage)
 if not 0<=c.identity<7762:return m,calls,0x80000000,observations
 a,b,cache,priority,activity=positions(c,s);size=read(m,a,2)
 if not size:put(m,cache,0x80000000)
 elif read(m,cache)==0xFFFFFFFF:
  m[s['D_800DBDBA']]=5
  if read(m,home+8)==63:put(m,home+8,62)
  if connected:source=u32(s['D_1A37E0']+sum(read(m,s['D_80091D20']+i*2,2)for i in range(c.identity)))
  else:source=c.source
  call(s['func_1510D374'],(c.identity,),'offset');skip=source&1;source=u32(source-skip);amount=(size+skip+1)&~1;amount=(amount+15)&~15
  call(s['func_10003C6C'],(amount,1,2,1,2),'first')
  if c.failure==1:return m,calls,0x80000000,observations
  call(s['func_10004514'],(source,TEMP,amount,1),'dma');put(m,TEMP,0x444D4121)
  call(s['func_10003C6C'],(read(m,b,2),1,1,0,2),'second')
  if c.failure==2:
   call(s['func_10004074'],(TEMP,),'free');return m,calls,0x80000000,observations
  call(s['func_10006240'],(TEMP+skip,EXPANDED,read(m,s['D_8003809C'])),'decode');put(m,EXPANDED,0x44454321)
  call(s['func_10004074'],(TEMP,),'free');put(m,cache,EXPANDED);m[activity]=0
 if output(c,s):put(m,output(c,s),read(m,b,2))
 result=read(m,cache);p=signed(read(m,home+8))
 if byte(m[priority])<p:m[priority]=p&255
 if read(m,home+12)and m[activity]<255:m[activity]+=1
 return m,calls,result,observations
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=tuple(map(u32,(c.identity,output(c,s),c.priority,c.retain))));self.before=self.r[:];self.before_f=self.f[:];self.allocations=0;self.observations=[]
 def record_call(self,t):
  counts={self.syms['func_1510D374']:1,self.syms['func_10003C6C']:5,self.syms['func_10004514']:4,self.syms['func_10006240']:3,self.syms['func_10004074']:1,ENTRY:4};assert t in counts,hex(t)
  a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t!=ENTRY:self.observations.append(observe(self.memory,self.case,self.syms))
 def hook(self,t):
  c,s,a=self.case,self.syms,self.calls[-1][1]
  if t==s['func_1510D374']:stage='offset';value=u32(c.source)
  elif t==s['func_10003C6C']:
   self.allocations+=1;stage='first'if self.allocations==1 else'second';value=0 if c.failure==self.allocations else TEMP if self.allocations==1 else EXPANDED
  elif t==s['func_10004514']:stage='dma';value=0xFFFFFFFF
  elif t==s['func_10006240']:stage='decode';value=u32(c.decoder)
  else:assert t==s['func_10004074'];stage='free';value=0xDEADBEEF
  effects(self.memory,c,s,stage)
  if stage=='dma':put(self.memory,TEMP,0x444D4121)
  if stage=='decode':put(self.memory,EXPANDED,0x44454321)
  for i in range(5):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value;self.hi,self.lo=0xA5000010,0xA5000011
def words(path,s=SYMS):
 t,fs,rs=parse_object(path);f=fs['func_1510D0EC'];return bound_blob(t[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']},s)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.observations,m.events,m.trace,m.current_pc,m.delay_of,m.dispatched_word)
def check(m,initial,c,s=SYMS,connected=False):
 want,calls,result,observations=reference(initial,c,s,connected);assert(public(m.memory),m.calls,m.r[2],m.observations)==(public(want),calls,result,observations),c
 if output(c,s):assert read(m.memory,output(c,s))==read(want,output(c,s)),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[31]==m.before[31]and m.f[20:]==m.before_f[20:]
def cases():
 for identity,minimum,maximum in itertools.product((-1,-2147483648,7762,2147483647),(7762,0),(-1,7761)):yield Case(identity=identity,minimum=minimum,maximum=maximum)
 for i in range(256):yield Case(cache=(0,0x80000000,0x81234567)[i%3],prior=i,priority=(-129,-128,-1,0,62,63,127,128,255)[i%9],retain=(0,1,0xFFFFFFFF,0x80000000)[i%4],activity=i,output=i%3,phase=(i%2)*8)
 for size,odd,failure,priority,effect in itertools.product((1,2,15,16,17,31,32,33,65535),(0,1),range(3),(3,63),(0,63)):
  yield Case(size=size,source=0x1A37E0+odd,failure=failure,priority=priority,effects=effect,decoder=(0,-1,64)[size%3])
 for identity,size,cache,activity,retain in itertools.product((0,1,7761),(0,17),(0x80000000,0x81234567),(254,255),(0,-1)):
  yield Case(identity=identity,size=size,cache=cache,activity=activity,retain=retain)
 for output_kind,cache,failure,effect in itertools.product(range(2,8),(0x81234567,0xFFFFFFFF),range(3),(0,127)):
  yield Case(identity=0,output=output_kind,cache=cache,failure=failure,effects=effect,source=0x1A37E0)
def main():
 names=('retail-reference.o','qualified-padded.o','qualified-owner.o','predecessor-owner.o');ps=[words(out/n)for n in names];assert ps[0]==ps[1];visited=set();count=0
 for c in cases():
  initial=fixture(c);pair=[]
  for ws in ps:m=Oracle(ws,initial,c).run();check(m,initial,c);pair.append(m)
  assert state(pair[0])==state(pair[1]);visited.update(pair[0].visits);count+=1
 assert len(visited)==162,len(visited)
 cuts=delays=0
 for c in(Case(identity=-1),Case(size=0),Case(cache=0x81234567,activity=255),Case(effects=127),Case(failure=2,effects=63)):
  initial=fixture(c);full=Oracle(ps[0],initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for ws in ps[:2]:
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access boundary')
    except AccessBoundary:pass
    pair.append(m)
   assert state(pair[0])==state(pair[1]);cuts+=1;delays+=pair[0].delay_of is not None
 rebases=0
 for j in range(6):
  s={k:v+j*(0x20000 if k.startswith('func_')else 0x108000)for k,v in SYMS.items()};entry=ENTRY+j*0x10000;qs=[words(out/n,s)for n in names];assert qs[0]==qs[1]
  for c in(Case(),Case(size=0),Case(cache=0x80000000),Case(failure=1),Case(failure=2,effects=31),Case(effects=63,output=2)):
   initial=fixture(c,s)
   for ws in qs:m=Oracle(ws,initial,c,entry,s).run();check(m,initial,c,s)
   rebases+=1
 asm=(root/'conker/asm/139FC0.s').read_text();a=asm.index('glabel func_1510D374\n');b=asm.index('endlabel func_1510D374',a);rr=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',asm[a:b]);rom=(root/'conker/conker.us.bin').read_bytes();truth=rom[int(rr[0][0],16):int(rr[0][0],16)+4*len(rr)];elf=(out/'frozen/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,OFFSET,len(truth));assert elf[at:at+len(truth)]==truth
 code=dict(zip(range(OFFSET,OFFSET+len(truth),4),struct.unpack('>%dI'%len(rr),truth)));connected=0
 for c in(Case(identity=identity,size=size,failure=failure,effects=effect)for identity,size,failure,effect in itertools.product((0,1,2,31),(1,17),range(3),(0,63))):
  initial=fixture(c,prefix=True);pair=[]
  for ws in ps:m=Oracle(ws,initial,c,connected=code).run();check(m,initial,c,connected=True);pair.append(m)
  assert state(pair[0])==state(pair[1]);connected+=1
 report=dict(cases_per_body=count,executions=count*4,retail_and_normalized_words=162,old_semantic_words=155,covered_words=162,fault_prefix_pairs=cuts,delay_slot_faults=delays,rebase_layouts=6,rebase_cases=rebases,connected_prefix_words=len(rr),connected_prefix_cases=connected,all_allocator_failure_paths=True,provider_mutations_and_out_aliases=True,guest_incoming_home_cases_separate=True,all_four_public_contracts_equal=True,normalized_literal_state_equal=True,SDK_services_bounded=True,hardware_and_decompressor_claimed=False)
 (out/'guest-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
