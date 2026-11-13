def run():
 from pathlib import Path
 from tools.tests import game_queue_append_1518abd0_oracle as oracle
 ns=vars(oracle)
 from itertools import product
 Machine=ns['Machine'];Case=ns['Case'];program=ns['program'];root=ns['root'];out=ns['out'];struct=ns['struct'];public=ns['public'];put=ns['put'];STACK=ns['STACK'];Q=ns['Q'];HEAD=ns['HEAD'];TAIL=ns['TAIL'];NEW=ns['NEW'];OWNER=ns['OWNER'];BUILD=ns['BUILD'];FREE=ns['FREE'];MARK=ns['MARK'];CB=ns['CB'];Q2=0x36000;ENTRY2=0x37000
 rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>82I',rom,0x1b8080);programs=[retail,program(out/'after.o'),program(out/'generated.o'),program(out/'generic.o')]
 class Mutation(Machine):
  def __init__(self,w,c,mode):
   super().__init__(w,c);self.mode=mode
   for i in range(0x80):self.memory[Q2+i]=self.memory[Q+i];self.memory[ENTRY2+i]=0
  def hook(self,t):
   a=self.calls[-1][1];answer=0xabcdefff
   if t==BUILD:
    if self.c.allocation:
     answer=NEW;put(self.memory,NEW+0x10,a[0]);put(self.memory,NEW+0x14,0);put(self.memory,NEW+0x18,0);self.memory[NEW+0x1c]=a[1]&255
    else:answer=0
    if self.mode&1:put(self.memory,self.r[29]+0x20,Q2)
    if self.mode&2:put(self.memory,self.r[29]+0x24,OWNER+16)
    if self.mode&4:put(self.memory,self.r[29]+0x2b,2,1)
   elif t==FREE:put(self.memory,MARK+4,a[0])
   else:
    put(self.memory,MARK,a[0])
    if self.mode&8:put(self.memory,self.r[29]+0x1c,ENTRY2)
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=answer
 count=0
 for phase,allocation,selector,limit,mode in product((0,8),(0,1),(0,1,255),(0,2),range(16)):
  c=Case(phase,1,allocation,selector,1,limit,1,1);ms=[Mutation(w,c,mode).run() for w in programs];a=ms[0]
  assert all((public(m.memory,c),m.calls,m.r[2])==(public(a.memory,c),a.calls,a.r[2]) for m in ms[1:]),(c,mode)
  count+=1
 print('incoming homes and callback slot mutations',count,'cases agree across four streams')
