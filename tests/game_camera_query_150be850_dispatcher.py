from dataclasses import replace
from pathlib import Path
import itertools,runpy,struct,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-camera-condition-150be850-screen'
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put
from tools.match_progress import load_elf_functions
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
g=runpy.run_path(str(out/'guest.py'));Machine=g['Machine'];Case=g['Case'];ENTRY=g['ENTRY'];CAMERA=g['CAMERA'];STACK=g['STACK'];SYMS=g['SYMS'];programs=g['programs'];rom=(root/'conker/conker.us.bin').read_bytes()
entry=0x15130230;retail=list(struct.unpack_from('>20I',rom,0x15d6e0));actual,_,_=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');assert list(actual['func_15130230'][:20])==retail
table=rom[0x22e130:0x22e130+48*4];assert struct.unpack_from('>I',table,18*4)[0]==ENTRY
elf=(root/'conker/build/conker.us.elf').read_bytes();assert elf[elf_slot_offset(elf,0x80089670,len(table)):][:len(table)]==table
class Caller(Machine):
 def __init__(self,caller,words,c,m):
  self.c=c;self.entries=[];connected=dict(zip(range(ENTRY,ENTRY+4*len(words),4),words));FactoryOracle.__init__(self,caller,m,c,entry=entry,s=SYMS,arguments=(CAMERA,0x87654321),connected=connected)
 def record_call(self,t):
  if t==ENTRY:self.entries.append(tuple(self.arguments(1)))
  else:super().record_call(t)
count=0
for idx,path,phase in itertools.product((0,18),range(8),(0,8)):
 c=Case(3,1 if path&1 else 0,-1 if path&2 else 0,8 if path&4 else 0,1,1,1,phase);initial=g['fixture'](c);put(initial,0x800B0DF0,0x70000);initial.update({0x70000+i:0 for i in range(16)});initial[0x7000f]=idx;put(initial,0x80089670+18*4,ENTRY)
 expected=g['reference'](initial,c) if idx else ({a:b for a,b in initial.items() if not STACK-512<=a<STACK+512},[])
 for caller in (retail,list(actual['func_15130230'][:20])):
  for words in (programs[0],programs[1],programs[2],programs[3]):
   m=Caller(caller,words,c,initial.copy()).run();public={a:b for a,b in m.memory.items() if not STACK-512<=a<STACK+512};assert (public,m.calls)==expected,(idx,path,phase);assert m.entries==([(CAMERA,)] if idx else [])
 count+=1
print(count,'complete dispatcher cases per caller and callback stream; retail table and linked data unchanged')
