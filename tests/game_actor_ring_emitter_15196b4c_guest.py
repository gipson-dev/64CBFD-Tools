"""Independent emitter semantics, live providers and complete raw/retail execution."""
from pathlib import Path
from dataclasses import dataclass,replace
from collections import Counter
import json,struct,sys
from tools.experiments import game_actor_ring_emitter_15196b4c_match as p
r=p.ROOT;o=p.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
ENTRY=0x15196b4c;OWNER=0x30000;P=0x80000;ALT_P=0x81000;RECORDS=0x50000;ALT_RECORDS=0x60000;MARK=0x70000;ACTOR=0x90000;ALT_ACTOR=0x91000;MATRIX=0xa0000;ALT_MATRIX=0xb0000;WORLD=STACK-20
SCALE=(0x15197a0c,0x15197a68,0x15197ab4);TRANSFORM=0x15143134;FIRST=0x15198d88;SECOND=0x151990ac;RNG=0x150ada20
u32=lambda n:n&0xffffffff
s8=lambda n:((n&255)^128)-128
floating=lambda b:struct.unpack('>f',struct.pack('>I',b))[0]
def bits(f):
 try:return struct.unpack('>I',struct.pack('>f',f))[0]
 except OverflowError:return 0xff800000 if f<0 else 0x7f800000
def f(a,b,k):return fp(a,b,k,'left')
@dataclass(frozen=True)
class Case:
 seed:int=0;cap:int=4;head:int=0;tail:int=3;count:int=3;gate:int=0;selector:int=0;index:int=1
 phase:int=0x40200000;rate:int=0x3f000000;dt:int=0x3f000000;mutations:int=0;real:int=-1;rule:str='left'
