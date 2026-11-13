from tools.tests.game_fixed_effect_150afc68_oracle import *
from types import SimpleNamespace
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();IDENT=0x800c3e78;windows=((0x150525bc,0x150525dc,3),(0x150525dc,0x15052600,2))
 class Connected(FactoryOracle):
  def __init__(self,w,phase,identity,window):
   start,end,_=window;m={STACK+phase+i:(i*17+0xa5)&255 for i in range(-512,256)};m[IDENT]=identity
   code=dict(zip(range(ENTRY,ENTRY+len(w)*4,4),w));code[end]=0
   words=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2d4b0)
   super().__init__(words,m,SimpleNamespace(phase=phase),entry=start,s=S,arguments=(0x800c0000,),connected=code)
   self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,t):
   assert t in (ENTRY,CALLEE),hex(t);n=6 if t==ENTRY else 49;self.calls.append((t,*self.arguments(n)))
  def hook(self,t):
   assert t==CALLEE
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)]
 count=0
 for phase,identity,window in itertools.product((0,8),(0,1,127,128,255),windows):
  args=(identity,window[2],1020,6,255,0);want=[(ENTRY,*args),(CALLEE,*packet(args))]
  for words in programs():
   m=Connected(words,phase,identity,window)
   try:m.run();raise AssertionError('missing caller boundary')
   except WindowBoundary:pass
   assert m.calls==want,(phase,identity,window,m.calls,want)
  count+=1
 print('two original caller windows:',count,'cases per stream, all 49 helper words',flush=True)
