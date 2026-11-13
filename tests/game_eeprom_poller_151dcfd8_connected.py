from pathlib import Path
import itertools,struct,sys
from tools.experiments import game_eeprom_poller_151dcfd8_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_eeprom_poller_151dcfd8_guest as g
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();parent=struct.unpack_from('>58I',rom,0x20a3a0);start=0x151dcef0;count=0
 for length,clock in itertools.product((1,8,9,16),(0,0xffffffff,0x100000000,0xffffffffffffffff)):
  c=g.Case(1,0,length,0,1,clock,0);initial=g.fixture(c);m=initial.copy();calls=[]
  for i in range(4):
   public,step,result=g.reference(m,c);m.update(public);calls.append((g.ENTRY,(1,)));calls.extend(step)
   if result==0:break
  else:raise AssertionError('poll sequence did not finish')
  queue,addr,buffer,newlength=0x70000,0x123456aa,0x80000,24
  g.put(m,g.SYMS['D_800E0A20'],queue);m[g.SYMS['D_800E0A24']]=addr&255;g.put(m,g.SYMS['D_800E0A28'],buffer);g.put(m,g.SYMS['D_800E0A2C'],newlength)
  product=(clock*12000)&0xffffffffffffffff;deadline=product//1000000
  calls.extend(((g.SYMS['__ll_mul'],(0,12000,clock>>32,clock&g.MASK)),(g.SYMS['__ull_div'],(product>>32,product&g.MASK,0,1000000)),(g.SYMS['osSetTimer'],(g.SYMS['D_80042A58'],deadline>>32,deadline&g.MASK,0,0,g.SYMS['__osEepromTimerQ'],g.SYMS['D_80042A90']))))
  for p in g.words():
   code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(p),4),p));machine=g.Machine(parent,c,initial.copy(),entry=start,arguments=(queue,addr,buffer,newlength),connected=code).run()
   assert (g.public(machine.memory),machine.calls,machine.r[2])==(g.public(m),calls,0xfeedface),(length,clock,machine.calls,calls)
  count+=1
 print(count,'complete original request callers per stream with connected poller and modeled EEPROM providers')
