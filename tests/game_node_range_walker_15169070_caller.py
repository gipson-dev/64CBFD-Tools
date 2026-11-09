"""All three retail JALs: exact live C wrapper and two live assembly packet windows."""
import json,struct,sys
from dataclasses import replace
from pathlib import Path
from tools.experiments.game_node_range_walker_15169070_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_node_range_walker_15169070_oracle as guest
from tools.experiments import game_node_range_walker_15169070_match as qualify
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.match_progress import load_elf_functions
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
WRAPPER=0x15169040;PARENT=0x1505B9C4;ACTOR0=0x60000;ACTOR1=0x61000
class CallerOracle(guest.Oracle):
 def record_call(self,t):
  if t==guest.ENTRY:
   assert tuple(self.arguments(4))==guest.args(self.case);self.root_calls+=1;self.root_initial=dict(self.memory)
   if self.packet is not None:
    p,actor,tag,tail=self.packet;assert(guest.read(self.memory,p),self.memory[p+4],bytes(self.memory[p+i]for i in(5,6,7)))==(actor,tag,tail)
   return
  super().record_call(t)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();jal=0x0C000000|((guest.ENTRY>>2)&0x3FFFFFF);j=0x08000000|((guest.ENTRY>>2)&0x3FFFFFF);calls=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==jal];ptrs=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==guest.ENTRY];jumps=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==j];assert calls==[0x892E0,0x89300,0x196508]and not ptrs and not jumps
 before=(out/'frozen'/qualify.ELF).read_bytes();after=(out/'qualified-image.elf').read_bytes();functions,_,_=load_elf_functions(str(out/'frozen'/qualify.ELF),'mips-linux-gnu-objdump');linked=[(n,i)for n,ws in functions.items()for i,w in enumerate(ws)if w==jal];assert sorted(n for n,i in linked)==['func_1505B9C4','func_1505B9C4','func_15169040'],linked
 for entry,offset,n in((WRAPPER,0x1964F0,48),(PARENT,0x88E74,0x77C)):
  at=elf_slot_offset(before,entry,n);assert before[at:at+n]==after[at:at+n]==rom[offset:offset+n],('Caller not retail exact',hex(entry))
 bodies=(guest.words(out/'selected.o'),guest.words(out/'qualified-padded/game_1944C0.c.o'),list(struct.unpack_from('>124I',rom,qualify.ROM)));count=0;seen=set();helpers=guest.helper_code()
 for which,(entry,stop)in enumerate(((WRAPPER,None),(0x1505BE10,0x1505BE38),(0x1505BE38,0x1505BE58))):
  length=48 if stop is None else stop-entry;offset=entry-0x15000000+0x2D4B0;window=list(struct.unpack_from('>%dI'%(length//4),rom,offset))
  for pattern,mode,phase,real in __import__('itertools').product(range(3),(0,15,16,64),(0,8),(False,True)):
   if which and mode==64:continue
   c=replace(guest.Case(),first=0,last=104,opcode=0xABCD000F if not which else 2,pattern=pattern,mode=mode,phase=phase,real_helpers=real,payload_kind=0 if not which else 4)
   if not which:c=replace(c,opcode=c.opcode&255)
   for ws in bodies:
    connected=dict(zip(range(guest.ENTRY,guest.ENTRY+496,4),ws))
    if real:connected.update(helpers)
    if stop is not None:connected[stop]=0
    m=CallerOracle(window,guest.fixture(c),c,entry=entry,connected=connected);m.ws=ws;m.root_calls=0;m.packet=None;home=guest.STACK+phase
    if not which:
     m.r[29]=home+24;m.r[4]=guest.payload(c);m.r[5]=0xABCD000F
    else:
     m.r[24]=ACTOR0;m.r[16]=ACTOR1;m.r[9]=0x70000;m.memory[ACTOR0+0x3B]=0xF7;m.memory[ACTOR1+0x3B]=0x80;guest.put(m.memory,home+0x3C,home+0x40);actor=ACTOR0 if which==1 else ACTOR1;tag=0xF7 if which==1 else 0x80;m.packet=(home+0x40,actor,tag,bytes(m.memory[home+0x40+i]for i in(5,6,7)))
     m.code=WindowCode(m.code,m);m.code.ends=(stop,)
    saved=m.r[:];m.before=m.r[:];saved_f=m.f[:]
    try:m.run()
    except WindowBoundary:assert stop is not None
    else:assert stop is None
    assert m.root_calls==1;want,expected,observations=guest.reference(m.root_initial,c);assert(guest.public(m.memory),m.calls,m.observations)==(guest.public(want),expected,observations),(which,c)
    assert all(m.memory[p]==want[p]for p in m.root_initial if home<=p<home+96)
    assert m.r[16:24]==saved[16:24]and m.r[28:31]==saved[28:31]and m.f[20:]==saved_f[20:]
    if not which:assert m.r[31]==saved[31]and guest.read(m.memory,home+28)==0xABCD000F
    seen.update(m.visits&set(range(entry,entry+length,4)));count+=1
 assert len(seen)==30,len(seen)
 report=dict(executions=count,bodies=3,retail_ROM_JALs=[hex(v)for v in calls],current_linked_JALs=len(linked),aligned_literal_pointers=0,direct_jumps=0,original_windows=3,original_window_words=[12,10,8],original_window_visited=30,live_retail_exact_C_wrapper=True,live_retail_exact_assembly_parent=True,assembly_parent_converted_or_fully_executed=False,packet_pointer_and_delay_slot_tag=True,native_original_wrapper_qualified_separately=True,full_parent_or_hardware_claimed=False)
 (out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
