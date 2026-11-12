import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_scene_transition_dispatch_match as p
out=p.out; root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x1501C730; RESET=0x1501C53C; ADVANCE=0x15016680
MODE=0x800BE615; GATE=0x800BE616; SCENE=0x800BE9F4; ARG4=0x800BEA00; ARG3=0x800BEA04
PRIOR=0x800CC382; RESULT=0x800D2132; CHANNEL=0x800DD2C0; TABLE=0x800969A0
OFFSETS=(0x118,0x8c,0xb0,0xdc,0x54,0x100,0x54)
@dataclass(frozen=True)
class Case:
 command:int;gate:int;mutation:int;phase:int
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-256,256)}
 for base,n in ((MODE-4,12),(SCENE-4,24),(PRIOR-4,12),(RESULT-4,12),(CHANNEL-4,12),(TABLE,28)):
  m.update({base+i:(i*11+0x57)&255 for i in range(n)})
 m[GATE]=c.gate;put(m,PRIOR,0x81f2,2);put(m,STACK+c.phase+16,0x87654321)
 for i,v in enumerate(OFFSETS):put(m,TABLE+4*i,ENTRY+v)
 return m
def effect(m,c,t):
 if t==RESET and c.mutation:
  m[GATE]^=1;put(m,PRIOR,0x1234,2);put(m,SCENE,0xdeadbeef)
 if t==ADVANCE and c.mutation:
  m[MODE]=0x99;put(m,RESULT,0xbeef,2)
def public(m):return {a:v for a,v in m.items() if not STACK-256<=a<STACK+256}
def reference(c):
 m=fixture(c);calls=[RESET];effect(m,c,RESET);put(m,RESULT,0,2)
 if c.command in (4,6):
  put(m,ARG4,0x87654321);put(m,ARG3,0x13579bdf);put(m,SCENE,0xfedcba98);m[CHANNEL]=0x80;m[MODE]=2
 elif c.command==1:
  m[MODE]=3;put(m,SCENE,0xfedcba98);put(m,RESULT,read(m,PRIOR,2),2)
 elif c.command==2:
  m[MODE]=3;put(m,SCENE,0xfedcba98);m[CHANNEL]=0x80;put(m,RESULT,read(m,PRIOR,2),2)
 elif c.command==3 and not m[GATE]:
  m[MODE]=4;calls.append(ADVANCE);effect(m,c,ADVANCE)
 elif c.command==5:put(m,SCENE,5);m[MODE]=1
 return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(c.command,0xfedcba98,0xffffff80,0x13579bdf));self.before_f=self.f[:]
 def record_call(self,t):
  assert t in (RESET,ADVANCE),hex(t);self.calls.append(t)
 def hook(self,t):
  effect(self.memory,self.case,t)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
def main():
 data,fs,rs=parse_object(out/'candidate.o');a,n=fs['func_1501C730']['value'],fs['func_1501C730']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n}
 elf=(root/'conker/build/conker.us.elf').read_bytes();lookup={v[1]:v[2][1] for v in symbol_rows(elf)};lookup['.rodata']=TABLE
 candidate=bound_blob(data[a:a+n],refs,{nm:lookup[nm] for es in refs.values() for _,nm in es})
 rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>74I',rom,0x49BE0);assert tuple(candidate)==retail
 seen=set();count=0
 for command,gate,mutation,phase in itertools.product((0,1,2,3,4,5,6,7,8,255,0x7fffffff,0x80000000,0xffffffff),(0,1,255),(0,1),(0,8)):
  c=Case(command,gate,mutation,phase);expected,calls=reference(c)
  for words in (retail,candidate):
   m=Oracle(words,c).run();assert (public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls)
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
   seen.update(m.visits)
  count+=1
 missing=[hex(ENTRY+4*i) for i in range(74) if ENTRY+4*i not in seen]
 assert not missing,missing
 report=dict(cases=count,executions=count*2,visited_words=74,helper_effects_modeled=True,source_installed=False)
 (out/'guest_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
