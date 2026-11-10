"""Independent state-dispatch model with actual connected recursive guest code."""
import itertools,json,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-state-dispatch-1506045C-match'
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x1506045C;QUERY=0x15080738;DISPATCH=0x15065A5C;FINAL=0x150642AC
ACTOR=0x30000;A=0x50000;B=0x51000;MARK=0x70000;CONTROL=0x71000
DISABLED=0x800C35EA;TICKS=0x800BE9E4;MODE=0x800BE9F0;CONTROL_PTR=0x800CC284;TABLE=0x800CBFA8
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
COUNTS={ENTRY:5,QUERY:1,DISPATCH:9,FINAL:5}
@dataclass(frozen=True)
class Case:
 command:int=5
 overlay:int=0
 fallback:int=0
 timer:int=0
 ticks:int=1
 mode:int=0
 controls:int=0
 query:int=0
 blocked:int=0
 force_command:int=0
 extra:int=0
 actor_force:int=0
 actor_busy:int=0
 identity:int=0
 category:int=0
 stunned:int=0
 buttons:int=0x12345678
 flags:int=0
 height:int=0x41234567
 secondary:int=0
 disabled:int=0
 mutation:int=0
 result:int=0x12345678
 phase:int=0
 seed:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2304)}
 for address,n in ((ACTOR,812),(A,512),(B,512),(MARK,32),(CONTROL,8)):
  m.update({address+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 put(m,ACTOR+0x31C,A);m[ACTOR+0x65]=c.identity&255;m[ACTOR+0x104]=c.stunned&255;m[ACTOR+0x137]=c.actor_busy&255;m[ACTOR+0x13C]=c.actor_force&255
 for s in (A,B):
  put(m,s+0x72,c.timer,2)
  for offset,value in ((0x75,c.command),(0x78,c.overlay),(0x7C,c.fallback),(0x17,c.force_command),(0x4E,c.blocked),(0x7B,c.extra)):m[s+offset]=value&255
 put(m,MARK,0);m[DISABLED]=c.disabled&255;put(m,TICKS,c.ticks);put(m,MODE,c.mode);put(m,CONTROL_PTR,CONTROL);put(m,CONTROL,c.controls,2)
 for i in range(256):m[TABLE+i*812]=c.category&255
 put(m,STACK+c.phase+16,c.secondary)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def provider(m,c,target,args):
 n=read(m,MARK)+1;put(m,MARK,n)
 if target==QUERY:
  if c.mutation&1:
   put(m,ACTOR+0x31C,B);m[B+0x75]=0x91;m[B+0x78]=0x2A;m[B+0x7C]=7
  if c.mutation&2:
   m[ACTOR+0x104]=1;m[ACTOR+0x137]=1;m[ACTOR+0x65]=1;put(m,MODE,0x2E)
  return u32(c.query)
 if target==DISPATCH:
  if c.mutation&4:
   s=B if read(m,ACTOR+0x31C)==A else A;put(m,ACTOR+0x31C,s);m[s+0x7B]=1
  if c.mutation&8:
   m[ACTOR+0x104]=1;s=read(m,ACTOR+0x31C);m[s+0x75]^=0x55;m[s+0x78]=0x8A
  return u32(c.result^n)
 assert target==FINAL
 if c.mutation&16:
  s=B if read(m,ACTOR+0x31C)==A else A;put(m,ACTOR+0x31C,s);m[s+0x75]^=0xAA;m[s+0x7C]=0x81
 return 0xDEADBEEF
def reference(initial,c):
 m=dict(initial);calls=[]
 def call(t,*args):
  args=tuple(map(u32,args));calls.append((t,args));return provider(m,c,t,args)
 def dispatch(buttons,flags,height,secondary,depth=0):
  assert depth<2
  result=0
  if m[DISABLED]==1:return
  force=stun=expired=0;s=read(m,ACTOR+0x31C);timer=read(m,s+0x72,2)
  if timer and secondary==0:
   delta=signed(read(m,TICKS))
   if delta<timer:put(m,s+0x72,timer-delta,2)
   else:put(m,s+0x72,0,2);expired=1
  s=read(m,ACTOR+0x31C);command=m[s+0x75]&~0x80
  if m[s+0x7C] and command==0:command=m[s+0x7C]
  if read(m,MODE)not in(0x29,0x2E)and not m[s+0x78]and read(m,read(m,CONTROL_PTR),2)&0x20:
   if call(QUERY,command):command=0x1A
  s=read(m,ACTOR+0x31C);overlay=m[s+0x78]
  if overlay in(0x1A,0x2A):command=overlay
  if m[ACTOR+0x13C]or m[ACTOR+0x137]:
   if secondary:force=1
   else:command=0
  identity=m[ACTOR+0x65]
  if identity and not secondary:
   category=m[TABLE+identity*812];command={12:8,35:27,138:27,40:0}.get(category,14)
  if m[s+0x17]:command=0x3C
  if secondary==0 and overlay and command!=(overlay&~0x80):
   saved=m[s+0x75];m[s+0x75]=overlay;calls.append((ENTRY,tuple(map(u32,(ACTOR,buttons,flags,height,1)))))
   dispatch(buttons,flags,height,1,depth+1);m[read(m,ACTOR+0x31C)+0x75]=saved;m[read(m,ACTOR+0x31C)+0x78]=0
  if m[ACTOR+0x104]:stun=1;buttons=flags=0
  s=read(m,ACTOR+0x31C)
  if command and not m[s+0x4E]:result=call(DISPATCH,ACTOR,buttons,flags,height,secondary,command,stun,expired,force)
  s=read(m,ACTOR+0x31C)
  if m[s+0x7B]or flags&0x4000:call(FINAL,ACTOR,flags,height,force,result)
 dispatch(u32(c.buttons),u32(c.flags),u32(c.height),u32(c.secondary))
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c):
  self.c=c;super().__init__(words,memory,c,entry=ENTRY,arguments=(ACTOR,u32(c.buttons),u32(c.flags),u32(c.height),u32(c.secondary)))
  self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  assert t in COUNTS,hex(t);args=tuple(map(u32,self.arguments(COUNTS[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  assert t!=ENTRY,'Recursion must execute real connected code'
  value=provider(self.memory,self.c,t,self.calls[-1][1])
  for i in range(max(4,COUNTS[t])):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value;self.hi,self.lo=0xA5000010,0xA5000011
def words(path):
 text,fs,rs=parse_object(path);a,n=fs['func_1506045C']['value'],fs['func_1506045C']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};s={name:int(name.split('_')[1],16)for vs in refs.values()for _,name in vs};return bound_blob(text[a:a+n],refs,s)
def cases():
 cs=[Case(command=command,secondary=secondary,controls=32,query=query)for command,secondary,query in itertools.product(range(256),(0,1),(0,1))]
 cs +=[Case(overlay=overlay,secondary=secondary,mutation=28)for overlay,secondary in itertools.product(range(256),(0,1))]
 for f,vs in {'timer':(0,1,2,65535),'ticks':(0,1,65534,65535,65536,0x7FFFFFFF,0x80000000,0xFFFFFFFF),'fallback':range(256),'mode':(0,40,41,42,45,46,47,0xFFFFFFFF),'controls':(0,16,32,48,65535),'query':(0,1,0x80000000,0xFFFFFFFF),'disabled':(0,1,2,255),'secondary':(0,1,2,0x80000000,0xFFFFFFFF),'height':(0,0x80000000,1,0x7F800000,0x7FC12345,0xFFFFFFFF),'flags':(0,0x4000,0x8000,0xFFFF,0x80000000,0xFFFFFFFF),'buttons':(0,0xFFFF,0x80000000,0xFFFFFFFF),'identity':range(256),'category':range(256),'blocked':(0,1,255),'force_command':(0,1,255),'extra':(0,1,255),'actor_force':(0,1,255),'actor_busy':(0,1,255),'stunned':(0,1,255)}.items():
  for v in vs:
   for secondary in(0,1):cs.append(replace(Case(command=0 if f=='fallback'else 5,timer=1,controls=32,identity=1 if f=='category'else 0,overlay=0x89 if f in('height','extra')else 0,secondary=secondary),**{f:v}))
 for bits in range(32):
  for overlay in(0,0x1A,0x2A,0x89):cs.append(Case(overlay=overlay,mutation=bits,controls=32,query=1,flags=0x4000))
 for timer,delta in itertools.product((1,2,65534,65535),(0,1,2,65534,65535,65536,0x7FFFFFFF,0x80000000,0x80000001,0xFFFFFFFF)):cs.append(Case(timer=timer,ticks=delta))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]
def check(m,c):
 expected,calls=reference(m.initial,c);assert m.calls==calls,('calls',c,m.calls,calls);assert public(m.memory)==public(expected),('public',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],('ABI',c)
def main():
 original=struct.unpack_from('>199I',(root/'conker/conker.us.bin').read_bytes(),0x8D90C);raw=words(out/'selected.o');assert [i for i,(a,b)in enumerate(zip(raw,original))if a!=b]==[131]
 cs=cases();coverage={};runs=0;full_state_pairs=0
 for c in cs:
  machines=[]
  for label,ws in [('raw',raw),('original',original)]:
   m=Oracle(ws,fixture(c),c);m.run();check(m,c);coverage.setdefault(label,set()).update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+796);machines.append(m);runs+=1
  a,b=machines;assert (a.memory,a.r,a.f,a.calls,a.trace)==(b.memory,b.r,b.f,b.calls,b.trace),('complete-state',c);full_state_pairs+=1
 result=dict(cases=len(cs),executions=runs,coverage={k:len(v)for k,v in coverage.items()},missing={k:[i for i in range(199)if i not in v]for k,v in coverage.items()},full_state_and_access_trace_pairs=full_state_pairs,actual_connected_recursion=True,upper_bits_and_timer_wrap=True,helper_algorithms_qualified=False)
 (out/'guest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
