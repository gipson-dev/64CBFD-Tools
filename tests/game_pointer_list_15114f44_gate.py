"""Prove disabled modes and empty lists do not dereference absent entries."""
from tools.tests.game_pointer_list_15114f44_common import *
count=0
for mode in (0,0x11,0x14,0x35,0x37,0xffffffff):
 m=fixture(mode,(1,1),0)
 for base in (sym('D_800DBDD8'),sym('D_800DBE18')):
  for i in range(8):m.pop(base+i,None)
 want,calls,trap=model(m,args,False,0)
 for name in ('retail','raw','guarded'):
  q=Oracle(programs[name],m.copy(),args,False,0).run()
  assert public(q.memory)==want and not q.calls
 count+=1
for mode,n in itertools.product((0x12,0x13,0x36),(-1,0)):
 m=fixture(mode,(n,n),0)
 for g in range(2):put(m,sym('D_800DBDD8')+4*g,0xdeadfff0)
 want,calls,trap=model(m,args,False,0)
 for name in ('retail','raw','guarded'):
  q=Oracle(programs[name],m.copy(),args,False,0).run()
  assert public(q.memory)==want and not q.calls
 count+=1
assert count==12
print(json.dumps(dict(gate_cases=count,unmapped_globals_or_entries=True,uncredited=True)),flush=True)
