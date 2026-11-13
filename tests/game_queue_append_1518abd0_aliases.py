def run():
 from pathlib import Path
 from tools.tests import game_queue_append_1518abd0_oracle as oracle
 ns=vars(oracle)
 from itertools import product
 Machine=ns['Machine'];Case=ns['Case'];program=ns['program'];root=ns['root'];out=ns['out'];struct=ns['struct'];public=ns['public'];put=ns['put'];STACK=ns['STACK'];Q=ns['Q'];HEAD=ns['HEAD'];TAIL=ns['TAIL'];NEW=ns['NEW'];BUILD=ns['BUILD'];FREE=ns['FREE'];MARK=ns['MARK'];CB=ns['CB']
 rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>82I',rom,0x1b8080);programs=[retail,program(out/'after.o'),program(out/'generated.o'),program(out/'generic.o')]
 class Alias(Machine):
  def __init__(self,w,c,p):super().__init__(w,c);self.ptr=p
  def hook(self,t):
   a=self.calls[-1][1];answer=0xabcdefff
   if t==BUILD:
    answer=self.ptr;put(self.memory,self.ptr+0x10,a[0]);put(self.memory,self.ptr+0x14,0);put(self.memory,self.ptr+0x18,0);self.memory[self.ptr+0x1c]=a[1]&255
   elif t==FREE:put(self.memory,MARK+4,a[0])
   else:put(self.memory,MARK,a[0])
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=answer

 def execute(w,c,p):
  m=Alias(w,c,p)
  try:m.run();error=None
  except (AssertionError,KeyError) as e:error=(type(e).__name__,str(e))
  return m,error
 count=0;stops=0;diff=[]
 for phase,nonempty,limit,selector,position in product((0,8),(0,1),(0,1,4),(0,1,255),range(10)):
  c=Case(phase,1,1,selector,1,limit,nonempty,1);ptr=(NEW,Q,Q+4,HEAD,HEAD+4,TAIL,TAIL+4,STACK+phase-0x40,STACK+phase-0x20,STACK+phase)[position];runs=[execute(w,c,ptr) for w in programs];a,err=runs[0];stops+=err is not None
  for b,e in runs[1:]:
   if (err,public(a.memory,c),a.calls,a.r[2])!=(e,public(b.memory,c),b.calls,b.r[2]):diff.append((c,position,err,e,a.calls,b.calls,a.r[2],b.r[2]));break
  count+=1
 print('allocation pointer alias cases',count,'stopped',stops,'differences',len(diff));print('examples',diff[:3]);assert not diff
