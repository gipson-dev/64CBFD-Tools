from tools.tests.game_fade_graphic_151ed09c_oracle import *
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x234ac4)[0]==ENTRY
 start,end=0x151e8628,0x151e866c;table=0x8008ffc0;selector=0x800e0b94;segment=0x8003c8e0
 programs=[struct.unpack_from('>81I',rom,0x21a54c)]+[program(out/(x+'.o')) for x in ('after','generated','generic')]
 class Connected(Machine):
  def __init__(self,w,c):
   memory=fixture(c)
   for i in range(32):put(memory,table+4*i,ENTRY if i==17 else 0)
   memory[selector]=17;put(memory,segment,0xdeadbeef)
   code=dict(zip(range(ENTRY,ENTRY+len(w)*4,4),w));code[end]=0
   words=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2d4b0)
   FactoryOracle.__init__(self,words,memory,c,entry=start,s=S,arguments=(BASE,),connected=code)
   self.draws=0;self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,t):
   if t==ENTRY:self.calls.append((ENTRY,(self.r[4],)))
   else:super().record_call(t)
 count=0
 for phase,timer,level,mutation,alias in itertools.product((0,8),(0,63,64,0xffffffff),(0,127,255),(0,1),(0,1)):
  c=Case(phase,timer,level,mutation,alias);want,calls,value=reference(c);want=dict(want)
  for i in range(32):put(want,table+4*i,ENTRY if i==17 else 0)
  want[selector]=17;put(want,segment,0x09000000)
  for words in programs:
   m=Connected(words,c)
   try:m.run();raise AssertionError('missing caller boundary')
   except WindowBoundary:pass
   assert (public(m.memory),m.calls,m.r[4])==(want,[(ENTRY,(BASE,))]+calls,value),(c,m.calls,calls,m.r[4],value)
  count+=1
 print('original mode-17 indirect caller window:',count,'cases per stream',flush=True)
