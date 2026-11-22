"""The original/current callback prefix and complete scene dispatcher ABI."""
from pathlib import Path
import itertools,json,struct,sys
from tools.experiments import game_view_color_script_150d08c0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_view_color_script_150d08c0_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
PARENT=0x15130230;TABLE=0x80089670;SCENE=0x50000;POINTER=0x800B0DF0
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 body=rom[0x15D6E0:0x15D724];at=elf_slot_offset(elf,PARENT,80);assert elf[at:at+80]==body+bytes(12)
 table=rom[0x22E130:0x22E1C0];at=elf_slot_offset(elf,TABLE,144);assert elf[at:at+144]==table
 assert struct.unpack_from('>I',table,120)[0]==g.ENTRY
 words=list(struct.unpack('>17I',body));assert words[11:13]==[0x0320F809,0]
 def machine(ws,c,index=30,broken=False):
  memory=g.fixture(c);memory.update({SCENE+i:0xA5 for i in range(32)});memory[SCENE+15]=index;g.put(memory,POINTER,SCENE)
  memory.update({TABLE+i:b for i,b in enumerate(table)})
  code=dict(zip(range(g.ENTRY,g.ENTRY+1488,4),ws));caller=list(words)
  if broken:caller[12]=0x00002025
  return g.Oracle(caller,c,entry=PARENT,connected=code,memory=memory,arguments=(g.VIEW,0x87654321))
 count=0;visits=set()
 for replies,mode,phase,rm in itertools.product(((0,0,0,0),(1,1,0,0),(1,0,1,0),(1,0,0,1),(1,0,0,0)),(0,7),(0,8),range(4)):
  c=g.Case(replies=replies,mode=mode,phase=phase,fcsr=rm);pair=[]
  for ws in g.streams():
   m=machine(ws,c).run();expected,calls,observations=g.reference(m.initial,c)
   assert m.calls==[(g.ENTRY,(g.VIEW,))]+calls
   assert m.observations[1:]==observations and g.public(m.memory)==g.public(expected)
   assert m.fcsr==c.fcsr;pair.append(g.state(m));visits.update(m.visits)
  assert pair[0]==pair[1];count+=1
 for phase in(0,8):
  m=machine(g.streams()[0],g.Case(phase=phase),index=0).run();assert not m.calls and g.public(m.memory)==g.public(m.initial)
 m=machine(g.streams()[0],g.Case(),broken=True)
 try:m.run();raise AssertionError('missing-view negative ineffective')
 except AssertionError as e:assert 'unmapped read'in str(e),str(e)
 assert {PARENT+4*i for i in range(17)}<=visits
 r=dict(cases_per_stream=count,streams=2,original_call_window_words=17,current_complete_dispatcher_equal=True,
  caller_slot_padding_bytes=12,callback_prefix_entries=36,callback_index=30,target_pointer_address='0x800896E8',
  complete_table_symbol_has_following_graphics_words=True,incoming_A0_preserved=True,callback_return_ignored=True,
  zero_scene_gate_checked=True,effective_missing_view_control=True,source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
