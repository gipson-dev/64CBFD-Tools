def run():
 from pathlib import Path
 from tools.tests import game_actor_sentinel_query_15037880_oracle as oracle
 ns=vars(oracle)
 from tools.tests.game_owner_float_payload_oracle import FactoryOracle
 from itertools import product
 Machine=ns['Machine'];Case=ns['Case'];program=ns['program'];root=ns['root'];out=ns['out'];struct=ns['struct'];put=ns['put'];read=ns['read'];bits=ns['bits'];fixture=ns['fixture'];output=ns['output'];u32=ns['u32'];ENTRY=ns['ENTRY'];S=ns['S'];CALLER=0x1503b708;FALLBACK=0x150380c0;SENTINEL=0x800986ec;SCRATCH=0x800c3fd0;rom=(root/'conker/conker.us.bin').read_bytes();caller=struct.unpack_from('>45I',rom,0x68bb8);retail=struct.unpack_from('>87I',rom,0x64d30);programs=[retail,program(out/'after.o'),program(out/'generated.o'),program(out/'generic.o')]
 class Connected(Machine):
  def __init__(self,w,c):
   self.c=c;m=fixture(c)
   for base,n in ((SENTINEL,4),(SCRATCH,12)):m.update({base+i:0 for i in range(n)})
   put(m,SENTINEL,0xc7c34f80);args=(output(c),0x12345678,0x87654321,u32(c.index),bits(4.25),0xabcdef12,0x50000,9,10,11,12);code=dict(zip(range(ENTRY,ENTRY+len(w)*4,4),w))
   FactoryOracle.__init__(self,caller,m,c,entry=CALLER,s=S,arguments=args,connected=code)
  def record_call(self,t):
   if t==ENTRY:a=tuple(self.arguments(2))
   elif t==FALLBACK:a=tuple(self.arguments(11))
   else:raise AssertionError(('unexpected',hex(t)))
   self.calls.append((t,a))
  def hook(self,t):
   assert t==FALLBACK;a=self.calls[-1][1]
   for i,v in enumerate((10.0,20.0,30.0)):put(self.memory,a[0]+4*i,bits(v))
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=0xdeadbeef
 count=0
 for phase,mode,kind,threshold,alias in product((0,8),range(8),(0,4),(0,1,3),(0,1,3)):
  c=Case(phase,0,mode,kind,0,threshold,alias);ms=[Connected(w,c).run() for w in programs];a=ms[0]
  assert all((m.memory,m.calls,m.r[2])==(a.memory,a.calls,a.r[2]) for m in ms[1:]),c
  assert a.calls[0]==(ENTRY,(0,output(c)))
  if mode in (0,4,5,6,7):assert len(a.calls)==2 and a.calls[1][0]==FALLBACK and read(a.memory,output(c))==bits(10.0),c
  else:assert len(a.calls)==1,c
  count+=1
 print('original sentinel fallback caller connected',count,'cases across four streams; fallback helper modeled')
