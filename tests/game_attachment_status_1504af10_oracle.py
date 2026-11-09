"""Packed attachment state, live pointer/index aliases and the real zero resolver."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_attachment_status_1504af10_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.pad_generated_object import parse_object
ENTRY=0x1504AF10;HELPER=0x1504AEF4;TABLE0=0x300000;TABLE1=0x500000
SYMS=dict(func_1504AEF4=HELPER,D_800DBEF4=0x800DBEF4,D_800CC2D0=0x800CC2D0)
u32=lambda n:n&0xFFFFFFFF
s32=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
s16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 flags:int=0x3001
 force:int=0
 release:int=0
 answer:int=0
 resolved:int=7
 effects:int=0
 actor_index:int=1
 field:int=0xE7
 positions:tuple=(0x41480000,0xC0200000,0x422E0000)
 offset:int=0xFFFF
 alias:int=0
 phase:int=0
def actor(c,s=SYMS):return u32(s['D_800CC2D0']+812*c.actor_index)
def alternate(s=SYMS):return u32(s['D_800CC2D0']+812*26)
def args(c,s=SYMS):return(actor(c,s),u32(c.force),u32(c.release))
def fixture(c=Case(),s=SYMS):
 home=STACK+c.phase;pointer=s['D_800DBEF4'];p=actor(c,s);base=TABLE0
 if c.alias==1:base=u32(p+0x92-0x4E-(c.flags&4095)*160)
 elif c.alias==2:base=u32(pointer+3-0x4F-(c.flags&4095)*160)
 elif c.alias==3:base=u32(home-8+3-0x4F-(c.flags&4095)*160)
 elif c.alias==4:base=u32(p+10-(c.flags&4095)*160)
 m={home+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for ap in(p,alternate(s)):m.update({u32(ap+i):(i*13+0x59)&255 for i in range(-8,820)})
 if c.alias==2:
  start=pointer&0xFFFF0000;m.update({start+i:(i*13+0x59)&255 for i in range(0x10000)})
 indices={0,1,7,4095,c.flags&4095,c.resolved&4095,0x6400}
 for table in(base,TABLE1):
  for index in indices:
   at=u32(table+index*160);m.update({u32(at+i):(i*29+0xA5)&255 for i in range(-8,168)});m[u32(at+79)]=c.field
 for ap in(p,alternate(s)):
  for i,v in enumerate(c.positions):put(m,ap+20+4*i,v)
  put(m,ap+144,c.offset,2);put(m,ap+146,c.flags,2)
 put(m,pointer,base);return m
def effects(m,c,s=SYMS):
 home=STACK+c.phase;p=actor(c,s)
 if c.effects&1:
  put(m,p+146,c.flags^0x55,2);put(m,s['D_800DBEF4'],TABLE1)
  for i,value in enumerate((-12.75,-4.25,15.5)):put(m,p+20+4*i,bits(value))
  put(m,p+144,0xFFE0,2)
 if c.effects&2:put(m,home+4,0x100);put(m,home+8,0x80000000)
 if c.effects&4:put(m,home,alternate(s));put(m,s['D_800DBEF4'],TABLE1)
def snapshot(m,c,s=SYMS):
 home=STACK+c.phase;return(read(m,actor(c,s)+146,2),read(m,s['D_800DBEF4']),read(m,home),read(m,home+4),read(m,home+8))
def trunc(word):
 value=math.trunc(floating(word));assert -0x80000000<=value<0x80000000,'Outside qualified signed conversion';return value&65535
def reference(initial,c=Case(),s=SYMS,connected=False):
 m=dict(initial);home=STACK+c.phase;slot=home-8;p=actor(c,s);put(m,home+4,c.force);put(m,home+8,c.release);flags=read(m,p+146,2);calls=[];observations=[]
 if not flags or not c.force and flags&0x8000:return m,calls,observations
 kind=(flags>>12)&7
 if not kind:
  put(m,home,p);calls.append((s['func_1504AEF4'],(flags&0x7FFF,slot)));observations.append(snapshot(m,c,s))
  if connected:kind=0
  else:put(m,slot,c.resolved);effects(m,c,s);kind=u32(c.answer)
  p=read(m,home)
  if kind:put(m,p+146,u32(kind<<12)|read(m,slot),2)
 put(m,slot,read(m,p+146,2)&4095)
 if kind!=3:return m,calls,observations
 def record():return u32(read(m,s['D_800DBEF4'])+read(m,slot)*160)
 if read(m,home+8):m[record()+78]=0;put(m,p+146,0,2);return m,calls,observations
 distance=s32(p-s['D_800CC2D0']);index=(abs(distance)//812)*(-1 if distance<0 else 1);m[record()+78]=(index+100)&255
 if read(m,home+4):m[record()+78]=0;return m,calls,observations
 q=record();m[q+79]=m[q+79]&0x9F;q=record();m[q+79]|=0x20
 q=record();value=read(m,p+20);put(m,q+16,trunc(value),2)
 offset=s16(read(m,p+144,2));q=record();value=bits(floating(read(m,p+24))+float(offset));put(m,q+18,trunc(value),2)
 q=record();value=read(m,p+28);put(m,q+20,trunc(value),2);return m,calls,observations
class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  super().__init__(ws,memory,c,entry=entry,s=s,connected=connected,arguments=args(c,s));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observations=[]
 def record_call(self,t):
  assert t==self.syms['func_1504AEF4'];a=tuple(self.arguments(2));self.calls.append((t,a));self.observations.append(snapshot(self.memory,self.case,self.syms));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert len(self.calls)==1;put(self.memory,self.calls[-1][1][1],self.case.resolved);effects(self.memory,self.case,self.syms)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=u32(self.case.answer);self.hi,self.lo=0xA5000010,0xA5000011
def words(p,s=SYMS):
 raw,fs,rs=parse_object(p);a,n=fs['func_1504AF10']['value'],fs['func_1504AF10']['size'];return bound_blob(raw[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s)
def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+1024}
def check(m,c=Case(),s=SYMS,connected=False):
 want,calls,observations=reference(m.initial,c,s,connected);assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),('attachment/public/ABI',c)
 assert all(m.memory[p]==want[p]for p in m.initial if STACK+c.phase<=p<STACK+c.phase+512),('caller storage',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
def cases():
 result=[]
 for flags,force,release in itertools.product((0,1,7,0xFFF,0x1001,0x3000,0x3001,0x3FFF,0x7007,0x8000,0x8001,0xB001,0xFFFF),(0,1,0x100,0x80000000),(0,1,0x100)):
  result.append(replace(Case(),flags=flags,force=force,release=release,phase=(len(result)&1)*8))
 for answer,resolved,mode in itertools.product((0,1,3,7,0x10003,0xFFFFFFFF),(0,1,4095,0xFFFFFFFF),(0,1,2,4,7)):
  result.append(replace(Case(),flags=1,answer=answer,resolved=resolved,effects=mode,phase=(len(result)&1)*8))
 for field in range(256):result.append(replace(Case(),field=field,phase=(field&1)*8))
 for answer in(0x10000,0x80000000):result.append(replace(Case(),flags=1,answer=answer,resolved=7))
 for index in(-100,-1,0,1,25,155,156,255):result.append(replace(Case(),actor_index=index))
 for pos,offset in(((0.,0.,0.),0),((-12.75,-5.5,7.75),0x8000),((1000000.,-1000000.,32768.75),0xFFFF)):
  result.append(replace(Case(),positions=tuple(bits(v)for v in pos),offset=offset))
 for alias in(1,2,3,4):result.append(replace(Case(),flags=0x3000,actor_index=0,alias=alias,positions=(bits(258.),0,0),offset=0))
 result.append(replace(Case(),flags=0x3000,actor_index=90,alias=2,positions=(bits(258.),0,0),offset=0))
 result.append(replace(Case(),flags=0x3000,actor_index=0,alias=4,positions=(bits(-1.),bits(512.),0),offset=0))
 return result
def helper(s=SYMS):
 rom=(root/'conker/conker.us.bin').read_bytes();raw=rom[0x783A4:0x783C0];elf=(root/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,HELPER,28);assert elf[at:at+28]==raw;return dict(zip(range(s['func_1504AEF4'],s['func_1504AEF4']+28,4),struct.unpack('>7I',raw)))
def main():
 paths={'raw':out/'qualified-owner.o','normalized':out/'qualified-padded/game_77AD0.c.o','retail':out/'retail-reference.o'};counts={};coverage={};real=rebases=0
 for label,path in paths.items():
  ws=words(path);seen=set()
  for c in cases():m=Oracle(ws,fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  counts[label]=len(cases());coverage[label]=len(seen&set(range(ENTRY,ENTRY+4*len(ws))));assert coverage[label]==len(ws)
  for flags in(0,1,0xFFF,0x8001,0x3001,0xBFFF):
   for force in(0,1):
    c=replace(Case(),flags=flags,force=force);m=Oracle(ws,fixture(c),c,connected=helper());m.run();check(m,c,connected=True);real+=1
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=dict(func_1504AEF4=0x15300000,D_800DBEF4=0x80300000+low,D_800CC2D0=0x80400000+low)
  for path in paths.values():
   for phase in(0,8):
    c=replace(Case(),flags=1,phase=phase);m=Oracle(words(path,s),fixture(c,s),c,entry=ENTRY+0x4000,s=s,connected=helper(s));m.run();check(m,c,s,True);rebases+=1
 report=dict(cases_per_body=counts,total=sum(counts.values()),coverage=coverage,real_zero_resolver_executions=real,independent_rebases=rebases,all_status_bytes=True,scripted_nonzero_returns_are_extension_cases=True,guest_only_aliases=4,guest_home_mutations=True,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
