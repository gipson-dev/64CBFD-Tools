def run():
 from pathlib import Path
 from tools.tests import game_trajectory_actor_150e1570_oracle as oracle
 ns=vars(oracle)
 from itertools import product
 Machine=ns['Machine'];Case=ns['Case'];TABLE=ns['TABLE'];STACK=ns['STACK'];ENTRY=ns['ENTRY'];SOURCE=ns['SOURCE'];EMIT=ns['EMIT'];put=ns['put'];read=ns['read'];program=ns['program'];root=ns['root'];out=ns['out'];struct=ns['struct'];external=ns['external']
 retail=struct.unpack_from('>161I',(root/'conker/conker.us.bin').read_bytes(),0x10ea20);raw=program(out/'after.o')
 class AliasMachine(Machine):
  def __init__(self,w,c,ptr):
   super().__init__(w,c);self.ptr=ptr;self.r[4]=ptr;put(self.memory,ptr+0x76,0x1234,2);self.memory[ptr+0x124]=c.sourceSlot
  def hook(self,t):
   if t==EMIT:put(self.memory,self.ptr+0x76,0x6789,2)
   return super().hook(t)
 def execute(w,c,ptr):
  m=AliasMachine(w,c,ptr)
  try:m.run();error=None
  except (AssertionError,KeyError) as exc:error=(type(exc).__name__,str(exc))
  return m,error
 count=0;diffs=[];errors={}
 for phase,slot,offset in product((0,8),(0,1,25),(-0x1a0,-0x17c,-0x160,-0x140,-0x120,-0x110,-0xe0,-0xd0,-0xc0,-0xb0,-0xa0,-0x90,-0x80,-0x70,-0x60,-0x50,-0x40,-0x30,-0x20,-0x10,0,0x10)):
  c=Case(phase,slot,-1,0,0);ptr=STACK+phase+offset;a,ae=execute(retail,c,ptr);b,be=execute(raw,c,ptr);key=(ae,external(a.memory),a.calls,a.r[2]);other=(be,external(b.memory),b.calls,b.r[2]);count+=1
  if ae:errors[ae[0]]=errors.get(ae[0],0)+1
  if key!=other:diffs.append((phase,slot,offset,ae,be,a.r[2],b.r[2],a.calls[-1] if a.calls else None,b.calls[-1] if b.calls else None))
 for idx in (0,1,5,24):
  c=Case(0,0,-1,0,0);ptr=TABLE+idx*0x32c;a,ae=execute(retail,c,ptr);b,be=execute(raw,c,ptr);count+=1
  if (ae,external(a.memory),a.calls,a.r[2])!=(be,external(b.memory),b.calls,b.r[2]):diffs.append(('table',idx,ae,be))
 print('source aliases',count,'public/call/outcome differences',len(diffs));print('first differences',diffs[:5]);print('modeled stopped cases',errors)

 assert not diffs, diffs[:5]
