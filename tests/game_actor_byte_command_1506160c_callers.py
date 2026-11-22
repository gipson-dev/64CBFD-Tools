"""Complete original/current byte-forwarding caller and an ignored-result ABI."""
from pathlib import Path
from dataclasses import replace
import csv,itertools,json,struct,sys
from tools.experiments import game_actor_byte_command_1506160c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_actor_byte_command_1506160c_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
PARENT=0x15076C7C;POINTER=0x800D154C;BYTE=0x800D1890
def main():
 elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();rom=(root/'conker/conker.us.bin').read_bytes()
 start=PARENT-0x15000000+0x2D4B0;truth=rom[start:start+56];at=elf_slot_offset(elf,PARENT,56);assert elf[at:at+56]==truth
 caller=list(struct.unpack('>14I',truth));jal=0x0C000000|(g.ENTRY>>2&0x3FFFFFF);assert caller.count(jal)==1
 direct=[];pointer_words=[]
 for i in range(0,len(rom)-3,4):
  w=struct.unpack_from('>I',rom,i)[0]
  if w==jal:direct.append(i)
  if w==g.ENTRY:pointer_words.append(i)
 def machine(ws,c,broken=False):
  c=replace(c,command=1,first=c.first&255,second=0,slot=0);memory=g.fixture(c);g.put(memory,POINTER,g.ACTOR);memory[BYTE]=c.first
  code=dict(zip(range(g.ENTRY,g.ENTRY+432,4),ws));words=list(caller)
  if broken:
   loads=[i for i,w in enumerate(words)if w>>26==35 and(w>>16&31)==4];assert len(loads)==1
   words[loads[0]]=0x00002025
  return g.Oracle(words,c,entry=PARENT,connected=code,memory=memory,args=()),c
 count=0;visits=set()
 for first,priority,gates,phase in itertools.product(range(256),(0,1,2,255),((0,0,0,0),(0,0,0,1)),(0,8)):
  c=g.Case(first=first,priority=priority,gates=gates,phase=phase);pair=[]
  for ws in g.streams():
   m,c2=machine(ws,c);m.run();assert m.calls==[(g.ENTRY,(g.ACTOR,1,first,0,0))]
   assert g.public(m.memory)==g.public(g.reference(m.initial,c2))
   assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f==m.before_f
   pair.append(g.state(m));visits.update(m.visits)
  assert pair[0]==pair[1];count+=1
 m,c=machine(g.streams()[0],g.Case(),True)
 try:m.run();raise AssertionError('missing-actor control ineffective')
 except AssertionError as e:assert 'unmapped'in str(e),str(e)
 assert {PARENT+4*i for i in range(14)}<=visits
 rows=list(csv.DictReader((root/'conker/progress.csv').open()));owners=[]
 for offset in direct:
  address=0x15000000+offset-0x2D4B0
  found=[r['function']for r in rows if r['section']=='game'and int(r['offset'])<=address<int(r['offset'])+int(r['length'])]
  owners.append(dict(ROM=f'0x{offset:X}',VA=f'0x{address:X}',owners=found))
 r=dict(cases_per_stream=count,streams=2,complete_caller_words=14,caller_frame=24,actual_original_current_slot_equal=True,
  direct_JAL_sites=owners,aligned_pointer_literals=[f'0x{x:X}'for x in pointer_words],all_256_forwarded_bytes=True,
  five_word_o32_arguments=True,callback_return_ignored=True,effective_missing_actor_control=True,
  source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='direct_JAL_sites'}),flush=True);return r
if __name__=='__main__':main()
