"""Actual frame-layer registration and complete original/current caller execution."""
from pathlib import Path
import itertools,json,struct,sys
from tools.experiments import game_record_sound_scheduler_150d0730_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_record_sound_scheduler_150d0730_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
PARENT=0x151749F8;TABLE=0x8008CD04;SCENE=0x50000;SCENE_PTR=0x800B0DF0;PAIR=0x800B0E00;GATE=0x800BE616;PHASE=0x800CBD4E
PREFIX=(0x15165F70,0x15195FF0,0x1510C8A8);TAIL=(0x1517DE5C,0x151880C0)
class Caller(g.Oracle):
 def record_call(self,t):
  if t not in PREFIX+TAIL:return super().record_call(t)
  args=tuple(map(g.u32,self.arguments(2 if t==PREFIX[1]else 0)));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  if t not in PREFIX+TAIL:return super().hook(t)
  self.clobber(0x87654321)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 table=rom[0x2317C4:0x231834];at=elf_slot_offset(elf,TABLE,112);assert elf[at:at+112]==table and struct.unpack_from('>I',table,56)[0]==g.ENTRY
 body=rom[0x1A1EA8:0x1A1F54];at=elf_slot_offset(elf,PARENT,len(body));assert elf[at:at+len(body)]==body
 words=list(struct.unpack('>43I',body));assert words[20:24]==[0x8F39CD04,0x8FA4001C,0x0320F809,0]
 def machine(ws,c,index=14,gate=0,broken=False):
  memory=g.fixture(c);g.put(memory,SCENE_PTR,SCENE);memory.update({SCENE+i:0xA5 for i in range(32)});memory[SCENE+11]=index
  memory.update({TABLE+i:b for i,b in enumerate(table)});g.put(memory,PAIR,0x12345678);g.put(memory,PAIR+4,0x87654321);memory[GATE]=gate;g.put(memory,PHASE,0xFFF0,2)
  code=dict(zip(range(g.ENTRY,g.ENTRY+388,4),ws));caller=list(words)
  if broken:caller[21]=0
  return Caller(caller,c,entry=PARENT,connected=code,memory=memory,arguments=(0xABCDEF01,c.argument))
 count=0;visits=set()
 for timer,selection,mode,phase,gate,argument in itertools.product((0,127),range(7),(0,15),(0,8),(0,1),(0,0xFFFFFFFF)):
  c=g.Case(timer=timer,replies=tuple(i!=selection for i in range(6)),mode=mode,phase=phase,argument=argument);pair=[]
  for ws in g.streams():
   m=machine(ws,c,gate=gate).run();expected,calls,observations=g.reference(m.initial,c)
   want=[(PREFIX[0],()),(PREFIX[1],(0x12345678,0x87654321)),(PREFIX[2],()),(g.ENTRY,(argument,))]+calls
   if not gate:want +=[(t,())for t in TAIL]
   g.put(expected,PHASE,(0xFFF0+(g.read(expected,g.STEP)<<6))&65535,2)
   assert m.calls==want,(c,'caller ABI',m.calls,want)
   assert m.observations[1:]==observations and g.public(m.memory)==g.public(expected)
   pair.append(g.state(m));visits.update(m.visits)
  assert pair[0]==pair[1];count+=1
 for gate in(0,1):
  m=machine(g.streams()[0],g.Case(),index=0,gate=gate).run();assert all(t!=g.ENTRY for t,a in m.calls)
 c=g.Case(argument=0x13579BDF);m=machine(g.streams()[0],c,broken=True).run();assert (g.ENTRY,(c.argument,))not in m.calls
 assert {PARENT+4*i for i in range(43)}<=visits
 # No V0 read occurs between the callback and the next V0-defining LUI.
 assert words[24:33]==[0x3C18800C,0x9318E616,0x17000005,0,0x0D45F797,0,0x0D462030,0,0x3C02800D]
 r=dict(cases_per_stream=count,streams=2,original_call_window_words=43,current_complete_caller_equal=True,
  table_entries=28,callback_index=14,target_pointer_address='0x8008CD3C',incoming_view_word_checked=True,
  callback_return_ignored=True,zero_scene_gate_checked=True,tail_gate_and_phase_advance=True,
  effective_missing_view_reload_control=True,other_caller_helper_internals_contracted=True,source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
