def run():
 from pathlib import Path
 from tools.tests import game_actor_sentinel_query_15037880_oracle as oracle
 ns=vars(oracle)
 from tools.tests.game_owner_float_payload_oracle import FactoryOracle
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 from itertools import product
 Machine=ns['Machine'];Case=ns['Case'];program=ns['program'];root=ns['root'];out=ns['out'];struct=ns['struct'];put=ns['put'];fixture=ns['fixture'];output=ns['output'];u32=ns['u32'];STACK=ns['STACK'];ENTRY=ns['ENTRY'];S=ns['S'];START=0x15037b00;FAIL=0x15037b18;SUCCESS=0x15038080;rom=(root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>6I',rom,START-0x14fd2b50);retail=struct.unpack_from('>87I',rom,0x64d30);programs=[retail,program(out/'after.o'),program(out/'generated.o'),program(out/'generic.o')]
 class Window(Machine):
  def __init__(self,w,c):
   self.c=c;m=fixture(c);put(m,STACK+c.phase+0x84,0xcafebabe);code=dict(zip(range(ENTRY,ENTRY+len(w)*4,4),w));FactoryOracle.__init__(self,window,m,c,entry=START,s=S,arguments=(0,0,0,u32(c.index)),connected=code);self.r[4]=u32(c.index);self.r[16]=output(c);self.code=WindowCode(self.code,self);self.code.ends=(FAIL,SUCCESS)
  def record_call(self,t):assert t==ENTRY;self.calls.append((t,tuple(self.arguments(2))))
 count=0
 for phase,index,mode,kind,threshold,alias in product((0,8),(-1,0,1),range(8),(0,4),(0,1,3),(0,1,3)):
  c=Case(phase,index,mode,kind,0,threshold,alias);ms=[]
  for w in programs:
   m=Window(w,c)
   try:m.run();raise AssertionError('window did not stop')
   except WindowBoundary:pass
   ms.append(m)
  a=ms[0];assert all((m.memory,m.calls,m.r[2],m.r[31],m.visits)==(a.memory,a.calls,a.r[2],a.r[31],a.visits) for m in ms[1:]),c
  assert a.calls==[(ENTRY,(u32(index),output(c)))];assert (SUCCESS in a.visits)==(mode in (1,2,3));assert (FAIL in a.visits)==(mode in (0,4,5,6,7))
  count+=1
 print('original parent query window',count,'cases and both return branches across four streams')
