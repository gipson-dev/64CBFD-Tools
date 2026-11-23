"""Independent finite ring model and opaque mutation-capable o32 providers."""
from dataclasses import dataclass,replace
from pathlib import Path
import json,math,struct,sys
from tools.experiments import game_actor_effect_update_15196748_match as p
r=p.ROOT;o=p.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
ENTRY=0x15196748;OWNER=0x30000;PAYLOAD=0x80000;ALT_PAYLOAD=0x81000;RECORDS=0x50000;ALT_RECORDS=0x60000;MARK=0x70000
SPAWN=0x15198110;SOUND=0x15198C90;NOP=0x15198D7C;TICKS=(0x15198570,0x1519897C,0x151987CC);RELEASE=0x1516972C
u32=lambda v:v&0xffffffff
s8=lambda v:((v&255)^128)-128
s16=lambda v:((v&65535)^32768)-32768
float_value=lambda bits:struct.unpack('>f',struct.pack('>I',bits))[0]
def bits(value):
 try:return struct.unpack('>I',struct.pack('>f',value))[0]
 except OverflowError:return 0xFF800000 if value<0 else 0x7F800000
def fmul(a,b):return bits(float_value(a)*float_value(b))
def fadd(a,b):return bits(float_value(a)+float_value(b))
@dataclass(frozen=True)
class Case:
 seed:int=0
 cap:int=4
 head:int=0
 tail:int=3
 count:int=3
 flags:int=6
 tick:int=1
 dt:int=0x3f000000
 sound:int=0
 nop:int=0
 tick_callback:int=0
 tick_result:int=1
 mutations:int=0
 forward:int=3
 reverse:int=3
 phase:int=0
 real:int=-1
 stable:int=0
