from pathlib import Path
import itertools,struct,sys
from tools.experiments import game_eeprom_poller_151dcfd8_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_eeprom_poller_151dcfd8_guest as g
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();parent=struct.unpack_from('>45I',rom,0x20a850);start=0x151dd3a0;READ=0x151dd140;count=0
 class ReadMachine(g.Machine):
  def record_call(self,t):
   if t==READ:self.calls.append((t,tuple(self.arguments(3))))
   else:super().record_call(t)
  def hook(self,t):
   if t!=READ:return super().hook(t)
   queue,address,buffer=self.calls[-1][1]
   for i in range(8):self.memory[buffer+i]=(address+i)&255
   for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.r[2]=0
 for pending_length,read_length,clock in itertools.product((0,8,9),(0,1,8,9),(0,0xffffffff)):
  c=g.Case(1,0,pending_length,0,1,clock,0);initial=g.fixture(c);initial.update({0x70000+i:0xa5 for i in range(64)});m=initial.copy();calls=[]
  for i in range(4):
   public,step,result=g.reference(m,c);m.update(public);calls.append((g.ENTRY,(1,)));calls.extend(step)
   if result==0:break
  else:raise AssertionError('poll sequence did not finish')
  queue,addr,buffer=0x90000,254,0x70000
  for i in range((read_length+7)//8):
   address=(addr+i)&255;calls.append((READ,(queue,address,buffer+i*8)))
   for j in range(8):m[buffer+i*8+j]=(address+j)&255
  for p in g.words():
   code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(p),4),p));machine=ReadMachine(parent,c,initial.copy(),entry=start,arguments=(queue,addr,buffer,read_length),connected=code).run()
   assert (g.public(machine.memory),machine.calls,machine.r[2])==(g.public(m),calls,0),(pending_length,read_length,clock,machine.calls,calls)
  count+=1
 print(count,'complete original block-read callers per stream with connected poller and modeled EEPROM providers')
