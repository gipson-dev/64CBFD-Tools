from pathlib import Path
import itertools,runpy,struct,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-query-list-1509dbbc-screen'
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.match_progress import load_elf_functions
g=runpy.run_path(str(out/'guest.py'));ENTRY=g['ENTRY'];STACK=g['STACK'];Case=g['Case'];PROGRAMS=g['programs']
HELPER=0x1509BE40;PACKET=0x800D2F60;COUNT=0x800D3840;TABLE=0x80088498
rom=(root/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>92I',rom,0xc92f0));actual,_,_=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');assert tuple(actual['func_1509BE40'][:92])==tuple(parent);assert struct.unpack_from('>I',rom,0x22cf58+13*4)[0]==ENTRY
class Connected(g['Machine']):
 def __init__(self,caller,words,c,m,n):
  self.c=c;self.n=n;self.entries=[];code=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));FactoryOracle.__init__(self,caller,m,c,entry=HELPER,s=g['SYMS'],arguments=(n,0xe000|c.key,c.mode,0x12340000,0x12340001,0x12340002),connected=code)
 def record_call(self,target):
  if target==ENTRY:self.entries.append((tuple(self.arguments(3)),read(self.memory,COUNT),tuple(read(self.memory,PACKET+4*i) for i in range(self.n+2))))
  else:raise AssertionError(('unexpected nested helper',hex(target)))
count=0
for key,mode,scenario,n in itertools.product((0,4,5,6,25,26,4095),(0,1,4,5),range(9),(0,1,3)):
 c=Case(key,mode,scenario);initial=g['fixture'](c)
 for base,length in ((PACKET,128),(TABLE,60),(COUNT,4)):initial.update({base+i:(i*29+0x35)&255 for i in range(length)})
 put(initial,COUNT,0x76543210);put(initial,TABLE+13*4,ENTRY);expected=initial.copy();put(expected,PACKET,key);put(expected,PACKET+4,mode)
 for i in range(n):put(expected,PACKET+8+4*i,0x12340000+i)
 result=g['reference'](c,expected)[1];expected_public=g['public'](expected);expected_packet=(key,mode,*[0x12340000+i for i in range(n)])
 for caller in (parent,list(actual['func_1509BE40'][:92])):
  for words in PROGRAMS:
   m=Connected(caller,words,c,initial.copy(),n).run();assert (g['public'](m.memory),m.r[2])==(expected_public,result),(c,n);assert m.entries==[((key,mode,PACKET),n+2,expected_packet)]
 count+=1
print(count,'complete original and linked query-dispatcher cases per callback stream, with variable argument counts 0, 1 and 3')
