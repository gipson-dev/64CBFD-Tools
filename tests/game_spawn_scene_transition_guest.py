import itertools,json,struct,sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from tools.experiments import game_spawn_scene_transition_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x1507dfe4;QUERY=0x15084d70;TRANSFORM=0x15022190;DISPATCH=0x1501d348;SCENE=0x800be9f0;MODE=0x800c35ea;FLAG0=0x800c3670;FLAG1=0x800c3671;POS=0x800c358c;ANGLE=0x800c3594;POSFLAG=0x800c3663;QUERYTABLE=0x800d212c;QUERYCOUNT=0x800d2128;QUERYGATE=0x800be616;ACTORPTR=0x800cc5ec;ACTOR=0x70000
@lru_cache(maxsize=1)
def retail_rom():return (root/'conker/conker.us.bin').read_bytes()
@dataclass(frozen=True)
class Case:
 gate:int;result:int;byte:int;mutate:int;phase:int;connected:int;write:int=1;query_connected:int=0
def cases():
 return [Case(*x)for x in itertools.product((0,1,2,255),(0,1,2,0xffffffff),(0,63,64,127,255),(0,1),(0,8),(0,1))]+[Case(0,r,b,0,p,1,0,q)for r,b,p,q in itertools.product((0,1,2,0xdeadbeef),(0,64,255),(0,8),(0,1))]
def fixture(c):
 m={STACK+i:(i*17+c.byte*3+0xa5)&255 for i in range(-1024,512)}
 for base,n in ((SCENE,4),(POS,0x100)):
  m.update({base+i:(i*11+c.byte+7)&255 for i in range(n)})
 put(m,SCENE,0x1234abcd);m[MODE]=c.gate;m[FLAG0]=0x83;m[FLAG1]=0x71
 sp=STACK+c.phase-0x68;put(m,sp+0x38,c.result);m[sp+0x4e]=c.byte
 if c.query_connected:
  for base,n in ((QUERYTABLE,4),(QUERYCOUNT,4),(QUERYGATE,1),(ACTORPTR,4),(ACTOR,0x120)):m.update({base+i:(i*7+3)&255 for i in range(n)})
  put(m,QUERYTABLE,0);put(m,QUERYCOUNT,0);m[QUERYGATE]=0;put(m,ACTORPTR,ACTOR)
 return m
def signed16(v):return ((v&0xffff)^0x8000)-0x8000
def coords(c):return (signed16(0x8000+c.byte),signed16(0x7fff-c.byte),signed16(0xff00+c.byte))
def effect(m,c,t):
 if c.mutate and t==QUERY:put(m,SCENE,0x7aa12345)
 if c.mutate and t==DISPATCH:put(m,SCENE,0xdeadbeef);m[FLAG1]=0x56
def transform(m,position,angle):
 put(m,ANGLE,angle)
 for i,v in enumerate(position):put(m,POS+2*i,v&0xffff,2)
 m[POSFLAG]=1
def reference(c):
 m=fixture(c);sp=STACK+c.phase-0x68;calls=[]
 if c.gate!=1:
  calls.append((QUERY,(0,0x12345678,1,sp+0x5c,sp+0x50,sp+0x4f,sp+0x4e,sp+0x44,sp+0x48,1,0)));effect(m,c,QUERY)
  if c.query_connected:m[ACTOR+0x11b]=0
  if c.result in (0,1):
   position=coords(c)if c.write else tuple(signed16(read(m,sp+0x5c+2*i,2))for i in range(3));angle=bits((c.byte-64)*1.40625+180.0);calls.append((TRANSFORM,tuple(v&0xffffffff for v in position)+(angle,)));transform(m,position,angle)
   saved=read(m,SCENE);put(m,SCENE,0x25);m[FLAG1]=1;calls.append((DISPATCH,(0x25,1 if c.result==0 else 3,0,0,0),0x25,1));effect(m,c,DISPATCH);m[FLAG0]=1;put(m,SCENE,saved)
 return calls,{a:v for a,v in m.items()if not STACK-1024<=a<STACK+512}
class Oracle(FactoryOracle):
 def __init__(self,words,c,result_offset=0x38):
  self.result_offset=result_offset;code={}
  if c.connected:
   rom=retail_rom();code=dict(zip(range(TRANSFORM,TRANSFORM+88,4),struct.unpack_from('>22I',rom,0x4f640)))
  if c.query_connected:
   rom=retail_rom();code.update(zip(range(QUERY,QUERY+1696,4),struct.unpack_from('>424I',rom,0xb2220)))
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(0x12345678,0xabcdef01),connected=code);self.before=self.r[:];self.before_f=self.f[:];self.actual_query=None
 def record_call(self,t):
  assert t in (QUERY,TRANSFORM,DISPATCH),hex(t);a=tuple(self.arguments({QUERY:11,TRANSFORM:4,DISPATCH:5}[t]))
  if t==QUERY:
   self.actual_query=a;assert a[10]==STACK+self.case.phase-0x68+self.result_offset;a=a[:10]+(0,)
  self.calls.append((t,a,read(self.memory,SCENE),self.memory[FLAG1])if t==DISPATCH else(t,a))
 def hook(self,t):
  c=self.case
  if t==QUERY and c.write:
   a=self.actual_query
   for i,v in enumerate(coords(c)):put(self.memory,a[3]+2*i,v&0xffff,2)
   for i in range(3):put(self.memory,a[4]+4*i,0x3f800000+i)
   self.memory[a[5]]=0xa5;self.memory[a[6]]=c.byte;put(self.memory,a[7],0x11223344);put(self.memory,a[8],0x55667788);put(self.memory,a[10],c.result)
  elif t==TRANSFORM:
   a=self.calls[-1][1];transform(self.memory,a[:3],a[3])
  effect(self.memory,c,t)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000;self.r[2]=0x60000000+len(self.calls)
def main():
 data,fs,rs=parse_object(out/'candidate.o');a,n=fs['func_1507DFE4']['value'],fs['func_1507DFE4']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};elf=(root/'conker/build/conker.us.elf').read_bytes();look={v[1]:v[2][1]for v in symbol_rows(elf)};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>76I',rom,0xab494);at=elf_slot_offset(elf,TRANSFORM,88);assert elf[at:at+88]==rom[0x4f640:0x4f698];seen=set();connected_seen=set()
 for c in cases():
  calls,public=reference(c)
  for ws,offset in ((retail,0x38),(candidate,0x38)):
   m=Oracle(ws,c,offset);m.run();actual={a:v for a,v in m.memory.items()if not STACK-1024<=a<STACK+512}
   assert (m.calls,actual)==(calls,public),(c,m.calls,calls)
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
   if ws is retail:
    seen.update(m.visits)
    if c.connected:connected_seen.update(m.visits)
 control=next(c for c in cases()if not c.write and c.query_connected and c.result==1);mutant=list(retail);assert mutant.count(0x8fa20038)==1;mutant[mutant.index(0x8fa20038)]=0x00001025
 m=Oracle(mutant,control);m.run();expected,_=reference(control);assert m.calls!=expected,'Unwritten-result negative control did not fail'
 report=dict(cases=len(cases()),unwritten_output_cases=sum(not c.write for c in cases()),original_query_early_exit_cases=sum(c.query_connected for c in cases()),unwritten_result_negative_control=True,retail_words_visited=sum(ENTRY+4*i in seen for i in range(76)),connected_helper_words_visited=sum(TRANSFORM+4*i in connected_seen for i in range(22)),connected_helper_matches_current_elf=True,source_installed=False);(out/'guest_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
