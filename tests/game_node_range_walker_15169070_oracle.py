"""Independent row/list state model, live continuation slots and bounded providers."""
import itertools,json,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_node_range_walker_15169070_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.pad_generated_object import parse_object
ENTRY=0x15169070;CLAMP=0x15143D18;HELPER=0x1516968C;CLEAN=0x1516972C;CB0=0x15600000;CB1=0x15600100;PAYLOAD=0x50000
SYMS=dict(func_15143D18=CLAMP,func_1516968C=HELPER,D_8008B4A8=0x8008B4A8,D_800DD198=0x800DD198,D_800DD190=0x800DD190,D_800DCE50=0x800DCE50)
NODES=tuple(0x30000+i*0x100 for i in range(10));u32=lambda v:v&0xFFFFFFFF;s32=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000;s8=lambda v:((v&255)^128)-128
@dataclass(frozen=True)
class Case:
 first:int=2
 last:int=4
 opcode:int=1
 depth:int=-1
 pattern:int=2
 mode:int=0
 empty:bool=False
 payload_kind:int=0
 tag:int=0x39
 real_helpers:bool=False
 phase:int=0
 caller:bool=False
def payload(c,s=SYMS):return(PAYLOAD,s['D_800DD190'],NODES[0]+8,STACK+c.phase+4,STACK+c.phase+64)[c.payload_kind]
def args(c,s=SYMS):return(u32(c.first),u32(c.last),payload(c,s),u32(c.opcode))
def slot(m,s=SYMS):return u32(s['D_800DD198']+4*s8(m[s['D_800DD190']]))
def fixture(c=Case(),s=SYMS):
 assert u32(s['D_800DCE50']+0x340)==s['D_800DD190'],'Row-array end binding changed'
 m={STACK+i:(i*17+0xA5)&255 for i in range(-4096,1024)}
 for i in range(-128,128):put(m,u32(s['D_800DD198']+4*i),0)
 for i in range(208):put(m,s['D_800DCE50']+i*4,0)
 for i in range(104):
  at=s['D_8008B4A8']+i*52;m.update({at+j:(i*31+j*13+7)&255 for j in range(52)});put(m,at+28,CB0 if c.pattern==1 or c.pattern==2 and i%2==0 else 0)
 for i,node in enumerate(NODES):
  m.update({node+j:(i*19+j*13+5)&255 for j in range(-8,136)});m[node]=2 if i in(0,1,2,5,6,8,9)else 3;m[node+12]=c.tag
  following={0:1,1:2,3:4,5:6,8:9}.get(i);put(m,node+8,NODES[following]if following is not None else 0)
 for row,col,n in((0,2,0),(0,3,3),(1,2,5),(1,3,7)):put(m,s['D_800DCE50']+row*416+col*4,0 if c.empty else NODES[n])
 m.update({PAYLOAD+i:(i*17+3)&255 for i in range(32)});m[PAYLOAD]=0x39;m[s['D_800DD190']]=c.depth&255;return m
def clamp(m,a):
 first,last=s32(read(m,a[0])),s32(read(m,a[1]));first,last=min(first,last),max(first,last);put(m,a[0],max(first,2));put(m,a[1],min(last,104))
def snapshot(m,c,s=SYMS):
 home=STACK+c.phase;return(m[s['D_800DD190']],read(m,slot(m,s)),read(m,home+4),read(m,home+8),read(m,home+12))
def effects(m,c,node,state,s=SYMS,recurse=None):
 if state['fired']:return
 state['fired']=True;cursor=slot(m,s);following=read(m,cursor)
 if c.mode&1:put(m,node+8,NODES[8])
 if c.mode&2:put(m,cursor,read(m,following+8)if following else 0)
 if c.mode&4:
  following=read(m,cursor);m[s['D_800DD190']]=(m[s['D_800DD190']]+1)&255;put(m,slot(m,s),following)
 if c.mode&8:put(m,s['D_8008B4A8']+52*m[node]+28,CB1)
 if c.mode&16:put(m,STACK+c.phase+4,3)
 if c.mode&32:put(m,STACK+c.phase+8,0x12345678);put(m,STACK+c.phase+12,0xABCD0010)
 if c.mode&64:
  assert recurse is not None;recurse()
 if c.mode&128:put(m,STACK+c.phase,99)