def cases():
 for seed in range(512):
  cap=(1,2,4,7)[seed%4]
  yield Case(seed=seed,cap=cap,head=(seed//5)%cap,tail=(seed//3)%cap,count=(0,1,2,cap)[seed//8%4],flags=(seed//4)%8,tick=(0,1,3,-1,-2,100,0x7fffffff,0x80000000)[seed//32%8],dt=(0,0x80000000,0x3f000000,0x3f800000,0xbf000000)[seed%5],sound=seed//7%2-1,nop=seed//9%2-1,tick_callback=seed//11%4-1,tick_result=seed//13%2,mutations=(0,1,2,4,8,16,32,3,20,10,63)[seed%11],forward=(0,1,2,255)[seed//2%4],reverse=(0,1,3,255)[seed//6%4],phase=(seed%2)*8,stable=int(seed%5==0))
 for preset in range(7):
  for cap in(2,4,7):
   for head in(0,cap-1):
    for result in(0,1):yield Case(seed=600+preset*20+cap*2+head,cap=cap,head=head,tail=(head+cap-1)%cap,count=cap-1,tick_result=result,real=preset,stable=result)
 for cap in(31,127):
  for flags in(0,2,4,6):yield Case(seed=900+flags,cap=cap,head=cap-2,tail=cap-1,count=2,flags=flags,forward=1,reverse=1,stable=1)
def fixture(c):
 m={STACK+i:(i*17+c.seed*11+0xa5)&255 for i in range(-1024,512)}
 for base,size in((OWNER,0xa0),(PAYLOAD,0x90),(ALT_PAYLOAD,0x90),(RECORDS,c.cap*36+16),(ALT_RECORDS,c.cap*36+16),(MARK,16)):
  assert base+size<=STACK-1024 or base>=STACK+512
  m.update({base+i:(i*19+c.seed*13+0x51)&255 for i in range(size)})
 put(m,OWNER+0x94,RECORDS);put(m,OWNER+0x98,PAYLOAD);m[OWNER+0x25]=c.cap;m[OWNER+0x2c]=c.count&255;m[OWNER+0x2d]=c.head;m[OWNER+0x2e]=c.tail;m[OWNER+0x2f]=2;m[OWNER+0x30]=0;put(m,OWNER+0x1e,0,2)
 for k,base in enumerate((PAYLOAD,ALT_PAYLOAD)):
  put(m,base,OWNER);m[base+6]=c.flags;m[base+0x52]=(c.seed*7+k*3)&255;m[base+0x6a]=255 if c.seed%2 else 10;put(m,base+0x40,bits((c.seed%5-2)*0.125));put(m,base+0x58,bits((c.seed%7-3)*0.25));m[base+0x64]=c.sound&255;m[base+0x68]=c.nop&255;m[base+0x61]=c.tick_callback&255;put(m,base+0x66,0x2345,2)
  if k:m[base+0x61]=((c.tick_callback+2)%4-1)&255
  for at,v in((0x8c,c.forward),(0x8d,(c.seed*19+35)&255),(0x8e,c.reverse),(0x8f,(c.seed*23+129)&255)):m[base+at]=v
 for base in(RECORDS,ALT_RECORDS):
  for index in range(c.cap):
   at=base+36*index
   for axis in range(3):put(m,at+4*axis,bits((c.seed%11+index*3+axis-5)*0.25+(100.0 if base==ALT_RECORDS else 0.0)));put(m,at+12+4*axis,bits((c.seed%7+index+axis-4)*0.125))
   put(m,at+24,bits((index+1)*0.5));put(m,at+28,32767 if c.stable else(-32768,-1,0,1,3,20,32767)[(c.seed+index*3)%7],2);m[at+30]=127 if c.stable else(-128,-1,0,1,127)[(c.seed+index)%5]&255;m[at+33]=(c.seed//17+index)%2
 put(m,S['D_800BE9E4'],c.tick);put(m,S['D_800BE9A4'],c.dt);put(m,MARK,0);put(m,MARK+4,0)
 for name,targets in(('D_8008F894',(SOUND,)),('D_8008F89C',(NOP,)),('D_8008F880',TICKS)):
  for i,target in enumerate(targets):put(m,S[name]+i*4,target)
 if c.real>=0:
  rom=(r/'conker/conker.us.bin').read_bytes();p=rom[0x24D260+c.real*96:0x24D260+(c.real+1)*96]
  for dst,src,n in((0x40,4,4),(0x52,0x31,1),(0x6a,0x47,1),(0x58,0x34,4),(0x64,0x40,1),(0x68,0x42,1),(0x61,0x3d,1),(0x8c,0x5c,4)):
   for i in range(n):m[PAYLOAD+dst+i]=p[src+i]
  m[PAYLOAD+6]=2
 return m
def service(m,c,target,args,home):
 put(m,MARK,u32(read(m,MARK)*33+(1 if target==SPAWN else 2 if target==SOUND else 3 if target==NOP else 4+TICKS.index(target))))
 if target==SPAWN:
  index=args[1];assert args==(OWNER,index)and 0<=index<c.cap;at=RECORDS+index*36;put(m,MARK+4,read(m,MARK+4)+1)
  if c.mutations&1:put(m,at+28,(index+3)*5,2);put(m,PAYLOAD+0x58,0x3e800000)
  if c.mutations&2:put(m,OWNER+0x94,ALT_RECORDS);put(m,OWNER+0x98,ALT_PAYLOAD)
  if c.mutations&32:
   m[OWNER+0x2d]=index;m[OWNER+0x2c]=1;put(m,S['D_800BE9A4'],0xbf000000);put(m,S['D_800BE9E4'],3)
  if c.mutations&128:put(m,home,0xDEADC0DE)
 elif target==SOUND:
  assert args==(OWNER,)
  if c.mutations&4:m[PAYLOAD+0x68]=0;m[PAYLOAD+0x61]=2;put(m,RECORDS+c.head*36,0x41200000)
 elif target==NOP:
  assert args==(OWNER,)
  if c.mutations&8:m[OWNER+0x2d]=c.cap-1;m[OWNER+0x2c]=1;m[PAYLOAD+0x61]=1
 else:
  assert target in TICKS and args==(OWNER,)
  if c.mutations&16:m[OWNER+0x2d]=c.cap-1;m[OWNER+0x2c]=0 if c.seed%2 else 1
  return c.tick_result
 return 0xDEADBEEF
def reference(initial,c,home=None):
 m=initial.copy();calls=[];home=STACK+c.phase if home is None else home;p=read(m,OWNER+0x98);records=read(m,OWNER+0x94)
 def call(t,a):calls.append((t,a));return service(m,c,t,a,home)
 if s8(m[OWNER+0x2c])<2 and m[p+6]&1:return m,calls,0
 index=s8(m[OWNER+0x2e]);iterations=0
 while index!=s8(m[OWNER+0x2d]):
  index-=1
  if index<0:index=m[OWNER+0x25]-1
  at=records+36*index;v=read(m,at+16);put(m,at+16,fadd(v,fmul(read(m,p+0x40),read(m,S['D_800BE9A4']))))
  for axis in range(3):put(m,at+axis*4,fadd(read(m,at+axis*4),fmul(read(m,at+12+axis*4),read(m,S['D_800BE9A4']))))
  m[at+31]=255
  if s8(m[at+30])>0:m[at+30]=(s8(m[at+30])-read(m,S['D_800BE9E4']))&255
  else:put(m,at+28,read(m,at+28,2)-m[p+0x52]*read(m,S['D_800BE9E4']),2)
  if s16(read(m,at+28,2))<m[p+0x6a]and m[at+33]==0:call(SPAWN,(OWNER,index))
  put(m,at+24,fadd(read(m,at+24),fmul(read(m,p+0x58),read(m,S['D_800BE9A4']))))
  if s16(read(m,at+28,2))<0:
   m[p+6]&=253;drop=0
   while index!=s8(m[OWNER+0x2d]):
    m[OWNER+0x2d]=(s8(m[OWNER+0x2d])+1)&255
    if s8(m[OWNER+0x2d])==m[OWNER+0x25]:m[OWNER+0x2d]=0
    m[OWNER+0x2c]=(s8(m[OWNER+0x2c])-1)&255;drop+=1;assert drop<=c.cap
   put(m,records+s8(m[OWNER+0x2d])*36+28,0,2)
  iterations+=1;assert iterations<=c.cap
 index=s8(m[OWNER+0x2d])
 if m[p+6]&2:
  mark=0;remaining=m[p+0x8c];n=0
  while True:
   m[records+36*index+31]=mark;remaining=s16(remaining-1);index+=1;mark=(mark+m[p+0x8d])&255
   if index==m[OWNER+0x25]:index=0
   n+=1;assert n<=c.cap
   if remaining==0 or index==s8(m[OWNER+0x2e]):break
 if m[p+6]&4:
  index=s8(m[OWNER+0x2e])-1
  if index<0:index=m[OWNER+0x25]-1
  mark=0;remaining=m[p+0x8e];n=0
  while True:
   at=records+index*36;remaining=s16(remaining-1);index-=1;m[at+31]=(m[at+31]*mark)>>8;mark=(mark+m[p+0x8f])&255
   if index<0:index=m[OWNER+0x25]-1
   n+=1;assert n<=c.cap
   if remaining==0 or index==s8(m[OWNER+0x2e]):break
 selector=s8(m[p+0x64])
 if selector!=-1:call(read(m,S['D_8008F894']+selector*4),(OWNER,))
 selector=s8(m[p+0x68])
 if selector!=-1:call(read(m,S['D_8008F89C']+selector*4),(OWNER,))
 selector=s8(m[p+0x61])
 if selector!=-1 and call(read(m,S['D_8008F880']+selector*4),(OWNER,))==0:return m,calls,0
 if s8(m[OWNER+0x2c])>0:
  at=records+36*s8(m[OWNER+0x2d])
  for axis in range(3):put(m,OWNER+0x54+axis*4,read(m,at+axis*4))
 else:
  for axis in range(3):put(m,OWNER+0x54+axis*4,0)
 return m,calls,1
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None,arguments=None):
  self.c=c;self.guest_home=STACK+c.phase;super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=(OWNER,)if arguments is None else arguments)
 def record_call(self,target):
  count=2 if target==SPAWN else 1;assert target in(SPAWN,SOUND,NOP,ENTRY,RELEASE,*TICKS),hex(target);a=tuple(map(u32,self.arguments(count)));self.calls.append((target,a));self.events.append(('CALL',target,a))
  if target==ENTRY:self.guest_home=self.r[29]
 def hook(self,target):
  if target==RELEASE:assert self.calls[-1][1]==(OWNER,);put(self.memory,MARK+8,0x13579BDF);value=0xDEADBEEF
  else:value=service(self.memory,self.c,target,self.calls[-1][1],self.guest_home)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-56<=a<STACK+c.phase}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,getattr(m,'dispatched_word',None))
