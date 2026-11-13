"""Independent descriptor model and overlap checks for both constructors."""
import itertools
from tools.tests import game_random_paired_constructor_oracle as g
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put

RANDOM_VALUES=(0xffffffff,0,0xffffffff,100,0,5,123456789,0x80000000)
FLOAT_VALUES=(0.0,0.25,0.5,0.75,1.0)

def programs(state,name):
 ws=[g.program(state[name][label],name)for label in ('after','retail','generated','generic')]
 assert ws[1]==ws[2]==ws[3]
 return ws

def expected(c,name):
 home=g.STACK+c.phase;d=home-0x70;p=home-0x9c;mem=g.fixture(c,name)
 ints=[RANDOM_VALUES[(i+c.seed)%8]for i in range(8)];floats=[FLOAT_VALUES[(i+c.seed)%5]for i in range(6)]
 f=lambda x:floating(bits(x))
 scale=f(f(floats[0]*62.0)+41.0)
 for off,value,size in ((0,0x200005,4),(4,0,4),(8,0xc01,2),(10,ints[2]%51+106,2),(12,0,4),(16,0,4)):
  put(mem,d+off,value,size)
 for i in range(7):mem[d+0x14+i]=0
 mem[d+0x1b]=ints[3]%101+100;mem[d+0x1c]=255;mem[d+0x1d]=47
 for off,value in ((0x1e,30),(0x20,8),(0x22,0)):put(mem,d+off,value,2)
 for off,value in ((0x24,0.0),(0x28,scale),(0x2c,scale),(0x30,1.5),(0x34,-4.0),(0x38,3.5),(0x3c,0.0),(0x40,0.0),(0x44,0.0),(0x48,-1.25*.125),(0x4c,0.0),(0x50,2.5*.125),(0x54,f(f(floats[5]*60.0)+21.0))):put(mem,d+off,bits(value))
 put(mem,d+0x58,0x3207|(0x40 if ints[0]&1 else 0)|(0x80 if ints[1]&1 else 0))
 for i,v in enumerate((5,5,4,255)):mem[d+0x60+i]=v
 put(mem,p,bits(scale));mem[p+4]=mem[p+5]=0;mem[p+6]=ints[4]%5+4;mem[p+7]=ints[5]%5+4
 for off,value in ((8,f(f(f(floats[1]*.25)+.25)*scale)),(12,f(f(f(floats[2]*.25)+.375)*scale)),(16,4.0),(20,.25),(28,f(f(f(floats[3]*.5)+.625)*scale)),(32,f(f(f(floats[4]*.75)+.875)*scale)),(36,12.5)):put(mem,p+off,bits(value))
 mem[p+24]=mem[p+25]=0;mem[p+26]=ints[6]%5+4;mem[p+27]=ints[7]%5+4
 return bytes(mem[d+i]for i in range(112)),bytes(mem[p+i]for i in range(40))

def ordinary(state):
 report={}
 order=(g.RNG,g.RNG,g.RNG,g.RNG,g.RF,g.RNG,g.RNG,g.RF,g.RF,g.RNG,g.RNG,g.RF,g.RF,g.RF,g.FACTORY)
 for name in state:
  ws=programs(state,name);n=0
  for phase,success,seed in itertools.product((0,8),(0,1),range(5)):
   c=g.Case(phase=phase,success=success,seed=seed);expected_desc,expected_payload=expected(c,name);states=[]
   for w in ws:
    m=g.Machine(w,c,g.fixture(c,name),name).run();home=g.STACK+phase
    assert tuple(x[0]for x in m.calls[:15])==order
    assert m.calls[14]==(g.FACTORY,(home-0x70,2,40),expected_desc),(name,c,'descriptor')
    if success:
     assert m.calls[15]==(g.COPY,(g.OUT+0xa8,home-0x9c,40),expected_payload),(name,c,'payload')
     assert bytes(m.memory[g.OUT+0xa8+i]for i in range(40))==expected_payload
    else:assert len(m.calls)==15
    public={a:v for a,v in m.memory.items()if not home-2048<=a<home+2048};states.append((public,m.calls))
   assert states.count(states[0])==4,(name,c);n+=1
  report[name]=n
 return report

def aliases(state):
 report={}
 for name in state:
  ws=programs(state,name);count=0
  for phase,delta,success in itertools.product((0,8),range(-0x180,0x41,4),(0,1)):
   c=g.Case(phase=phase,owner=g.STACK+phase+delta,success=success)
   states=[g.observed(w,c,name,True) for w in ws];assert states.count(states[0])==4,(name,c)
   count+=1
  report[name]=count
 return report