def reference(initial,c=Case(),s=SYMS):
 m=dict(initial);calls=[];observations=[];state=dict(fired=False)
 def walk(c):
  home=STACK+c.phase;put(m,home,c.first);put(m,home+4,c.last);put(m,home+12,c.opcode)
  def record(t,a):calls.append((t,tuple(a)));observations.append(snapshot(m,c,s))
  a=(home,home+4,2,104);record(s['func_15143D18'],a);clamp(m,a);first=s32(read(m,home));last=s32(read(m,home+4));column=u32(first*4);descriptor=u32(s['D_8008B4A8']+first*52)
  if first>=last:return
  put(m,home-24,column)
  def recur():
   child=replace(c,first=3,last=4,phase=c.phase-152);record(ENTRY,args(child,s));walk(child)
  outer=0
  while True:
   outer+=1;assert outer<=104,'Unbounded fixture columns'
   for row in range(2):
    callback=bool(read(m,descriptor+28));depth=m[s['D_800DD190']];node=read(m,u32(s['D_800DCE50']+416*row+column));m[s['D_800DD190']]=(depth+1)&255;cursor=slot(m,s);steps=0
    while node:
     steps+=1;assert steps<=32,'Unbounded fixture nodes';put(m,cursor,read(m,node+8));a=(node,payload(c,s),c.opcode&255);record(s['func_1516968C'],a)
     if not c.real_helpers:effects(m,c,node,state,s,recur)
     elif c.opcode&255 in(15,16)and m[payload(c,s)]==m[node+12]:record(CLEAN,(node,));effects(m,c,node,state,s,recur)
     if callback:
      t=read(m,descriptor+28);assert t in(CB0,CB1);record(t,a);effects(m,c,node,state,s,recur)
     cursor=slot(m,s);node=read(m,cursor)
    m[s['D_800DD190']]=(m[s['D_800DD190']]-1)&255
   column=u32(read(m,home-24)+4);put(m,home-24,column);descriptor=u32(descriptor+52)
   if s32(column)>=s32(u32(read(m,home+4)*4)):return
 walk(c);return m,calls,observations
class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c=Case(),s=SYMS,entry=ENTRY,connected=None,state=None):
  super().__init__(ws,memory,replace(c,phase=c.phase&8),entry=entry,s=s,connected=connected,arguments=args(c,s));self.case=c;self.target_home=STACK+c.phase;self.r[29]=STACK+c.phase;self.ws=ws;self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.observations=[];self.state=dict(fired=False)if state is None else state;self.bound_helpers={}if connected is None else connected
 def execute(self,word):
  if word>>26==0 and word&63==0x26:self.r[word>>11&31]=u32(self.r[word>>21&31]^self.r[word>>16&31]);self.r[0]=0;return
  return super().execute(word)
 def record_call(self,t):
  n=4 if t in(self.syms['func_15143D18'],ENTRY)else 3 if t in(self.syms['func_1516968C'],CB0,CB1)else 1 if t==CLEAN else None;assert n is not None,('Unbounded walker provider',hex(t));a=tuple(self.arguments(n));self.calls.append((t,a));self.observations.append(snapshot(self.memory,self.case,self.syms));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.case;s=self.syms;a=self.calls[-1][1]
  def recur():
   child=replace(c,first=3,last=4,phase=c.phase-152);self.calls.append((ENTRY,args(child,s)));self.observations.append(snapshot(self.memory,c,s));m=Oracle(self.ws,self.memory,child,s,connected=self.bound_helpers,state=self.state);m.run();self.memory.clear();self.memory.update(m.memory);self.calls.extend(m.calls);self.observations.extend(m.observations)
  if t==s['func_15143D18']:clamp(self.memory,a)
  else:
   assert t in(s['func_1516968C'],CB0,CB1,CLEAN);effects(self.memory,c,a[0],self.state,s,recur)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,0xA5000002
