"""Complete original no-argument wrappers plus fresh JAL and dispatch-pointer census."""
import itertools,json,struct,sys
from pathlib import Path
from tools.experiments.game_actor_selection_15075650_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_actor_selection_15075650_oracle as guest
from tools.experiments import game_actor_selection_15075650_match as qualify
from tools.match_progress import load_elf_functions
WRAPPERS=((0x15075B8C,0xA303C,10),(0x150761C8,0xA3678,5),(0x150779A8,0xA4E58,11))
class CallerOracle(guest.Oracle):
 def record_call(self,t):
  if t==guest.ENTRY:self.root_calls+=1;self.root_initial=dict(self.memory);return
  return super().record_call(t)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();jal=0x0C000000|((guest.ENTRY>>2)&0x3FFFFFF);j=0x08000000|((guest.ENTRY>>2)&0x3FFFFFF)
 calls=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==jal];ptrs=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==guest.ENTRY];jumps=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==j]
 assert calls==[0xA3044,0xA3680,0xA4E60]and ptrs==[0x22B388]and not jumps
 before=(out/'frozen'/qualify.ELF).read_bytes();after=(out/'qualified-image.elf').read_bytes();functions,_,_=load_elf_functions(str(out/'frozen'/qualify.ELF),'mips-linux-gnu-objdump');linked=[(n,i)for n,ws in functions.items()for i,w in enumerate(ws)if w==jal];assert sorted(linked)==[('func_15075B8C',2),('func_150761C8',2),('func_150779A8',2)]
 bodies=(guest.words(out/'selected.o'),guest.words(out/'qualified-padded/game_A28B0.c.o'),list(struct.unpack_from('>141I',rom,qualify.ROM)));count=0;seen=set()
 for entry,offset,status in WRAPPERS:
  raw=rom[offset:offset+44];at=qualify.elf_slot_offset(before,entry,44);assert before[at:at+44]==after[at:at+44]==raw
  ws=list(struct.unpack('>11I',raw));assert ws[0]==0x27BDFFE8
  for mode,mutation,phase,real in itertools.product((0,254,255),(0,1,2,4,8,15),(0,8),(False,True)):
   c=guest.replace(guest.Case(),mode=mode,mutation=mutation,phase=phase,real=real)
   for body in bodies:
    connected=dict(zip(range(guest.ENTRY,guest.ENTRY+564,4),body));connected.update(guest.helper_code(c))
    m=CallerOracle(ws,guest.fixture(c),c,entry=entry,connected=connected);m.root_calls=0;m.r[29]=guest.STACK+phase+24;m.before=m.r[:];saved=m.r[:];saved_f=m.f[:];m.run();assert m.root_calls==1
    want,expected,observations,trap=guest.reference(m.root_initial,c);assert not trap;want[guest.read(want,guest.SYMS['D_800D154C'])+0x223]=status
    assert(guest.public(m.memory),m.calls,m.observations)==(guest.public(want),expected,observations),(hex(entry),c)
    assert m.r[16:24]==saved[16:24]and m.r[28:]==saved[28:]and m.f[20:]==saved_f[20:]
    seen.update(m.visits&set(range(entry,entry+44,4)));count+=1
 assert len(seen)==33
 report=dict(executions=count,bodies=3,retail_ROM_JALs=[hex(v)for v in calls],current_linked_JALs=len(linked),aligned_literal_pointers=[hex(v)for v in ptrs],direct_jumps=0,complete_original_wrappers=3,original_wrapper_words=33,visited_wrapper_words=len(seen),void_no_arguments=True,live_actor_reloaded_after_call=True,dispatch_pointer_preserved_by_protected_data=True,indirect_dispatcher_or_hardware_qualified=False)
 (out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
