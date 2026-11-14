from pathlib import Path
import itertools,json,struct
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-pointer-list-validation-15114f44-screen';conker=root/'conker';entry=0x15114f44
s={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};sym=lambda n:s[n];helper=sym('func_150AD770');lists=(0x30000,0x50000)
assert helper==0x150ad770 and struct.unpack_from('>4I',(conker/'conker.us.bin').read_bytes(),0xdac20)==(12,0,0,0)
programs={'retail':list(struct.unpack_from('>89I',(conker/'conker.us.bin').read_bytes(),0x1423f4)),'raw':bound_blob(*payload(Path(__import__('os').environ.get('POINTER_LIST_RAW',out/'selected.o')),'func_15114F44'),s),'guarded':bound_blob(*payload(Path(__import__('os').environ.get('POINTER_LIST_GUARDED',out/'guarded.o')),'func_15114F44'),s)};assert programs['retail']==programs['guarded']
class SyscallBoundary(Exception):pass
class Oracle(FactoryOracle):
 def __init__(self,words,memory,args,resume,mutate):
  connected=None if resume else {helper:0x0000000c,helper+4:0}
  super().__init__(words,memory,Case(),entry=entry,s={},arguments=args,connected=connected);self.mutate=mutate
 def record_call(self,t):
  assert t==helper,hex(t);self.calls.append((t,()));self.events.append(('CALL',t,()))
 def execute(self,w):
  if self.current_pc==helper and w==12:raise SyscallBoundary
  return super().execute(w)
 def hook(self,t):
  assert t==helper
  if self.mutate&1:
   count_addr=self.r[20];put(self.memory,count_addr,1)
  if self.mutate&2:
   for i in range(3):put(self.memory,STACK+4*i,0x12340000+i)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011

def fixture(mode,counts,pattern):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-256,128)}
 for n,length in (('D_800BE9F0',4),('D_800DBDD8',8),('D_800DBE18',12),('D_8003C8E0',4),('D_800DBF9C',12)):m.update({sym(n)+i:0x5a for i in range(length)})
 for base in lists:m.update({base+i:0 for i in range(36)})
 put(m,sym('D_800BE9F0'),mode)
 for g,base in enumerate(lists):
  put(m,sym('D_800DBDD8')+4*g,base);put(m,sym('D_800DBE18')+4*g,counts[g]&0xffffffff)
  for row in range(3):
   for col in range(3):put(m,base+row*12+col*4,0x80001000+g*0x100+row*12+col*4)
 if pattern == 10:
  put(m,lists[0],0x90000000);put(m,lists[0]+12,0x90000000)
 elif pattern:
  slot=(pattern-1)%3;bad=(pattern-1)//3;v=(0x90000000,0x80001001,0x7ffffffc)[bad];put(m,lists[0]+slot*4,v)
 return m

def public(m):return {a:v for a,v in m.items() if not STACK-256<=a<STACK+128}
def trace(q):return [x for x in q.trace if not STACK-256<=x[1]<STACK+128]
def model(initial,args,resume,mutate):
 m=initial.copy();calls=0
 if read(m,sym('D_800BE9F0')) not in (0x12,0x36,0x13):return public(m),calls,False
 for g in range(2):
  count=signed(read(m,sym('D_800DBE18')+4*g));base=read(m,sym('D_800DBDD8')+4*g);i=0
  while i<count:
   p=base+i*12;x=read(m,p);y=z=0
   valid=(x&0xf0000000)==0x80000000
   if valid:y=read(m,p+4);valid=(y&0xf0000000)==0x80000000
   if valid:z=read(m,p+8);valid=(z&0xf0000000)==0x80000000
   if valid:valid=not((x|y|z)&3)
   if not valid:
    put(m,sym('D_8003C8E0'),0x0c00005a);calls+=1
    if not resume:return public(m),calls,True
    if mutate&1:put(m,sym('D_800DBE18')+4*g,1)
    if mutate&2:args=(0x12340000,0x12340001,0x12340002)
    count=signed(read(m,sym('D_800DBE18')+4*g))
   i+=1
 for i,a in enumerate(args):put(m,sym('D_800DBF9C')+4*i,a)
 return public(m),calls,False

args=(0x11223344,0x55667788,0x99aabbcc)