def words(p,s=SYMS):
 raw,fs,rs=parse_object(p);a,n=fs['func_15169070']['value'],fs['func_15169070']['size'];return bound_blob(raw[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s)
def public(m):return{a:v for a,v in m.items()if not STACK-4096<=a<STACK+1024}
def check(m,c=Case(),s=SYMS):
 want,calls,observations=reference(m.initial,c,s);assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),('walker public/call state',c)
 assert all(m.memory[p]==want[p]for p in m.initial if STACK+c.phase<=p<STACK+c.phase+64),('incoming homes',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
def helper_code(s=SYMS):
 result={};rom=(root/'conker/conker.us.bin').read_bytes();image=(root/'conker/build/conker.us.elf').read_bytes()
 for entry,offset,n,key in((CLAMP,0x1711C8,36,'func_15143D18'),(HELPER,0x196B3C,20,'func_1516968C')):
  raw=rom[offset:offset+4*n];at=elf_slot_offset(image,entry,4*n);assert image[at:at+4*n]==raw;result.update(zip(range(s[key],s[key]+4*n,4),struct.unpack('>%dI'%n,raw)))
 return result
def cases():
 result=[replace(Case(),pattern=pattern,mode=mode,phase=(mode&1)*8)for pattern,mode in itertools.product(range(3),range(256))]
 result +=[replace(Case(),opcode=op,real_helpers=True,tag=tag)for op,tag in itertools.product(range(256),(0,0x39))]
 result +=[replace(Case(),opcode=op)for op in(0x100,0x1000F,0x80000010,0xFFFFFFFF)]
 result +=[replace(Case(),depth=d,empty=empty)for d,empty in itertools.product(range(256),(False,True))]
 result +=[replace(Case(),first=a,last=b)for a,b in((0,1),(-1,5),(7,2),(104,105),(0x80000000,0x7FFFFFFF),(2,104),(2,2),(0xFFFFFFFF,3))]
 result +=[replace(Case(),payload_kind=kind,mode=mode,real_helpers=real,opcode=15)for kind,mode,real in itertools.product((1,2,3),(0,1,2,4,8,16,32,64,128),(False,True))]
 return result
def main():
 paths={'raw':out/'selected.o','normalized':out/'qualified-padded/game_1944C0.c.o','retail':out/'retail-reference.o'};coverage={};counts={};helpers=helper_code();total=0
 for label,path in paths.items():
  ws=words(path);seen=set()
  for c in cases():
   m=Oracle(ws,fixture(c),c,connected=helpers if c.real_helpers else None)
   try:m.run();check(m,c)
   except (AssertionError,KeyError)as e:raise AssertionError((label,c,str(e)))from e
   seen.update(m.visits)
  coverage[label]=sorted((p-ENTRY)//4 for p in set(range(ENTRY,ENTRY+496,4))-seen);assert coverage[label]==[75],(label,coverage[label]);counts[label]=len(cases());total+=len(cases())
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=dict(SYMS,func_15143D18=0x15300000,func_1516968C=0x15310000,D_8008B4A8=0x80300000+low,D_800DCE50=0x80400000+low,D_800DD190=0x80400340+low,D_800DD198=0x80400348+low)
  for path in paths.values():
   for mode in(0,15,64):
    c=replace(Case(),mode=mode);m=Oracle(words(path,s),fixture(c,s),c,s);m.run();check(m,c,s);rebases+=1
 report=dict(cases_per_body=counts,total=total,unreachable_words=coverage,retained_unreachable_signed_load=75,independent_rebases=rebases,real_helpers_compared_with_retail=True,scripted_helper_mutations_are_extensions=True,all_opcode_bytes=True,all_signed_depth_bytes=True,recursive_provider_extension=True,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