def streams():
 from tools.tests.game_actor_effect_update_15196748_normalizer import normalize
 raw=payload(o/'selected-final/candidate.o','func_15196748');programs={k:bound_blob(*v,S)for k,v in dict(raw=raw,normalized=normalize(*raw),retail=payload(o/'original-target.o','func_15196748')).items()};padded=o/'qualified-owner/generated_1C2C60.c.o'
 if padded.exists():programs['padded']=bound_blob(*payload(padded,'func_15196748'),S)
 assert len({tuple(v)for k,v in programs.items()if k!='raw'})==1;return programs
def main():
 programs=streams();assert struct.pack('>257I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x1C3BF8:0x1C3FFC];visits=set();count=0
 for c in cases():
  initial=fixture(c);expected,calls,value=reference(initial,c);models=[]
  for label,words in programs.items():
   m=Oracle(words,initial,c);m.run();actual=public(m.memory,c);want=public(expected,c);assert actual==want,(label,c,[(hex(a),want.get(a),actual.get(a))for a in want.keys()|actual.keys()if want.get(a)!=actual.get(a)][:12]);assert m.calls==calls,(label,c,'calls',m.calls,calls);assert m.r[2]==value,(label,c,'return');models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);assert models[0].memory==models[1].memory,(c,'raw private bytes');visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=list(programs),independent_public_memory_return_and_exact_calls_equal=True,raw_private_bytes_equal=True,normalized_complete_state_equal=True,real_preset_cases=84,unexecuted_retail_words=[i for i in range(257)if ENTRY+4*i not in visits],source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def faults():
 programs={k:v for k,v in streams().items()if k!='raw'};count=0
 examples=[Case(count=1,flags=1),Case(cap=2,head=0,tail=1,count=1,flags=6,mutations=0,stable=1,forward=0,reverse=0),Case(cap=2,head=0,tail=1,count=1,flags=6,mutations=63),Case(cap=2,head=1,tail=0,count=1,flags=0,tick_result=0),Case(cap=2,head=0,tail=1,count=1,flags=2,mutations=128)]
 for c in examples:
  initial=fixture(c);m=Oracle(programs['retail'],initial,c);m.run()
  for cut in range(m.all_accesses):
   states=[]
   for words in programs.values():
    n=Oracle(words,initial,c);n.cut=cut
    try:n.run()
    except AccessBoundary:pass
    else:raise AssertionError('Own-access boundary did not fire')
    states.append(state(n))
   assert all(s==states[0]for s in states[1:]);count+=1
 q=dict(full_state_own_access_prefix_sets=count,streams=list(programs),dispatched_word_included=True,source_installed=p.installed(),matching_credit=0);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def aliases():
 tests=[]
 for offset in(-4,0,4):
  c=Case(seed=1300+offset,cap=1,head=0,tail=0,count=1,flags=0,sound=-1,nop=-1,tick_callback=-1);m=fixture(c);put(m,OWNER+0x94,OWNER+0x54+offset);tests.append((c,m))
 c=Case(seed=1301,cap=2,head=0,tail=1,count=1,flags=0,mutations=128);tests.append((c,fixture(c)));count=0
 for c,initial in tests:
  expected,calls,value=reference(initial,c);models=[]
  for label,words in streams().items():
   m=Oracle(words,initial,c);m.run();assert public(m.memory,c)==public(expected,c)and m.calls==calls and m.r[2]==value,(label,c,'guest-only alias');models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 q=dict(guest_only_alias_cases=count,coordinate_exact_and_partial_overlap=True,incoming_home_mutation=True,portable_native_alias_claim=False,source_installed=p.installed(),matching_credit=0);(o/'aliases.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();entry=0x15147740;end=0x151478D0;parent=list(struct.unpack_from('>100I',rom,0x174BF0));count=0
 for c in list(cases())[::8]:
  initial=fixture(c);put(initial,S['D_8008A200']+8,ENTRY);expected,calls,value=reference(initial,c,STACK+c.phase-32)
  if not value:put(expected,MARK+8,0x13579BDF)
  models=[]
  for label,child in streams().items():
   m=Oracle(parent,initial,c,entry=entry,connected=dict(zip(range(ENTRY,ENTRY+4*len(child),4),child)));m.r[31]=end;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Original caller did not return')
   actual={a:b for a,b in m.memory.items()if not STACK+c.phase-88<=a<STACK+c.phase+4};want={a:b for a,b in expected.items()if not STACK+c.phase-88<=a<STACK+c.phase+4};assert actual==want,(label,c,'parent memory');assert m.calls==[(ENTRY,(OWNER,))]+calls+([]if value else[(RELEASE,(OWNER,))]),(label,c,'parent calls');models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 q=dict(cases_per_stream=count,complete_original_parent_words=100,caller='func_15147740',dispatch='D_8008A200[2]',release_provider_bounded=True,source_installed=p.installed(),matching_credit=0);(o/'caller-window.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
