from pathlib import Path
import itertools,struct
from tools.tests.game_script_sorted_insert_oracle import Oracle
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_view_scale_1500e738_guest import ENTRY,View,fixture
from tools.experiments import game_view_scale_1500e738_match as screen
root,out=screen.ROOT,screen.OUT;rom=(root/'conker/conker.us.bin').read_bytes();jal=struct.pack('>I',0x0C000000|((ENTRY>>2)&0x03FFFFFF));assert [i for i in range(0,len(rom)-3,4) if rom[i:i+4]==jal]==[0x350dc]
parent=0x15007B3C;words=list(struct.unpack_from('>64I',rom,0x34FEC));truth=list(struct.unpack_from('>86I',rom,0x3BBE8));blob,refs=payload(out/'padded.o','func_1500E738')
addresses={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};padded=list(bound_blob(blob,refs,{s:addresses[s] for v in refs.values() for _,s in v}))
base,data=sections(root/'conker/build/conker.us.elf')['.game_data'];view_table=data[0x800961D0-base:0x800961D0-base+64];caller_table=data[0x80095A50-base:0x80095A50-base+180]
BEFORE=(0x10004308,0x15002FB4,0x100014C4);STOP=0x1500C2A0
class Boundary(Exception):pass
class Caller(View):
 def __init__(self,child,initial):Oracle.__init__(self,words,initial,0,0,parent,{ENTRY+4*i:w for i,w in enumerate(child)})
 def record_call(self,t):
  if t==ENTRY:assert read(self.memory,0x800E0A00,1)==0;self.calls.append((t,()));return
  if t==STOP:raise Boundary()
  assert t in BEFORE,hex(t);args=tuple(self.arguments(1 if t in (0x15002FB4,0x100014C4) else 0));self.calls.append((t,args))
 def hook(self,t):
  assert t in BEFORE
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
count=0
for state,mode,category,bit in itertools.product((0,1,2,3,4),(1,2,4,8,16,255),(0,0x13,0x24,0x33,0x34,0x3f,0x40),(0,1)):
 initial=fixture(state,mode,view_table,0x800961D0)
 for i,b in enumerate(caller_table):initial[0x80095A50+i]=b
 for a,n in ((0x800BE9B4,4),(0x800BE9F4,4),(0x800B0DF0,4),(0x800D2E4C,4),(0x800E0A00,4),(0x300000,32),(0x310000,32)):
  for i in range(n):initial[a+i]=0
 put(initial,0x800BE9F4,category);put(initial,0x800B0DF0,0x300000);put(initial,0x800D2E4C,0x310000);initial[0x300011]=3;initial[0x310011]=bit*4;initial[0x800E0A00]=0xa5
 models=[]
 for child in (truth,padded):
  m=Caller(child,initial)
  try:m.run()
  except Boundary:pass
  else:raise AssertionError('Caller did not reach continuation boundary')
  models.append(m)
 assert models[0].memory==models[1].memory and models[0].calls==models[1].calls and models[0].trace==models[1].trace
 assert [t for t,args in models[0].calls].count(ENTRY)==1
 count+=1
print(count,'original caller prefixes per retail/padded body through following helper',flush=True)
