from pathlib import Path
import itertools,struct
from tools.tests.game_script_sorted_insert_oracle import Oracle
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_cache_expiry_1517abb0_guest import ENTRY,Expiry,Case,fixture
from tools.experiments import game_cache_expiry_1517abb0_match as screen
root,out=screen.ROOT,screen.OUT;rom=(root/'conker/conker.us.bin').read_bytes()
jal=struct.pack('>I',0x0C000000|((ENTRY>>2)&0x3FFFFFF));assert [i for i in range(0,len(rom)-3,4) if rom[i:i+4]==jal]==[0x468e4]
parent=0x15019414;words=list(struct.unpack_from('>20I',rom,0x468c4));truth=list(struct.unpack_from('>84I',rom,0x1A8060))
_,fs,_=parse_object(out/'variant-split.o');at=fs['func_1517ABB0']['value'];raw=list(struct.unpack('>84I',sections(out/'variant-split.elf')['.text'][1][at:at+336]))
blob,refs=payload(out/'padded.o','func_1517ABB0');addresses={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};padded=list(bound_blob(blob,refs,{s:addresses[s] for v in refs.values() for _,s in v}))
BEFORE,AFTER=0x15167010,0x1508F0A4
class Caller(Expiry):
 def __init__(self,child,initial,c):
  self.case=c;self.frees=0
  Oracle.__init__(self,words,initial,0,c.phase,parent,{ENTRY+4*i:w for i,w in enumerate(child)})
 def record_call(self,t):
  if t in (ENTRY,BEFORE,AFTER):self.calls.append((t,()));self.events.append(('CALL',t,()))
  else:super().record_call(t)
 def hook(self,t):
  if t not in (BEFORE,AFTER):return super().hook(t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
count=0
for active,after,mode,pattern,enabled,phase in itertools.product((0,1),(0,1),range(5),range(4),(0,1,3),(0,8)):
 c=Case(3,2,3,2,pattern,mode,enabled,phase);initial=fixture(c);initial[0x800BEAC0]=active;initial[0x800BE616]=after
 models=[Caller(child,initial,c).run() for child in (truth,raw,padded)]
 for m in models:
  targets=[t for t,args in m.calls];assert targets.count(ENTRY)==1 and targets.count(BEFORE)==(not active) and targets.count(AFTER)==(not after)
 for m in models[1:]:assert m.memory==models[0].memory and m.calls==models[0].calls and m.trace==models[0].trace,(c,active,after)
 count+=1
print(count,'complete original frame-caller cases per retail/raw/padded body',flush=True)
