import itertools,json,struct,sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from tools.experiments import game_actor_colored_dispatch_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x151026bc;HELPER=0x15100600;TABLE=0x800a2298;BYTE=0x800a2248;VEC1=0x800a21a0;VEC2=0x800a21f4;FLOAT=0x800a233c;ACTOR=0x30000;NESTED=0x40000
@dataclass(frozen=True)
class Case:
 identity:int;kind:int;mode:int;phase:int;present:bool=True
@lru_cache(maxsize=1)
def retail_table():
 elf=(root/'conker/build/conker.us.elf').read_bytes();return struct.unpack_from('>41I',elf,0x242b20+TABLE-0x80082b20)
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,256)}
 for base,n in ((ACTOR-4,0x330),(NESTED-4,0x90),(TABLE,164),(BYTE,256),(FLOAT,4)):
  m.update({base+i:(i*11+0x37)&255 for i in range(n)})
 m[ACTOR+4]=c.identity;put(m,ACTOR+0x31c,NESTED);m[NESTED+0x78]=c.kind
 # The jump table overlaps the byte-test range; retain its real entries and
 # derive expected byte values from memory, including for out-of-range modes.
 for i,v in enumerate(retail_table()):put(m,TABLE+4*i,v)
 put(m,FLOAT,0x3da3d70a)
 return m
def args(c):return (ACTOR if c.present else 0,0x12348001,0x12340000|c.mode,0xfedcba81,0x876543fe,0xabcdef01)
def reference(c,m):
 if not c.present:return [],0
 if c.identity in (0x58,0x5b,0x80):first,second=50,255
 elif c.identity in (0x5a,0x5f,0x74,0x75,0x7a):first,second=255,0
 else:first,second=((255,0)if c.kind==0x3b else(50,255))
 mode=c.mode&255;return [(HELPER,(ACTOR,VEC1+12*mode,VEC2+12*mode,m[BYTE+mode],0xffff8001,first,second,0,0x41a00000,0x41a00000,0x40800000,0x3da3d70a,0x81,0xfe,0xabcdef01))],0x87654321
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  self.initial=fixture(c);super().__init__(words,self.initial,c,entry=ENTRY,arguments=args(c));self.before_f=self.f[:]
 def record_call(self,t):assert t==HELPER;self.calls.append((t,tuple(self.arguments(15))))
 def hook(self,t):
  assert t==HELPER
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000;self.r[2]=0x87654321
def main():
 elf=(root/'conker/build/conker.us.elf').read_bytes();data,fs,rs=parse_object(out/'mixed-generated.o');a,n=fs['func_151026BC']['value'],fs['func_151026BC']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};lookup={v[1]:v[2][1]for v in symbol_rows(elf)};candidate=bound_blob(data[a:a+n],refs,{nm:lookup[nm]for es in refs.values()for _,nm in es});truth=struct.unpack_from('>75I',(root/'conker/conker.us.bin').read_bytes(),0x12fb6c);assert tuple(candidate)==truth
 seen=set();count=0
 cases=[Case(i,k,mode,phase)for i,k,mode,phase in itertools.product(range(256),(0x3b,0x3a),(0,6,7,255),(0,8))]+[Case(0,0,mode,phase,False)for mode,phase in itertools.product((0,255),(0,8))]
 for c in cases:
  expected,value=reference(c,fixture(c))
  for words in (truth,candidate):
   m=Oracle(words,c).run();assert m.calls==expected and m.r[2]==value,(c,m.calls,expected,hex(m.r[2]),hex(value))
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
   seen.update(m.visits)
  count+=1
 missing=[hex(ENTRY+4*i)for i in range(75)if ENTRY+4*i not in seen]
 report=dict(cases=count,executions=count*2,retail_words_visited=75-len(missing),unvisited=missing,helper='modeled',native_out_of_range_not_claimed=True,source_installed=False)
 (out/'guest_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
