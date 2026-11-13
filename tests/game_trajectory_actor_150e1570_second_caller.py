def run():
 from pathlib import Path
 from tools.tests import game_trajectory_actor_150e1570_oracle as oracle
 ns=vars(oracle)
 from tools.tests.game_owner_float_payload_oracle import FactoryOracle
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 from itertools import product
 Machine=ns['Machine'];Case=ns['Case'];program=ns['program'];root=ns['root'];out=ns['out'];struct=ns['struct'];external=ns['external'];put=ns['put'];bits=ns['bits'];fixture=ns['fixture'];STACK=ns['STACK'];SOURCE=ns['SOURCE'];ENTRY=ns['ENTRY'];TABLE=ns['TABLE'];S=ns['S']
 WINDOW=0x150e2740;END=0x150e27d0;OBJECT=0x60000;rom=(root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>%dI'%((END-WINDOW)//4),rom,WINDOW-0x15000000+0x2d4b0);retail=struct.unpack_from('>161I',rom,0x10ea20);programs=[retail,program(out/'after.o'),program(out/'generated.o'),program(out/'generic.o')]
 class Window(Machine):
  def __init__(self,scan,c,index):
   self.c=c;self.scores=[];m=fixture(c);m.update({OBJECT+i:0 for i in range(0x200)})
   for off,v in ((0x94,10.0),(0x98,20.0),(0x9c,30.0)):put(m,OBJECT+off,bits(v))
   ptr=0 if index<0 else TABLE+index*0x32c;put(m,OBJECT+0xdc,ptr)
   if ptr==0:
    for i in range(25):put(m,TABLE+i*0x32c,0)
   code=dict(zip(range(ENTRY,ENTRY+4*len(scan),4),scan));FactoryOracle.__init__(self,window,m,c,entry=WINDOW,s=S,arguments=(0,),connected=code)
   self.r[16]=OBJECT;self.r[15]=1;self.f[14]=bits(1.0);self.f[16]=bits(2.0);self.f[18]=bits(3.0);self.code=WindowCode(self.code,self);self.code.ends=(END,)
  def record_call(self,t):
   if t==ENTRY:self.calls.append((t,tuple(self.arguments(9))))
   else:super().record_call(t)
 count=0
 for phase,index,flags,pattern in product((0,8),(-1,0,5,24),(0,7),range(5)):
  c=Case(phase,0,-1,flags,pattern);ms=[]
  for w in programs:
   m=Window(w,c,index)
   try:m.run();raise AssertionError('window did not stop')
   except WindowBoundary:pass
   ms.append(m)
  a=ms[0];assert all((external(m.memory),m.calls,m.r[2])==(external(a.memory),a.calls,a.r[2]) for m in ms[1:]),(c,index)
  first=a.calls[0][1];assert first[0]==(0 if index<0 else TABLE+index*0x32c) and first[7]==(0 if index<0 else index) and first[8]==0,(index,first)
  count+=1
 print('original second-caller window',count,'cases through all four scan streams, including null source with no eligible actors')
