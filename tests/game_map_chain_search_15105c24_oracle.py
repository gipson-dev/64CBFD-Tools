from dataclasses import dataclass
from pathlib import Path
import itertools,json,random,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
ENTRY,HEADS,COLUMNS,NODES,ACTOR,OBJECTS,SUBMIT=0x15105C24,0x800DCE50,0x800A5770,0x30000,0x80000,0x800CC2D0,0x1505D024
@dataclass(frozen=True)
class Case:
 seed:int=0
 key:int=0x80000000
 match:int=0
 depth:int=2
 columns:tuple=(35,95)
 phase:int=0
 attached:int=0
def cases():
 for key,match,depth,columns in itertools.product((0,0xFFFFFFFF,0x80000000,0x7FFFFFFF),range(-1,4),(0,1,2),((35,95),(95,35),(0,103),(35,35))):
  yield Case((key+match+depth)&7,key,match,depth,columns)
 for seed,attached in itertools.product(range(8),(0,OBJECTS-3*0x32C,OBJECTS-1,OBJECTS,OBJECTS+17*0x32C,OBJECTS+101*0x32C+800)):
  yield Case(seed,0x7FFFAA00,seed%5-1,seed%3,(35,95),8*(seed&1),attached)
def fixture(c):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-256,256)}
 for base,n in((HEADS,0x340),(ACTOR,0xA0),(NODES,0x1000)):
  m.update({base+i:0 for i in range(n)})
 put(m,COLUMNS,c.columns[0]);put(m,COLUMNS+4,c.columns[1]);put(m,ACTOR+0x7A,0x80A5+c.seed,2)
 for chain in range(4):
  group,row=divmod(chain,2);column=c.columns[group];head=NODES+chain*0x300
  put(m,HEADS+row*0x1A0+column*4,head if c.depth else 0)
  for depth in range(3):
   node=head+depth*0x80;put(m,node+8,node+0x80 if depth+1<c.depth else 0)
   variant=(depth+c.seed)%3
   m[node+0x13]=0xAE if variant==1 else 0x2E
   put(m,node+0x28,c.key if variant==1 else c.key^(0x10000 if variant==0 else 1))
   put(m,node+0x98,c.attached)
   if chain==c.match and depth==c.depth-1:m[node+0x13]=0x2E;put(m,node+0x28,c.key)
 return m
def reference(m,key):
 trace=[]
 def get(p,n):v=read(m,p,n);trace.append(('R',p,n,v));return v
 for group in range(2):
  column=get(COLUMNS+4*group,4)
  for row in range(2):
   node=get(HEADS+row*0x1A0+4*column,4)
   while node:
    if get(node+0x13,1)==0x2E and get(node+0x28,4)==key:return node,trace
    node=get(node+8,4)
 return 0,trace
class Oracle(FactoryOracle):
 def record_call(self,t):
  n={ENTRY:1,SUBMIT:4}[t];args=self.arguments(n);self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  assert t==SUBMIT
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=0xDEADBEEF
def preserved(m,c):
 assert m.r[29]==STACK+c.phase and all(m.r[i]==m.before[i]for i in(*range(16,24),28,30,31))and m.f[20:]==m.saved_f
def run(raw,retail,root):
 count=0;visits=[set(),set()];prefixes=0
 for c in cases():
  memory=fixture(c);value,trace=reference(memory,c.key)
  for i,words in enumerate((raw,retail)):
   m=Oracle(words,memory,c,entry=ENTRY,arguments=(c.key,)).run()
   assert m.r[2]==value and m.memory==memory and m.trace==trace,(c,i,m.r[2],value,m.trace,trace)
   preserved(m,c);visits[i].update(m.visits)
  count+=1
 c=Case(match=3,depth=3);memory=fixture(c);value,trace=reference(memory,c.key)
 for cut in range(len(trace)):
  for words in(raw,retail):
   m=Oracle(words,memory,c,entry=ENTRY,arguments=(c.key,));m.cut=cut
   try:m.run()
   except faults.AccessBoundary:pass
   else:raise AssertionError(('unfired read prefix',cut))
   assert m.trace==trace[:cut]and m.memory==memory
  prefixes+=1
 rom=(root/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>28I',rom,0x18D074));callers=0
 for c in [*list(cases())[::19],*list(cases())[-48:]]:
  memory=fixture(c);value,_=reference(memory,c.key);attached=read(memory,value+0x98)if value else 0
  delta=((attached-OBJECTS+0x80000000)&0xFFFFFFFF)-0x80000000
  index=(abs(delta)//0x32C)*(-1 if delta<0 else 1)if attached else-1
  want=[(ENTRY,(c.key,)),(SUBMIT,(ACTOR,0x6002E,read(memory,ACTOR+0x7A,2),index&0xFFFFFFFF))]
  for words in(raw,retail):
   linked=dict(zip(range(ENTRY,ENTRY+4*len(words),4),words))
   m=Oracle(parent,memory,c,entry=0x1515FBC4,connected=linked,arguments=(ACTOR,c.key)).run()
   assert m.calls==want,(c,m.calls,want);preserved(m,c)
  callers+=1
 return dict(cases=count,streams=2,visited_words=[len(v)for v in visits],public_read_prefixes=prefixes,caller_cases=callers,actual_parent_words=28,table_columns=[35,95],ABI_preserved=True,read_only_memory=True)
