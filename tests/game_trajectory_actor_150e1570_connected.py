def run():
 from pathlib import Path
 from tools.tests import game_trajectory_actor_150e1570_oracle as oracle
 ns=vars(oracle)
 from tools.tests.game_owner_float_payload_oracle import FactoryOracle
 from itertools import product
 Machine=ns['Machine'];Case=ns['Case'];program=ns['program'];root=ns['root'];out=ns['out'];struct=ns['struct'];external=ns['external'];put=ns['put'];bits=ns['bits'];fixture=ns['fixture'];STACK=ns['STACK'];SOURCE=ns['SOURCE'];ENTRY=ns['ENTRY'];S=ns['S']
 CALLBACK=0x15072f10;VECTOR=0x1505a184;CURRENT=0x800d154c;SCALE=0x8009a094;STATE=0x60000;rom=(root/'conker/conker.us.bin').read_bytes();callback=struct.unpack_from('>79I',rom,0xa03c0);retail=struct.unpack_from('>161I',rom,0x10ea20);programs=[retail,program(out/'after.o'),program(out/'generated.o'),program(out/'generic.o')]
 class Connected(Machine):
  def __init__(self,scan,c):
   self.c=c;self.scores=[];m=fixture(c)
   for base,size in ((CURRENT,4),(SCALE,4),(STATE,0x100)):m.update({base+i:0 for i in range(size)})
   put(m,CURRENT,SOURCE);put(m,SCALE,bits(.25));put(m,SOURCE+0x31c,STATE);put(m,SOURCE+0x7a,0x1234,2);m[SOURCE+0x1d1]=250;put(m,STATE+0x12,25,2);put(m,STATE+0x24,9,2)
   for off,v in ((0x14,10.5),(0x18,20.5),(0x1c,-30.5)):put(m,SOURCE+off,bits(v))
   put(m,SOURCE+0xd6,5,2);code=dict(zip(range(ENTRY,ENTRY+4*len(scan),4),scan))
   FactoryOracle.__init__(self,callback,m,c,entry=CALLBACK,s=S,arguments=(0,),connected=code)
  def record_call(self,t):
   if t==VECTOR:self.calls.append((t,tuple(self.arguments(6))))
   elif t==ENTRY:self.calls.append((t,tuple(self.arguments(9))))
   else:super().record_call(t)
  def hook(self,t):
   if t!=VECTOR:return super().hook(t)
   a=self.calls[-1][1]
   for p,v in ((a[3],11.25),(a[4],-22.5),(a[5],33.75)):put(self.memory,p,bits(v))
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=0xabcdef01
 count=0
 for phase,slot,excluded,flags,pattern in product((0,8),(0,1,25),(0,9),(0,7),range(5)):
  c=Case(phase,slot,excluded,flags,pattern);machines=[Connected(w,c).run() for w in programs];a=machines[0]
  assert all((external(m.memory),m.calls,m.r[2])==(external(a.memory),a.calls,a.r[2]) for m in machines[1:]),c
  assert [x[0] for x in a.calls[:3]]==[VECTOR,ENTRY,0x15047390]
  assert a.r[2]==0xdeadbeef and ns['read'](a.memory,STATE+0x24,2)==8;cals=a.calls[1][1];assert cals[0]==SOURCE and cals[7]==0xcd and cals[8]==18
  count+=1
 print('connected original callback cases',count,'return and state agree through all four streams')
