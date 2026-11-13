from tools.tests.game_fixed_effect_150afc68_oracle import *
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put
from types import SimpleNamespace
ALLOC=0x15167a68;RECORD=0x50000
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();helper=struct.unpack_from('>125I',rom,0x19ae4c);helpercode=dict(zip(range(CALLEE,CALLEE+len(helper)*4,4),helper))
 def expected_record(args,success):
  m={RECORD+i:0xa5 for i in range(0x50)}
  if not success:return m
  p=packet(args)
  for off,index in ((0xe,0),(0x10,1),(0x12,2),(0x14,27),(0x16,28),(0x18,29),(0x1a,30),(0x20,31),(0x1c,36),(0x1e,37),(0x22,38)):put(m,RECORD+off,p[index],2)
  for i in range(24):m[RECORD+0x24+i]=p[3+i]&255
  m[RECORD+0x3c]=p[31]&255
  for i in range(4):m[RECORD+0x3d+i]=p[32+i]&255
  for off,index in ((0x41,39),(0x43,40),(0x44,41),(0x45,42),(0x46,43),(0x47,45),(0x48,46)):m[RECORD+off]=p[index]&255
  m[RECORD+0x42]=0
  return m
 class Connected(FactoryOracle):
  def __init__(self,w,args,phase,success):
   m={STACK+phase+i:(i*17+0xa5)&255 for i in range(-512,256)};m.update({RECORD+i:0xa5 for i in range(0x50)})
   super().__init__(w,m,SimpleNamespace(phase=phase,success=success),entry=ENTRY,s=S,arguments=args,connected=helpercode)
  def record_call(self,t):
   assert t in (CALLEE,ALLOC),hex(t);self.calls.append((t,*self.arguments(49 if t==CALLEE else 6)))
  def hook(self,t):
   assert t==ALLOC
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.r[2]=RECORD if self.case.success else 0
 count=0
 for args,phase,success in itertools.product(list(cases())[:19],(0,8),(0,1)):
  p=packet(args);want=[(CALLEE,*p),(ALLOC,0x11,args[5],0x4c,0,args[4]&255,1)]
  for words in programs():
   m=Connected(words,args,phase,success).run();actual={RECORD+i:m.memory[RECORD+i] for i in range(0x50)}
   assert m.calls==want and actual==expected_record(args,success),(args,phase,success,m.calls,want)
  count+=1
 print('connected original 49-argument helper:',count,'cases per stream, allocator success and failure',flush=True)