def cases():
 for seed in range(512):
  cap=(1,2,4,7)[seed%4]
  yield Case(seed=seed,cap=cap,head=(seed//7)%cap,tail=(seed//3)%cap,count=(seed//5)%cap,gate=int(seed%19==0),selector=seed//3%4-1,index=(0,1,3,255)[seed//13%4],phase=(0,0x3f800000,0x3f800001,0x3fa00000,0x40200000,0x40b00000,0xbf800000)[seed//11%7],rate=(0,0x3e000000,0x3f800000,0x40000000,0xbf800000)[seed%5],dt=(0,0x80000000,0x3f000000,0x3f800000,0xbf000000)[seed//5%5],mutations=(0,1,2,4,8,16,32,3,20,10,63)[seed%11])
 for preset in range(7):
  for cap in(2,7):
   for head in(0,cap-1):
    for mutation in(0,16,63):yield Case(seed=600+preset*20+head,cap=cap,head=head,tail=(head+cap-1)%cap,count=cap-1,mutations=mutation,real=preset)
 for cap in(31,127):
  for mutation in(0,4,16,63):yield Case(seed=900+mutation,cap=cap,head=cap-2,tail=cap-1,count=cap-1,mutations=mutation)
def fixture(c):
 m={STACK+i:(i*17+c.seed*11+0xa5)&255 for i in range(-1024,512)}
 for base,size in((OWNER,160),(P,144),(ALT_P,144),(RECORDS,36*c.cap+16),(ALT_RECORDS,36*c.cap+16),(MARK,32),(ACTOR,0x200),(ALT_ACTOR,0x200)):
  assert base+size<=STACK-1024 or base>=STACK+512;m.update({base+i:(i*19+c.seed*13+0x51)&255 for i in range(size)})
 for base in(MATRIX,ALT_MATRIX):
  for index in range(256):
   for axis in range(3):put(m,base+64*index+4*axis,bits((index+axis+c.seed%7)*0.125+(10 if base==ALT_MATRIX else 0)))
 put(m,OWNER+0x94,RECORDS);put(m,OWNER+0x98,P);m[OWNER+0x25]=c.cap;m[OWNER+0x2c]=c.count;m[OWNER+0x2d]=c.head;m[OWNER+0x2e]=c.tail;m[OWNER+0x2f]=0;m[OWNER+0x30]=2;put(m,OWNER+0x1e,0,2)
 put(m,ACTOR+0x1d4,0 if c.gate else MATRIX);put(m,ALT_ACTOR+0x1d4,ALT_MATRIX)
 for base in(P,ALT_P):
  put(m,base,ACTOR);m[base+5]=c.index;m[base+7]=c.selector&255
  for start in(8,20,32,44):
   for axis in range(3):put(m,base+start+axis*4,bits((c.seed%11+axis-start/4)*0.25+(100 if base==ALT_P else 0)))
  for at,v in((0x38,bits(0.75)),(0x3c,bits((c.seed%5-2)*0.125)),(0x40,bits((c.seed%7-3)*0.25)),(0x44,bits(1.25)),(0x48,c.rate),(0x4c,c.phase),(0x58,bits((c.seed%3-1)*0.25)),(0x5c,bits(2.0)),(0x78,bits((c.seed%5)*0.5)),(0x7c,bits((c.seed%3)*0.5)),(0x84,bits((c.seed%7)*0.25)),(0x88,bits((c.seed%5)*0.25))):put(m,base+at,v)
  m[base+0x50]=(c.seed*37+250)&255;m[base+0x53]=(c.seed*19+129)&255;m[base+0x54]=(c.seed*29+129)&255
 for base in(RECORDS,ALT_RECORDS):
  for index in range(c.cap):
   for at in range(0,28,4):put(m,base+36*index+at,bits((index+at/4+c.seed%9)*0.125+(100 if base==ALT_RECORDS else 0)))
 for i,target in enumerate(SCALE):put(m,S['D_8008F870']+4*i,target)
 put(m,S['D_800BE9A4'],c.dt)
 for i in range(0,32,4):put(m,MARK+i,0)
 if c.real>=0:
  preset=(r/'conker/conker.us.bin').read_bytes()[0x24d260+c.real*96:0x24d260+(c.real+1)*96]
  for dst,src,n in((8,0x18,12),(20,0x24,12),(0x40,4,4),(0x48,8,4),(0x53,0x32,1),(0x54,0x33,1),(0x58,0x34,4),(0x5c,0x38,4),(0x78,0x50,4),(0x84,0x58,4)):
   for i in range(n):m[P+dst+i]=preset[src+i]
  # Keep the caller's matrix/table selections valid; phase is a bounded input.
 return m
def service(m,c,target,args,counts):
 ordinal=counts[target];counts[target]+=1;role=SCALE.index(target)+1 if target in SCALE else 4 if target==TRANSFORM else 5 if target==FIRST else 6 if target==SECOND else 7
 put(m,MARK,u32(read(m,MARK)*33+role));put(m,MARK+4,read(m,MARK+4)+1)
 if target in SCALE:
  assert args==(OWNER,)
  if c.mutations&1:put(m,P,ALT_ACTOR);m[P+5]=255;put(m,S['D_800BE9A4'],bits(0.75))
  return bits((c.seed%9-4)*0.25)
 if target==TRANSFORM:
  source,output,matrix=args;assert source==P+(8 if ordinal==0 else 20);assert output==(OWNER+16 if ordinal==0 else WORLD)
  values=[f(read(m,source+4*i),read(m,matrix+4*i),'add')for i in range(3)]
  for i,v in enumerate(values):put(m,output+4*i,v)
  if ordinal==0 and c.mutations&2:
   put(m,OWNER+0x94,ALT_RECORDS);put(m,OWNER+0x98,ALT_P);put(m,read(m,P)+0x1d4,ALT_MATRIX);put(m,P+20,bits(7.0));m[P+5]^=1
  return 0
 if target in(FIRST,SECOND):
  assert args==(OWNER,WORLD)
  if c.mutations&4:
   put(m,WORLD,bits(2.0+ordinal));m[P+0x53]=(211+ordinal)&255;m[P+0x54]=(133+ordinal)&255;put(m,P+0x40,bits(-0.5));put(m,OWNER+0x94,ALT_RECORDS);put(m,OWNER+0x98,ALT_P)
  if c.mutations&8 and ordinal==0:
   if target==FIRST:put(m,P+0x88,bits(2.0));put(m,P+0x84,bits(0.25))
   else:m[OWNER+0x2e]=(c.tail+1)%c.cap;m[OWNER+0x2d]=(c.head+1)%c.cap;m[OWNER+0x2c]=c.cap-1
  return 0
 assert target==RNG and args==()
 if c.mutations&16:m[P+0x50]=(27+ordinal*39)&255;put(m,P+0x40,bits(0.25*(ordinal+1)));m[OWNER+0x2e]=(c.tail+ordinal+1)%c.cap;m[OWNER+0x2d]=(c.head+ordinal)%c.cap;m[OWNER+0x2c]=c.cap-1
 if c.mutations&32 and ordinal==0:put(m,P+0x4c,bits(0.5));put(m,S['D_800BE9A4'],bits(-0.5))
 return (0,5,6,0x7fffffff,0x80000000,0xffffffff)[(c.seed+ordinal)%6]
def reference(initial,c):
 m=initial.copy();calls=[];counts=Counter();p=read(m,OWNER+0x98);records=read(m,OWNER+0x94)
 def call(t,a):calls.append((t,a));return service(m,c,t,a,counts)
 matrix=read(m,read(m,p)+0x1d4)
 if not matrix:return m,calls,0
 selector=s8(m[p+7])
 if selector!=-1:put(m,p+0x44,call(read(m,S['D_8008F870']+4*selector),(OWNER,)));matrix=read(m,read(m,p)+0x1d4)
 matrix+=m[p+5]*64;call(TRANSFORM,(p+8,OWNER+16,matrix));call(TRANSFORM,(p+20,WORLD,matrix))
 put(m,p+0x4c,f(read(m,p+0x4c),f(read(m,p+0x48),read(m,S['D_800BE9A4']),'mul'),'add'));phase=read(m,p+0x4c)
 if floating(phase)>1.0:
  inverse=f(bits(1.0),phase,'div');point=[read(m,p+32+4*i)for i in range(3)];end=[read(m,p+44+4*i)for i in range(3)];elapsed=f(read(m,p+0x3c),read(m,S['D_800BE9A4']),'add');timeStep=f(elapsed,inverse,'mul');speed=read(m,p+0x38);size=f(read(m,p+0x5c),f(read(m,p+0x58),elapsed,'mul'),'add')
  pointStep=[f(f(read(m,OWNER+16+4*i),read(m,p+32+4*i),'sub'),inverse,'mul')for i in range(3)];endStep=[f(f(read(m,WORLD+4*i),read(m,p+44+4*i),'sub'),inverse,'mul')for i in range(3)];sizeStep=f(f(read(m,p+0x5c),size,'sub'),inverse,'mul');speedStep=f(f(read(m,p+0x44),speed,'sub'),inverse,'mul');iterations=0
  while True:
   put(m,p+0x7c,f(read(m,p+0x7c),read(m,p+0x78),'add'))
   if floating(read(m,p+0x7c))>1.0:call(FIRST,(OWNER,WORLD))
   put(m,p+0x88,f(read(m,p+0x88),read(m,p+0x84),'add'))
   if floating(read(m,p+0x88))>1.0:call(SECOND,(OWNER,WORLD))
   def at():return records+36*s8(m[OWNER+0x2e])
   m[at()+33]=0
   for i in range(3):put(m,at()+4*i,point[i])
   for i in range(3):put(m,at()+12+4*i,f(f(end[i],point[i],'sub'),speed,'mul'))
   put(m,at()+24,size);put(m,at()+28,m[p+0x53],2);m[at()+30]=m[p+0x54];m[at()+31]=255;m[at()+32]=m[p+0x50]
   random=call(RNG,());m[p+0x50]=(m[p+0x50]+random%6+3)&255
   put(m,at()+16,f(read(m,at()+16),f(read(m,p+0x40),elapsed,'mul'),'add'))
   for i in range(3):put(m,at()+4*i,f(read(m,at()+4*i),f(read(m,at()+12+4*i),elapsed,'mul'),'add'))
   elapsed=f(elapsed,timeStep,'sub');m[OWNER+0x2e]=(s8(m[OWNER+0x2e])+1)&255
   if m[OWNER+0x25]==s8(m[OWNER+0x2e]):m[OWNER+0x2e]=0
   head=s8(m[OWNER+0x2d]);m[OWNER+0x2c]=(s8(m[OWNER+0x2c])+1)&255
   if head==s8(m[OWNER+0x2e]):
    m[OWNER+0x2d]=(head+1)&255
    if m[OWNER+0x25]==s8(m[OWNER+0x2d]):m[OWNER+0x2d]=0
    m[OWNER+0x2c]=(s8(m[OWNER+0x2c])-1)&255
   point=[f(v,d,'add')for v,d in zip(point,pointStep)];end=[f(v,d,'add')for v,d in zip(end,endStep)];speed=f(speed,speedStep,'add');size=f(size,sizeStep,'add');put(m,p+0x4c,f(read(m,p+0x4c),bits(1.0),'sub'));iterations+=1;assert iterations<=32
   if not floating(read(m,p+0x4c))>1.0:break
  for i,v in enumerate(point):put(m,p+32+4*i,v)
  for i,v in enumerate(end):put(m,p+44+4*i,v)
  put(m,p+0x38,speed);put(m,p+0x3c,elapsed)
 return m,calls,1
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None):
  self.c=c;self.counts=Counter();self.fp_ops=[];super().__init__(words,initial.copy(),BaseCase(),entry=entry,s={},arguments=(OWNER,),connected=connected);self.initial_gpr=self.r[:];self.initial_fpr=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(0,1,2,3,60):
   fn=w&63;fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;x,y=self.f[fs],self.f[ft];self.fp_ops.append((fn,x,y))
   if fn==60:self.condition=floating(x)<floating(y)
   else:self.f[fd]=f(x,y,('add','sub','mul','div')[fn])
   return
  return super().execute(w)
 def record_call(self,target):
  n=1 if target in(*SCALE,ENTRY,0x1516972c)else 3 if target==TRANSFORM else 2 if target in(FIRST,SECOND)else 0;assert target in(*SCALE,TRANSFORM,FIRST,SECOND,RNG,ENTRY,0x1516972c),hex(target);a=tuple(map(u32,self.arguments(n)));self.calls.append((target,a));self.events.append(('CALL',target,a))
 def hook(self,target):
  if target==0x1516972c:assert self.calls[-1][1]==(OWNER,);put(self.memory,MARK+8,0x13579bdf);v=0xdeadbeef
  else:v=service(self.memory,self.c,target,self.calls[-1][1],self.counts)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(v)
  if target in SCALE:self.f[0]=v
def public(m):return{a:v for a,v in m.items()if not STACK-288<=a<STACK}
def programs():
 from tools.tests.game_actor_ring_emitter_15196b4c_normalizer import normalize
 raw,refs=payload(o/'selected-final/candidate.o','func_15196B4C');result=dict(raw=bound_blob(raw,refs,S),normalized=bound_blob(*normalize(raw,refs),S),retail=bound_blob(*payload(o/'original-target.o','func_15196B4C'),S))
 padded=o/'qualified-owner/generated_1C2C60.c.o'
 if padded.exists():result['padded']=bound_blob(*payload(padded,'func_15196B4C'),S)
 assert len({tuple(v)for k,v in result.items()if k!='raw'})==1
 assert struct.pack('>383I',*result['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x1c3ffc:0x1c45f8];return result
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,getattr(m,'dispatched_word',None))
def main():
 code=programs();count=0;visits=set()
 for c in cases():
  initial=fixture(c);expected,calls,value=reference(initial,c)
  models=[]
  for label,words in code.items():
   m=Oracle(words,initial,c);m.run();actual=public(m.memory);want=public(expected);assert actual==want,(label,c,[(hex(a),want.get(a),actual.get(a))for a in want.keys()|actual.keys()if want.get(a)!=actual.get(a)][:16]);assert m.calls==calls,(label,c,'calls',m.calls,calls);assert m.r[2]==value,(label,c,'return',m.r[2],value)
   assert all(m.r[i]==m.initial_gpr[i]for i in(*range(16,24),28,29,30,31)),(label,c,'saved GPR');assert m.f[20:]==m.initial_fpr[20:],(label,c,'saved FPR')
   if label=='retail':visits.update(m.visits)
   if label!='raw':models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]),(c,'normalized complete state')
  count+=1
 q=dict(cases_per_stream=count,streams=list(code),independent_public_memory_return_exact_calls_equal=True,saved_GPR_FPR_restored=True,normalized_complete_state_equal=True,unexecuted_retail_words=[i for i in range(383)if ENTRY+4*i not in visits],source_installed=p.installed(),matching_credit=0,limits='Bounded mutation-capable providers; no actual helper behavior, raw private/fault/FCSR or hardware acceptance claimed.');(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def aliases():
 count=0
 for offset in(-4,0,4):
  c=Case(seed=11,cap=1,head=0,tail=0,count=0,selector=-1,mutations=32);initial=fixture(c);put(initial,OWNER+0x94,P+0x20+offset);expected,calls,value=reference(initial,c)
  for label,words in programs().items():
   m=Oracle(words,initial,c);m.run();assert public(m.memory)==public(expected)and m.calls==calls and m.r[2]==value,(label,'payload/record overlap',offset)
  count+=1
 q=dict(guest_only_record_payload_overlap_cases=count,portable_native_alias_claim=False,source_installed=p.installed(),matching_credit=0);(o/'aliases.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def callers():
 global WORLD
 old=WORLD;WORLD=STACK-32-20;count=0
 try:
  rom=(r/'conker/conker.us.bin').read_bytes();entry=0x15147740;end=0x151478d0;parent=list(struct.unpack_from('>100I',rom,0x174bf0))
  for c in list(cases())[::16]:
   initial=fixture(c);put(initial,S['D_8008A23C']+8,ENTRY);expected,calls,value=reference(initial,c)
   if not value:put(expected,MARK+8,0x13579bdf)
   models=[]
   for label,words in programs().items():
    m=Oracle(parent,initial,c,entry=entry,connected=dict(zip(range(ENTRY,ENTRY+4*len(words),4),words)));m.r[31]=end;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Original caller did not return')
    filt=lambda d:{a:v for a,v in d.items()if not STACK-320<=a<STACK+4}
    assert filt(m.memory)==filt(expected),(label,c,'parent memory');assert m.calls==[(ENTRY,(OWNER,))]+calls+([]if value else[(0x1516972c,(OWNER,))]),(label,c,'parent calls',m.calls,calls)
    if label!='raw':models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);count+=1
 finally:WORLD=old
 q=dict(cases_per_stream=count,complete_original_parent_words=100,caller='func_15147740',dispatch='D_8008A23C[2]',release_provider_bounded=True,source_installed=p.installed(),matching_credit=0);(o/'caller-window.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def faults():
 streams={k:v for k,v in programs().items()if k!='raw'};count=0
 for c in(Case(gate=1),Case(phase=0),Case(seed=11,cap=2,tail=1,head=0,count=1,mutations=63)):
  initial=fixture(c);m=Oracle(streams['retail'],initial,c);m.run()
  for cut in range(m.all_accesses):
   states=[]
   for words in streams.values():
    n=Oracle(words,initial,c);n.cut=cut
    try:n.run()
    except AccessBoundary:pass
    else:raise AssertionError('Own-access boundary did not fire')
    states.append(state(n))
   assert all(v==states[0]for v in states[1:]);count+=1
 q=dict(full_state_own_access_prefix_sets=count,streams=list(streams),dispatched_word_included=True,raw_fault_prefix_claim=False,source_installed=p.installed(),matching_credit=0);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
