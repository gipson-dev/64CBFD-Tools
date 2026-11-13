from tools.tests.game_impact_random_151ac408_oracle import *
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22ef08)[0]==ENTRY
 start,end=0x15148d80,0x15148db8;table=0x8008a430
 class Connected(Machine):
  def __init__(self,w,c):
   memory=fixture(c)
   for i in range(8):put(memory,table+4*i,ENTRY if i==6 else 0)
   for i,v in enumerate(args(c)[1:4]):put(memory,STACK+c.phase+0x40+4*i,v)
   code=dict(zip(range(ENTRY,ENTRY+len(w)*4,4),w));code[end]=0
   words=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2d4b0)
   FactoryOracle.__init__(self,words,memory,c,entry=start,s=S,arguments=(),connected=code)
   self.randoms=0;self.position=[];self.home=STACK+c.phase;self.r[16]=ACTOR;self.r[2]=6;self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,t):
   if t==ENTRY:self.calls.append((ENTRY,tuple(self.arguments(6))))
   else:super().record_call(t)
 count=0;streams=programs()
 for phase,index,selector,first,second,mode in itertools.product((0,8),(-2,0,2),(0,255),(0,1),(0,0xffffffff),(0,1,3,7)):
  c=Case(phase,index,selector,first,second,mode,2,result=ACTOR+0x64);want,calls,position,value=reference(c);want=dict(want)
  for i in range(8):put(want,table+4*i,ENTRY if i==6 else 0)
  for words in streams:
   m=Connected(words,c)
   try:m.run();raise AssertionError('missing caller boundary')
   except WindowBoundary:pass
   assert (public(m.memory),m.calls,m.position,m.r[2])==(want,[(ENTRY,args(c))]+calls,[position],value),(c,m.calls,calls)
  count+=1
 print('original index-6 indirect caller window:',count,'cases per stream',flush=True)
