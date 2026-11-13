def run():
 from pathlib import Path
 from tools.tests import game_queue_append_1518abd0_oracle as oracle
 ns=vars(oracle)
 from tools.tests.game_owner_float_payload_oracle import FactoryOracle
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 from itertools import product
 Machine=ns['Machine'];Case=ns['Case'];program=ns['program'];root=ns['root'];out=ns['out'];struct=ns['struct'];public=ns['public'];put=ns['put'];STACK=ns['STACK'];Q=ns['Q'];NEW=ns['NEW'];OWNER=ns['OWNER'];ENTRY=ns['ENTRY'];BUILD=ns['BUILD'];FREE=ns['FREE'];MARK=ns['MARK'];CB=ns['CB'];S=ns['S'];ALLOC=0x15167a68;GLOBAL=0x800d98e0
 rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>82I',rom,0x1b8080);programs=[retail,program(out/'after.o'),program(out/'generated.o'),program(out/'generic.o')];builder=struct.unpack_from('>28I',rom,BUILD-0x14fd2b50)
 class Connected(Machine):
  def __init__(self,scan,c,which):
   self.c=c;self.which=which;m=ns['fixture'](c);m.update({GLOBAL+i:0 for i in range(4)});put(m,GLOBAL,Q if c.present else 0);put(m,STACK+c.phase+0x88,OWNER)
   start,end=(0x150baf40,0x150baf58) if which==0 else (0x150cb68c,0x150cb6b0);body=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x14fd2b50);code=dict(zip(range(ENTRY,ENTRY+len(scan)*4,4),scan));code.update(zip(range(BUILD,BUILD+len(builder)*4,4),builder))
   FactoryOracle.__init__(self,body,m,c,entry=start,s=S,arguments=(Q if c.present else 0,OWNER,1),connected=code)
   if which==0:self.r[2]=OWNER
   self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,t):
   if t==ENTRY:a=tuple(self.arguments(3))
   elif t==BUILD:a=tuple(self.arguments(2))
   elif t==ALLOC:a=tuple(self.arguments(6))
   elif t==FREE or CB<=t<CB+1024:a=tuple(self.arguments(1))
   else:raise AssertionError(('unexpected',hex(t)))
   self.calls.append((t,a))
  def hook(self,t):
   a=self.calls[-1][1];answer=0xabcdefff
   if t==ALLOC:
    assert a==(30,0,32,1,255,1),a;answer=NEW if self.c.allocation else 0
   elif t==FREE:put(self.memory,MARK+4,a[0])
   elif CB<=t<CB+1024:put(self.memory,MARK,a[0])
   else:raise AssertionError(('unbounded',hex(t)))
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=answer
 count=0
 for phase,present,allocation,limit,which in product((0,8),(0,1),(0,1),(0,2),(0,1)):
  c=Case(phase,present,allocation,1,1,limit,1,1);ms=[]
  for w in programs:
   m=Connected(w,c,which)
   try:m.run();raise AssertionError('window did not stop')
   except WindowBoundary:pass
   ms.append(m)
  a=ms[0];assert all((public(m.memory,c),m.calls)==(public(a.memory,c),a.calls) for m in ms[1:]),(c,which)
  assert a.calls[0][0]==ENTRY and a.calls[0][1][2]==1+which
  if not present or not allocation:assert a.calls[-1]==(FREE,(OWNER,)),(c,which,a.calls)
  count+=1
 print('original allocator and two caller windows',count,'cases across four streams')
