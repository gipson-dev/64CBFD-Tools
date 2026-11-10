"""Authentic retail call window; parent func_1504CB98 remains an unfinished placeholder."""
import itertools,json,struct,sys
from pathlib import Path
from tools.experiments.game_actor_state_1504be2c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_actor_state_1504be2c_oracle as guest
from tools.experiments import game_actor_state_1504be2c_match as qualify
from tools.match_progress import load_elf_functions
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
START=0x1504E000;ROM=0x7B4B0;END=0x1504E078
class CallerOracle(guest.Oracle):
 def record_call(self,t):
  if t==guest.ENTRY:
   assert tuple(self.arguments(4))==guest.args(self.case);self.root_calls+=1;self.root_initial=dict(self.memory);return
  return super().record_call(t)

def main():
 rom=(root/'conker/conker.us.bin').read_bytes();jal=0x0C000000|(guest.ENTRY>>2&0x3FFFFFF);jump=0x08000000|(guest.ENTRY>>2&0x3FFFFFF);calls=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==jal];assert calls==[0x7B510];assert not any(int.from_bytes(rom[i:i+4],'big')in(guest.ENTRY,jump)for i in range(0,len(rom)-3,4))
 fs,_,addresses=load_elf_functions(str(out/'frozen'/qualify.ELF),'mips-linux-gnu-objdump');linked=[(n,i)for n,ws in fs.items()for i,w in enumerate(ws)if w==jal];parent=fs['func_1504CB98'];assert linked==[] and parent[:2]==[0x00001025,0x03E00008]and len(parent)==4500 and not any(parent[2:])
 raw=rom[ROM:ROM+END-START];ws=list(struct.unpack('>30I',raw));runs=roots=0;seen=set()
 for label,p in(('raw',out/'selected.o'),('normalized',out/'qualified-padded/game_77AD0.c.o'),('retail',out/'retail-linked.o')):
  target=guest.words(p)
  for gate,mode,byte,actorflag,type,flags,first,phase in itertools.product((-32768,0,1),(1,3),(0,129),(0,255),(0xAA,0x2C),(0,1),(0,1),(0,8)):
   sp=guest.STACK+phase;c=guest.replace(guest.Case(),type=type,flags=flags,first=first,phase=phase,inputptr=sp+444,magptr=sp+436,outputptr=sp+407);initial=guest.fixture(c);guest.put(initial,sp+444,c.input,2);guest.put(initial,sp+436,c.magnitude);guest.put(initial,guest.CHILD+8,gate,2);initial[guest.CHILD+120]=mode;initial[guest.ACTOR+311]=actorflag;initial[guest.CONTROL+3]=byte
   connected=dict(zip(range(guest.ENTRY,guest.ENTRY+len(target)*4,4),target));m=CallerOracle(ws,initial,c,entry=START,connected=connected);m.r[16]=guest.ACTOR;m.r[13]=guest.CONTROL;m.f[12]=guest.bits(-7.25);m.root_calls=0;saved=m.r[:];savedf=m.f[:];m.code=WindowCode(m.code,m);m.code.ends={END}
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Retail window did not end')
   called=gate>0 or mode==3;assert m.root_calls==int(called)
   if called:
    want,cs,obs=guest.reference(m.root_initial,c);assert m.calls==cs and m.observations==obs;assert m.f[12]==guest.bits(-7.25);roots+=1
   else:
    want=dict(initial)
    if byte==0:want[guest.CHILD+83]=0
    if actorflag==255:want[guest.ACTOR+311]=0
    want[sp+441]=12;assert not m.calls
   assert guest.public(m.memory)==guest.public(want)
   assert all(m.memory[p]==want[p]for p in want if sp+16<=p<sp+512)
   assert m.r[4]==guest.ACTOR and m.r[6]==m.memory[guest.read(m.memory,guest.ACTOR+796)+120]
   assert m.r[16:24]==saved[16:24]and m.r[28:31]==saved[28:31]and m.f[20:]==savedf[20:];seen.update(m.visits&set(range(START,END,4)));runs+=1
 assert len(seen)==30
 report=dict(executions=runs,target_invocations=roots,ROM_JALs=calls,linked_JALs=linked,aligned_entry_pointers=0,direct_jumps=0,retail_window_words=30,visited_words=30,window_start=hex(START),window_end=hex(END),actual_stack_pointers={'input':444,'magnitude':436,'output_byte':407},delay_slot_float_save_and_reload=True,void_result_discarded=True,parent='func_1504CB98',parent_is_placeholder=True,complete_parent_qualified=False,hardware_qualified=False)
 (out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
