"""Two original caller windows; current caller placeholders remain uncredited."""
import json,struct,sys
from dataclasses import replace
from pathlib import Path
from tools.experiments.game_attachment_status_1504af10_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_attachment_status_1504af10_oracle as guest
from tools.experiments import game_attachment_status_1504af10_match as qualify
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.match_progress import load_elf_functions
WINDOWS=((0x1504AB48,0x1504AB58,16,0),(0x15060F80,0x15060F98,17,1))
class CallerOracle(guest.Oracle):
 def record_call(self,t):
  if t==guest.ENTRY:
   assert tuple(self.arguments(3))==guest.args(self.case);self.root_calls+=1;return
  super().record_call(t)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();jal=(0x0C000000|((guest.ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');j=(0x08000000|((guest.ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big')
 calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];ptrs=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==guest.ENTRY.to_bytes(4,'big')];jumps=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==j];assert calls==[0x78000,0x8E440]and not ptrs and not jumps,(calls,ptrs,jumps)
 before=(out/'frozen'/qualify.ELF).read_bytes();functions,_,_=load_elf_functions(str(out/'frozen'/qualify.ELF),'mips-linux-gnu-objdump');assert not[(n,i)for n,ws in functions.items()for i,w in enumerate(ws)if w==int.from_bytes(jal,'big')]
 sizes={n:r[2]for _,n,r,_ in symbol_rows(before)};stubs={n:dict(symbol_bytes=sizes[n],padded_disassembly_words=len(functions[n]))for n in('func_1504A730','func_15060F28')};assert [v['symbol_bytes']for v in stubs.values()]==[12,16],stubs
 bodies=(guest.words(out/'qualified-owner.o'),guest.words(out/'qualified-padded/game_77AD0.c.o'),list(struct.unpack_from('>123I',rom,qualify.ROM)));count=real=0;seen=set()
 for entry,stop,areg,force in WINDOWS:
  offset=entry-0x15000000+0x2D4B0;window=list(struct.unpack_from('>%dI'%((stop-entry)//4),rom,offset));at=elf_slot_offset(before,entry,stop-entry);assert before[at:at+stop-entry]==bytes(stop-entry),'Previously absent caller window changed'
  for connected_real in(False,True):
   samples=guest.cases()if not connected_real else[replace(guest.Case(),flags=flags,phase=phase)for flags in(0,1,0xFFF,0x8001,0x3001,0xBFFF)for phase in(0,8)]
   for base in samples:
    c=replace(base,force=force,release=0)
    for ws in bodies:
     connected=dict(zip(range(guest.ENTRY,guest.ENTRY+4*len(ws),4),ws));connected[stop]=0
     if connected_real:connected.update(guest.helper())
     m=CallerOracle(window,guest.fixture(c),c,entry=entry,connected=connected);m.root_calls=0;m.r[areg]=guest.actor(c)
     if areg==17:m.r[16]=1
     m.initial=dict(m.memory);m.code=WindowCode(m.code,m);m.code.ends=(stop,);saved=m.r[:];saved_f=m.f[:]
     try:m.run()
     except WindowBoundary:pass
     else:raise AssertionError('Caller boundary not reached')
     want,expected,obs=guest.reference(m.initial,c,connected=connected_real);assert m.root_calls==1 and(m.calls,m.observations)==(expected,obs)
     assert guest.public(m.memory)==guest.public(want)and all(m.memory[p]==want[p]for p in m.initial if guest.STACK+c.phase<=p<guest.STACK+c.phase+512)
     assert m.r[16:24]==saved[16:24]and m.r[28:31]==saved[28:31]and m.f[20:]==saved_f[20:];seen.update(m.visits&set(range(entry,stop,4)));count+=1;real+=int(connected_real)
 entry,stop,areg,force=WINDOWS[1];offset=entry-0x15000000+0x2D4B0;window=list(struct.unpack_from('>6I',rom,offset))
 for rejected in(0,2,0x100,0xFFFFFFFF):
  c=guest.Case();m=CallerOracle(window,guest.fixture(c),c,entry=entry,connected={0x15060FB8:0});m.root_calls=0;m.r[16]=rejected;m.r[17]=guest.actor(c);initial=dict(m.memory);m.code=WindowCode(m.code,m);m.code.ends=(0x15060FB8,)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Caller rejection not reached')
  assert m.memory==initial and not m.calls and not m.root_calls and m.r[4]==guest.actor(c);seen.update(m.visits&set(range(entry,stop,4)))
 assert len(seen)==10
 report=dict(executions=count,bodies=3,original_windows=2,original_window_words=[4,6],original_window_visited=len(seen),retail_ROM_JALs=[hex(v)for v in calls],aligned_literal_pointers=0,direct_jumps=0,current_linked_JALs=0,current_stub_callers=stubs,real_zero_resolver_executions=real,scripted_returns_are_extension_cases=True,second_caller_rejections=4,full_parent_or_hardware_claimed=False)
 (out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
