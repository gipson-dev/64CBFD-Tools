import itertools,struct
from tools.tests import game_checksum_record_spawn_oracle as g
from tools.experiments import game_checksum_record_spawn_match as packet
from pathlib import Path
from tools.tests.test_game_point_transform_match import put
O=packet.OUT;CORE=0x15149130
class Connected(g.Machine):
 def record_call(self,t):
  if t==CORE:self.calls.append((t,tuple(self.arguments(9))))
  else:super().record_call(t)
 def hook(self,t):
  if t!=CORE:return super().hook(t)
  n=self.n;self.n+=1
  if n==0:
   if self.case.mutation&1:put(self.memory,g.COUNT,1)
   if self.case.mutation&2:put(self.memory,g.PTR,g.TABLE2)
   if self.case.mutation&4:self.memory[self.case.owner+0x3b]^=0x5a
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.r[2]=0 if n==self.case.fail else g.OUT+n*0x100
def run():
 rom=(packet.ROOT/'conker/conker.us.bin').read_bytes();off=0x2d4b0+(g.FACTORY-0x15000000);w=struct.unpack_from('>28I',rom,off);code=dict(zip(range(g.FACTORY,g.FACTORY+112,4),w));programs=[g.words(O/(x+'.o'))for x in ('retail','after','generated','generic')];cases=0;visited=set()
 for count,fail,mismatch,mutation in itertools.product((0,1,3),(0,1,9),(0,1),(0,2,7)):
  c=g.Case(count=count,fail=fail,mismatch=mismatch,mutation=mutation);states=[]
  for ws in programs:
   m=Connected(ws,c);m.code.update(code);m.run();public={a:v for a,v in m.memory.items() if not g.STACK-2048<=a<g.STACK+2048};states.append((public,m.calls));visited.update(m.visits&set(code))
  assert states.count(states[0])==4,c
  ref,calls=g.reference(c);public={a:v for a,v in ref.items() if not g.STACK-2048<=a<g.STACK+2048};assert states[0][0]==public,c
  expected=[]
  for _,a in calls:expected.extend(((g.FACTORY,a),(CORE,(a[0],a[1],a[2],0xffffffff,*a[3:]))))
  assert states[0][1]==expected,(c,states[0][1],expected);cases+=1
 print('factory wrapper connected cases',cases,'visited',len(visited),'of',len(code))
