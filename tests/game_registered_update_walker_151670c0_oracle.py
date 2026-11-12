import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_registered_update_walker_151670c0_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object

ENTRY=0x151670C0;TABLE=0x8008B4A8;LISTS=0x800DCE50;DEPTH=0x800DD190;SLOTS=0x800DD198
CALLBACKS=(0x15010000,0x15010020);NODES=(0x30000,0x30100,0x30200,0x30300,0x30400,0x30500)
@dataclass(frozen=True)
class Case:
 pattern:int;mutation:int;depth:int;phase:int;seed:int=0
def cases():return [Case(*p) for p in itertools.product(range(4),range(4),(0,2,4),(0,8))]
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,512)}
 for base,n in ((TABLE,101*0x34),(LISTS,0x340),(DEPTH,1),(SLOTS,24)):
  m.update({base+i:0 for i in range(n)})
 for node in NODES:m.update({node+i:(i*11+node//256)&255 for i in range(16)});put(m,node+8,0)
 m[DEPTH]=c.depth
 if c.pattern==1:put(m,TABLE+50*0x34,CALLBACKS[0])
 if c.pattern in (2,3):
  for col in (0,50,100):put(m,TABLE+col*0x34,CALLBACKS[0])
  for row,col,node in ((0,0,NODES[0]),(0,50,NODES[2]),(1,100,NODES[4])):put(m,LISTS+row*0x1a0+col*4,node)
  for node,nextnode in ((NODES[0],NODES[1]),(NODES[2],NODES[3]),(NODES[4],NODES[5])):put(m,node+8,nextnode if c.pattern==3 else 0)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+512}
def mutate(m,c,target,node,column):
 if c.mutation&1:put(m,node+8,0)
 if c.mutation&2 and node in (NODES[0],NODES[2],NODES[4]):put(m,SLOTS+m[DEPTH]*4,0)
 if c.mutation==3:put(m,TABLE+column*0x34,CALLBACKS[1])
def reference(c):
 m=fixture(c);calls=[]
 for row in range(2):
  for column in range(101):
   if not read(m,TABLE+column*0x34):continue
   node=read(m,LISTS+row*0x1a0+column*4);m[DEPTH]=(m[DEPTH]+1)&255
   while node:
    put(m,SLOTS+m[DEPTH]*4,read(m,node+8));target=read(m,TABLE+column*0x34)
    assert target in CALLBACKS;calls.append((target,node,read(m,SLOTS+m[DEPTH]*4)))
    mutate(m,c,target,node,column);node=read(m,SLOTS+m[DEPTH]*4)
   m[DEPTH]=(m[DEPTH]-1)&255
 return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,words,c):
  super().__init__(words,fixture(c),c,entry=ENTRY,arguments=());self.before=self.r[:];self.before_f=self.f[:];self.observed=[]
 def record_call(self,target):
  assert target in CALLBACKS,(hex(target),hex(self.r[4]));node=self.r[4]
  col=next(i for i in (0,50,100) if read(self.memory,TABLE+i*0x34)==target and node in ((NODES[0],NODES[1]) if i==0 else (NODES[2],NODES[3]) if i==50 else (NODES[4],NODES[5])))
  self.observed.append((target,node,read(self.memory,SLOTS+self.memory[DEPTH]*4),col));self.calls.append((target,(node,)))
 def hook(self,target):
  _,node,_,column=self.observed[-1];mutate(self.memory,self.case,target,node,column)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
def main():
 data,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_151670C0']['value'],fs['func_151670C0']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n}
 look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
 candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>74I',(root/'conker/conker.us.bin').read_bytes(),0x194570);seen=set()
 for c in cases():
  expected,calls=reference(c)
  for ws in (retail,candidate):
   m=Oracle(ws,c);m.run();assert public(m.memory)==expected,(c,'memory')
   assert [x[:3] for x in m.observed]==calls,(c,m.observed,calls)
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
   if ws is retail:seen.update(m.visits)
 report=dict(cases=len(cases()),retail_words_visited=sum(ENTRY+4*i in seen for i in range(74)),callbacks='modeled',valid_iterator_depth_only=True,source_installed=False)
 (out/'guest_151670C0_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
