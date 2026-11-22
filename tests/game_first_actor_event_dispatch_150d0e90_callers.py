"""Execute the current retail-exact callback dispatcher with the qualified target."""
from pathlib import Path
import itertools,json,struct,sys
from tools.experiments import game_first_actor_event_dispatch_150d0e90_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_first_actor_event_dispatch_150d0e90_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
PARENT=0x151749F8;SCENEP=0x800B0DF0;SCENE=0x70000;TABLE=0x8008CD04
POST=0x800BE616;PHASE=0x800CBD4E;PAIRS=0x800B0E00
PRE=(0x15165F70,0x15195FF0,0x1510C8A8);AFTER=(0x1517DE5C,0x151880C0)
SIGN={PRE[0]:0,PRE[1]:2,PRE[2]:0,AFTER[0]:0,AFTER[1]:0}

class Oracle(g.Oracle):
 def record_call(self,t):
  if t not in SIGN:return super().record_call(t)
  args=tuple(map(g.u32,self.arguments(SIGN[t])));self.calls.append((t,args))
  self.events.append(('CALL',t,args));self.observations.append(g.observe(self.memory))
 def hook(self,t):
  if t not in SIGN:return super().hook(t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=0x12345678;self.f[:20]=[0xA5000000+i for i in range(20)]
  self.hi,self.lo=0xA5000010,0xA5000011

def main():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 parent=list(struct.unpack_from('>43I',rom,0x1A1EA8));at=elf_slot_offset(elf,PARENT,172)
 assert elf[at:at+172]==rom[0x1A1EA8:0x1A1F54]
 at=elf_slot_offset(elf,TABLE,112);table=elf[at:at+112]
 assert table==rom[0x2317C4:0x231834]and struct.unpack_from('>I',table,19*4)[0]==g.ENTRY
 target_at=elf_slot_offset(elf,g.ENTRY,596)
 assert elf[target_at:target_at+596]==struct.pack('>3I',0x00001025,0x03E00008,0)+bytes(584)
 live=(root/'conker/build/conker.us.elf').read_bytes();live_at=elf_slot_offset(live,g.ENTRY,596)
 assert live[live_at:live_at+596]==(rom[0xFE340:0xFE594]if packet.installed()else elf[target_at:target_at+596])
 count=0;visited=set()
 def make(ws,c,scene,post,view):
  memory=g.fixture(c)
  for a,n in((SCENEP,4),(SCENE,16),(TABLE,112),(POST,1),(PHASE,2),(PAIRS,8)):
   memory.update({a+i:0xA5 for i in range(n)})
  g.put(memory,SCENEP,SCENE);memory[SCENE+11]=scene;memory[POST]=post
  for i,b in enumerate(table):memory[TABLE+i]=b
  g.put(memory,PHASE,65530,2);g.put(memory,PAIRS,0xFFFFFFFF);g.put(memory,PAIRS+4,0x12345678)
  code=dict(zip(range(g.ENTRY,g.ENTRY+596,4),ws))
  return Oracle(parent,c,entry=PARENT,connected=code,memory=memory,arguments=(0xABCDEF01,view))
 for mask,gate,mode,phase,scene,post,view in itertools.product((0,5,15),(0,255),(0,4,15),(0,8),(0,19),(0,1),(0,0x80000000)):
  c=g.Case(mask=mask,gate=gate,mode=mode,phase=phase);states=[]
  for ws in g.streams():
   m=make(ws,c,scene,post,view);initial=dict(m.memory);m.run();visited.update(m.visits)
   expected,calls,observations=g.reference(initial,c)if scene else(initial,[],[])
   prefix=[(PRE[0],()),(PRE[1],(0xFFFFFFFF,0x12345678)),(PRE[2],())]
   all_calls=prefix+([(g.ENTRY,(view,))]if scene else[])+calls+([(v,())for v in AFTER]if not post else[])
   all_observations=[g.observe(initial)]*(3+bool(scene))+observations+([g.observe(expected)]*2 if not post else[])
   g.put(expected,PHASE,g.read(expected,PHASE,2)+(g.read(expected,g.TICKS)<<6),2)
   assert m.calls==all_calls,(c,scene,post,view,'calls',m.calls,all_calls)
   assert m.observations==all_observations,(c,scene,post,view,'observations')
   assert g.public(m.memory)==g.public(expected),(c,'memory')
   states.append(g.state(m))
  assert states[0]==states[1];count+=1
 broken=list(parent);assert broken[21]==0x8FA4001C;broken[21]=0
 m=make(g.streams()[0],g.Case(),19,0,0xCAFEBABE);m.code.update(zip(range(PARENT,PARENT+172,4),broken));m.run()
 assert next(a for t,a in m.calls if t==g.ENTRY)!=(0xCAFEBABE,)
 r=dict(cases_per_stream=count,streams=2,full_current_dispatcher_words=43,current_dispatcher_equals_original=True,
        dispatcher_words_executed=sum(PARENT+4*i in visited for i in range(43)),table_entries=28,callback_index=19,
        table_address='0x8008CD04',target_pointer_address='0x8008CD50',baseline_target_was_zero_stub=True,current_target_restored=packet.installed(),
        first_argument_is_unused_view=True,callback_return_ignored=True,effective_missing_argument_load_control=True,
        parent_other_helpers_modeled=True,source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
